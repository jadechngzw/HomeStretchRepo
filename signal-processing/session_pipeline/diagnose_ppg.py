"""Inspect PPG and motion together; no motion cancellation or validated HR claim."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy import signal
from .reader import load_recording
from .ppg_reference import filtered, estimate
from .pipeline import clean


def diagnose(csv_path, channel='ppg_green'):
    rec=load_recording(csv_path);ppg=rec['streams'].get(channel);acc=rec['streams'].get('acceleration')
    if ppg is None:raise ValueError('Requested PPG channel is not recorded.')
    windows=[]
    for start in np.arange(ppg[0,0]+5,ppg[-1,0]-8+1e-6,1):
        p=ppg[(ppg[:,0]>=start-1e-6)&(ppg[:,0]<=start+8+1e-6)]
        item=dict(start_sec=float(start),end_sec=float(start+8),candidate_bpm=None,
                  motion_rms_g=None,dominant_motion_hz=None,ppg_spectral_peak_bpm=None,
                  motion_harmonic_overlap=None)
        if len(p)<100 or not np.all(p[:,4]):
            item['quality']='Invalid/insufficient PPG';windows.append(item);continue
        e=estimate(p[:,0],p[:,1]);item.update(candidate_bpm=e['bpm'],quality=e['quality'],periodicity=e['periodicity'])
        y=filtered(p[:,0],p[:,1]);fs=1/np.median(np.diff(p[:,0]))
        if np.all(np.isfinite(y)):
            f,power=signal.periodogram(y,fs,nfft=4096)
            band=(f>=40/60)&(f<=200/60)
            peak=float(f[band][np.argmax(power[band])]);item['ppg_spectral_peak_bpm']=60*peak
        else:peak=None
        if acc is not None:
            a=acc[(acc[:,0]>=start-.06)&(acc[:,0]<=start+8+.06)&(acc[:,4]>0)]
            if len(a)>100 and a[0,0]<=p[0,0] and a[-1,0]>=p[-1,0] and np.max(np.diff(a[:,0]))<=.060001:
                x=np.column_stack([np.interp(p[:,0],a[:,0],a[:,j]) for j in (1,2,3)])
                x=x-x.mean(axis=0);item['motion_rms_g']=float(np.sqrt(np.mean(np.sum(x*x,axis=1))))
                mf,mp=signal.periodogram(x,fs,axis=0,nfft=4096);mp=mp.sum(axis=1)
                band=(mf>=.1)&(mf<=3)
                motion_peak=float(mf[band][np.argmax(mp[band])]);item['dominant_motion_hz']=motion_peak
                item['motion_harmonic_overlap']=bool(peak is not None and min(abs(peak-n*motion_peak) for n in (1,2,3,4))<.12)
        windows.append(item)
    return clean(dict(channel=channel,window_sec=8,step_sec=1,windows=windows,
        status='diagnostic_only',notes=[
            'Overlapping window candidates are not a validated session HR estimate.',
            'Spectral peak can reflect movement, pulse, drift or noise.',
            'Harmonic overlap is a screening hint, not proof or a cancellation algorithm.',
            'Motion spectrum uses short-gap interpolation when available.',
            'PPG and IMU device clocks have not been independently synchronized/calibrated.'])),rec


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('csv');p.add_argument('--output-dir',required=True)
    args=p.parse_args();out=Path(args.output_dir)
    if out.exists():p.exit(2,'Output directory already exists; choose a new name.\n')
    report,rec=diagnose(args.csv)
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    fig=Figure(figsize=(12,10),layout='constrained');FigureCanvasAgg(fig);axes=fig.subplots(3,2)
    ppg=rec['streams']['ppg_green'];acc=rec['streams'].get('acceleration')
    for col,(start,end,title) in enumerate([(14,22,'During curls'),(50,58,'Mostly still afterward')]):
        w=ppg[(ppg[:,0]>=start)&(ppg[:,0]<=end)];x=w[:,1].copy();x[w[:,4]==0]=np.nan
        axes[0,col].plot(w[:,0],x,linewidth=.8);axes[0,col].set(title=title+' — raw green PPG',ylabel='ADC counts')
        axes[1,col].plot(w[:,0],filtered(w[:,0],x),linewidth=.8);axes[1,col].set(title='0.5–4 Hz filtered PPG',ylabel='Filtered counts')
        if acc is not None:
            a=acc[(acc[:,0]>=start)&(acc[:,0]<=end)];v=a[:,1:4].copy();v[a[:,4]==0]=np.nan
            for j in range(3):axes[2,col].plot(a[:,0],v[:,j],label='xyz'[j],linewidth=.8)
            axes[2,col].legend()
        axes[2,col].set(title='Motion reference (invalid readings left blank)',ylabel='Acceleration (g)',xlabel='Seconds from recording start')
    for ax in axes.flat:ax.grid(alpha=.2)
    out.mkdir(parents=True)
    (out/'diagnostics.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    fig.savefig(out/'ppg-motion-comparison.png',dpi=140)
    print('Saved diagnostics and comparison plot to',out)

if __name__=='__main__':main()
