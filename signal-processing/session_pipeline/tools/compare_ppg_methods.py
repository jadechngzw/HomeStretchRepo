"""Compare v0 and NeuroKit Elgendi on raw recordings without uploading results."""
import argparse,json,sys,hashlib,warnings
from pathlib import Path
import numpy as np
from scipy import signal
import neurokit2 as nk
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
# Installed in session_pipeline/tools; caller supplies PYTHONPATH=signal-processing.
from session_pipeline.reader import load_recording
from session_pipeline.ppg_reference import filtered,estimate
from session_pipeline.ppg import summarize,merge_estimates


def detector(t,x,method):
    fs=1/np.median(np.diff(t));cut=int(fs)
    if method=='v0':
        y=filtered(t,x);z=y[cut:-cut];rms=np.std(z)
        p,_=signal.find_peaks(z-z.mean(),distance=max(1,int(fs*.3)),prominence=rms*.6);p+=cut
    else:
        y=nk.ppg_clean(x,sampling_rate=fs,method='elgendi')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            p=nk.ppg_findpeaks(y,sampling_rate=fs,method='elgendi')['PPG_Peaks']
        p=p[(p>=cut)&(p<len(y)-cut)];z=y[cut:-cut];rms=np.std(z)
    iv=np.diff(t[p]);bpm=float(60/np.median(iv)) if len(iv) else None
    cv=float(np.std(iv)/np.mean(iv)) if len(iv)>=3 else None
    z=z-z.mean();ac=signal.correlate(z,z,mode='full')[len(z)-1:];ac=ac/ac[0] if ac[0]>0 else ac*0
    lo=int(fs*60/200);hi=min(len(ac),int(fs*60/40));c,_=signal.find_peaks(ac[lo:hi]);c+=lo
    lag=int(c[np.argmax(ac[c])]) if len(c) else None;period=float(ac[lag]) if lag else None;ba=60*fs/lag if lag else None
    f,power=signal.periodogram(z,fs,nfft=max(4096,len(z)));mask=(f>=40/60)&(f<=200/60);bf=float(f[mask][np.argmax(power[mask])]*60)
    failures=[]
    if rms<2:failures.append('weak_amplitude')
    if np.max(abs(np.diff(x)))>max(100,8*rms):failures.append('abrupt_change')
    if period is None:failures.append('no_autocorrelation_peak')
    elif period<.45:failures.append('periodicity_below_0.45')
    if ba is not None and abs(ba-bf)>10:failures.append('autocorrelation_fft_disagreement')
    if bpm is None or abs(bpm-bf)>12:failures.append('peaks_fft_disagreement')
    if cv is None or cv>.22:failures.append('interval_cv_above_0.22')
    return dict(candidate_bpm=bpm,interval_cv=cv,periodicity=period,autocorrelation_bpm=ba,fft_bpm=bf,
                passed=not failures,failed_checks=failures,peak_times_sec=t[p].tolist()),y,p


def run(csv,out,label):
    rec=load_recording(csv);s=rec['streams']['ppg_green'];windows=[]
    for start in np.arange(s[0,0]+5,s[-1,0]-8+1e-6,1):
        w=s[(s[:,0]>=start-1e-6)&(s[:,0]<=start+8+1e-6)]
        if not np.all(w[:,4]):continue
        row=dict(start_sec=float(start),end_sec=float(start+8))
        for method in ['v0','elgendi']:
            try:row[method]=detector(w[:,0],w[:,1],method)[0]
            except Exception as e:row[method]=dict(candidate_bpm=None,passed=False,error=str(e),peak_times_sec=[])
        old=estimate(w[:,0],w[:,1]);row['v0']['passed']=old['bpm'] is not None;row['v0']['original_quality']=old['quality'];windows.append(row)
    report=dict(label=label,source=str(csv),source_sha256=hashlib.sha256(Path(csv).read_bytes()).hexdigest(),
                duration_sec=rec['duration'],neurokit_version=nk.__version__,new_v0_summary=summarize(s,rec['duration'],'ppg_green'),windows=windows)
    for method in ['v0','elgendi']:
        candidates=[w[method]['candidate_bpm'] for w in windows if w[method]['candidate_bpm'] is not None]
        ranges=[dict(start_sec=w['start_sec']+1,end_sec=w['start_sec']+7,bpm=w[method]['candidate_bpm']) for w in windows if w[method]['passed']]
        merged=merge_estimates(ranges);duration=sum(w['end_sec']-w['start_sec'] for w in merged)
        report[method]=dict(accepted_window_count=len(ranges),accepted_time_sec=duration,coverage_pct=100*duration/rec['duration'],
            candidate_bpm_median=float(np.median(candidates)) if candidates else None,
            candidate_bpm_range=[float(min(candidates)),float(max(candidates))] if candidates else None,
            accepted_intervals=merged)
    # Match time windows across algorithms. Show one rejected early window and one later.
    starts=[5.,21. if rec['duration']>=29 else 13.]
    fig=Figure(figsize=(13,8),layout='constrained');FigureCanvasAgg(fig);axes=fig.subplots(3,2)
    for col,start in enumerate(starts):
        w=s[(s[:,0]>=start-1e-6)&(s[:,0]<=start+8+1e-6)];t,x=w[:,0],w[:,1]
        axes[0,col].plot(t,x,lw=.9,color='#555555');axes[0,col].set(title=f'{label}: {start:g}–{start+8:g} s — raw PPG',ylabel='ADC counts')
        for row,method in enumerate(['v0','elgendi'],1):
            d,y,peaks=detector(t,x,method);axes[row,col].plot(t,y,lw=.9);axes[row,col].scatter(t[peaks],y[peaks],c='#dd5500',s=30,zorder=3)
            candidate=d['candidate_bpm'];value=f'{candidate:.1f}' if candidate is not None else 'none'
            axes[row,col].set(title=f'{method}: candidate {value} bpm; '+('passes checks' if d['passed'] else 'fails checks'),ylabel='Filtered counts',xlabel='Seconds')
            axes[row,col].axvspan(start,start+1,color='grey',alpha=.15);axes[row,col].axvspan(start+7,start+8,color='grey',alpha=.15)
    for ax in axes.flat:ax.grid(alpha=.2)
    fig.savefig(out/(label+'-detected-beats.png'),dpi=140)
    (out/(label+'-comparison.json')).write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(label,json.dumps({k:report[k] for k in ['v0','elgendi']},allow_nan=False))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--still',required=True);p.add_argument('--curls',required=True);p.add_argument('--output',required=True);args=p.parse_args()
    out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    for label in ['still','curls']:run(getattr(args,label),out,label)
