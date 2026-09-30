"""Exploratory PPG analysis. Preserve raw data; never fabricate SpO2 or fill gaps."""
import csv, json, html
from pathlib import Path
from datetime import datetime
import numpy as np
from scipy import signal

COLOURS={'ppg_infrared':'#7256a0','ppg_red':'#c94a4a','ppg_green':'#238550','ppg_blue':'#3876cb'}
WINDOW=8.0

def filtered(t,x,causal=False):
    t=np.asarray(t,float);x=np.asarray(x,float)
    if len(t)<(20 if causal else 31) or not np.all(np.isfinite(t)):return np.full(len(t),np.nan)
    dt=np.diff(t);fs=1/np.median(dt)
    if np.any(dt<=0) or np.any(dt>1.6/fs) or not np.all(np.isfinite(x)):return np.full(len(t),np.nan)
    sos=signal.butter(3,[.5,4],fs=fs,btype='bandpass',output='sos')
    if causal:return signal.sosfilt(sos,x,zi=signal.sosfilt_zi(sos)*x[0])[0]
    return signal.sosfiltfilt(sos,x)

def filtered_segments(t,x,causal=False):
    """Display valid contiguous segments, omitting filter settling/edge regions."""
    t=np.asarray(t,float);x=np.asarray(x,float);curve=np.full(len(t),np.nan)
    if len(t)<2:return curve
    valid=np.isfinite(x)&(x>0)&(x<524287);dt=np.diff(t)
    positive=dt[dt>0]
    if not len(positive):return curve
    period=np.median(positive)
    cuts=np.flatnonzero((dt>period*1.6)|(dt<=0)|(~valid[:-1])|(~valid[1:]))+1
    for ids in np.split(np.arange(len(t)),cuts):
        if len(ids)>30 and np.all(valid[ids]):
            y=filtered(t[ids],x[ids],causal)
            y[t[ids]<t[ids[0]]+(3 if causal else 5)]=np.nan
            if not causal:y[t[ids]>t[ids[-1]]-1]=np.nan
            curve[ids]=y
    return curve

def estimate(t,x):
    """8-second window, heuristic quality gate; unvalidated heart-rate estimate."""
    t=np.asarray(t,float);x=np.asarray(x,float)
    out={'bpm':None,'quality':'Insufficient data','periodicity':0.0}
    if len(t)<100 or t[-1]-t[0]<7.8:return out
    if not np.all(np.isfinite(x)) or np.any(x<=0) or np.any(x>=524287):return dict(out,quality='Invalid or clipped signal')
    fs=1/np.median(np.diff(t));y=filtered(t,x)
    if not np.all(np.isfinite(y)):return dict(out,quality='Sample gap')
    y=y[int(fs): -int(fs)] # Exclude filter edges; never count them as beats.
    rms=float(np.std(y))
    if rms<2:return dict(out,quality='Pulse too weak')
    if np.max(np.abs(np.diff(x)))>max(100,8*rms):return dict(out,quality='Abrupt optical change')
    z=y-y.mean();ac=signal.correlate(z,z,mode='full')[len(z)-1:];ac/=ac[0]
    lo=int(fs*60/200);hi=min(len(ac),int(fs*60/40))
    candidates,_=signal.find_peaks(ac[lo:hi]);candidates+=lo
    if not len(candidates):return dict(out,quality='No repeating pulse')
    lag=int(candidates[np.argmax(ac[candidates])]);periodicity=float(ac[lag]);bpm_ac=60*fs/lag
    f,p=signal.periodogram(z,fs,nfft=max(4096,len(z)));mask=(f>=40/60)&(f<=200/60)
    bpm_fft=float(f[mask][np.argmax(p[mask])]*60)
    peaks,_=signal.find_peaks(z,distance=max(1,int(fs*.3)),prominence=rms*.6)
    intervals=np.diff(peaks)/fs
    cv=float(np.std(intervals)/np.mean(intervals)) if len(intervals)>=3 else 99
    bpm_peaks=float(60/np.median(intervals)) if len(intervals) else 0
    if periodicity<.45 or abs(bpm_ac-bpm_fft)>10 or abs(bpm_peaks-bpm_fft)>12 or cv>.22:
        return dict(out,quality='Low confidence / irregular signal',periodicity=periodicity)
    return {'bpm':bpm_peaks,'quality':'Preliminary estimate','periodicity':periodicity}

def read_channels(path):
    channels={};origins={};last={};elapsed={}
    with Path(path).open(newline='') as f:
        for row in csv.DictReader(f):
            name=row['sensor']
            if name not in COLOURS:continue
            ms=int(row['watch_ms'])
            if name not in last:origins[name]=ms;elapsed[name]=0
            else:
                delta=(ms-last[name])&0xffffffff
                if delta>0x7fffffff:raise ValueError('Out-of-order PPG timestamps; inspect the raw recording before analysis.')
                elapsed[name]+=delta
            last[name]=ms
            value=float(row['x']) if row['valid']=='1' and row['x'] else float('nan')
            channels.setdefault(name,[]).append((origins[name]/1000+elapsed[name]/1000,value))
    return {k:np.asarray(v) for k,v in channels.items()}

def analyse_file(path):
    """Create an HTML/PNG/JSON report alongside a stopped CSV; no input edits."""
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    path=Path(path);channels=read_channels(path)
    if not channels:raise ValueError('This recording contains no PPG samples.')
    out=path.parent/(path.stem+'_analysis_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));out.mkdir()
    origin=min(v[0,0] for v in channels.values())
    result={'source':str(path),'method':'0.5–4 Hz offline filtering; 8 s windows every 2 s; first 5 s excluded; heuristic quality checks, no motion compensation','channels':{},'spo2':{'percent':None,'reason':'Requires matched red/infrared signals and device-specific calibration.'}}
    metadata_path=path.with_suffix('.json')
    metadata=json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
    result['recording_complete']=metadata.get('complete')
    result['recording_note']=metadata.get('reason','Completeness metadata unavailable')
    result['demo']=metadata.get('demo',False)
    images=[]
    for name,a in channels.items():
        t=a[:,0]-origin;x=a[:,1];curve=np.full(len(t),np.nan)
        curve=filtered_segments(t,x)
        windows=[]
        for end in np.arange(13,t[-1]+.001,2):
            ids=(t>=end-WINDOW)&(t<=end);e=estimate(t[ids],x[ids]);windows.append(dict(end_s=float(end),**e))
        good=[w['bpm'] for w in windows if w['bpm'] is not None]
        result['channels'][name]={'samples':len(x),'windows':windows,'average_bpm':float(np.mean(good)) if good else None,'accepted_windows':len(good),'total_windows':len(windows),'note':'Average across overlapping accepted windows only; not a whole-record validated heart rate.'}
        fig=Figure(figsize=(11,8),layout='constrained');FigureCanvasAgg(fig);axes=fig.subplots(3,1,sharex=True)
        axes[0].plot(t,x,color=COLOURS[name],lw=.8);axes[0].set_title(name.replace('ppg_','').title()+' — raw recording');axes[0].set_ylabel('ADC counts')
        axes[1].plot(t,curve,color=COLOURS[name],lw=1);axes[1].set_title('Processed PPG (0.5–4 Hz; settling/edge regions omitted)');axes[1].set_ylabel('Filtered counts')
        axes[2].plot([w['end_s'] for w in windows],[np.nan if w['bpm'] is None else w['bpm'] for w in windows],'o-',color=COLOURS[name]);axes[2].set_ylabel('Estimated bpm');axes[2].set_xlabel('Seconds from first optical sample');axes[2].set_title('Heart-rate estimates; rejected windows left blank')
        for ax in axes:ax.grid(alpha=.2)
        img=name+'.png';fig.savefig(out/img,dpi=130);images.append(img)
    # Diagnostic ratio only; pairing requires the exact recorded frame timestamps.
    if 'ppg_red' in channels and 'ppg_infrared' in channels:
        red,ir=channels['ppg_red'],channels['ppg_infrared'];_,ri,ii=np.intersect1d(red[:,0],ir[:,0],return_indices=True)
        rt=red[ri,0]-origin;rx=red[ri,1];ix=ir[ii,1];ratios=[]
        for end in np.arange(13,float(rt[-1])+.001,2) if len(rt) else []:
            sel=(rt>=end-8)&(rt<=end);tr=rt[sel];rr=rx[sel];iv=ix[sel]
            if estimate(tr,rr)['bpm'] is None or estimate(tr,iv)['bpm'] is None:continue
            ry=filtered(tr,rr);iy=filtered(tr,iv)
            if np.corrcoef(ry,iy)[0,1]<.6:continue
            ratio=float((np.std(ry)/np.mean(rr))/(np.std(iy)/np.mean(iv)))
            ratios.append({'end_s':float(end),'R':ratio})
        result['spo2']['paired_windows']=ratios
        result['spo2']['reason']='Red/infrared ratio R available for research; SpO2 % withheld without calibration.' if ratios else 'Red/infrared present, but no paired windows passed signal-quality checks.'
    (out/'report.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    parts=['<!doctype html><meta charset="utf-8"><title>VitalWave PPG analysis</title><style>body{font:16px system-ui;max-width:1050px;margin:32px auto;padding:16px;color:#172b3a}img{width:100%}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left}</style><h1>PPG analysis</h1>', '<p>'+('SIMULATED DATA. ' if result['demo'] else '')+'Recording complete: '+str(result['recording_complete'])+'. '+html.escape(result['recording_note'])+'</p><p>'+html.escape(result['method'])+'</p><table><tr><th>Channel</th><th>Average estimate</th><th>Accepted windows</th></tr>']
    for k,v in result['channels'].items():
        bpm='Unavailable' if v['average_bpm'] is None else f"{v['average_bpm']:.1f} bpm (preliminary)"
        parts.append(f'<tr><td>{k}</td><td>{bpm}</td><td>{v["accepted_windows"]}/{v["total_windows"]}</td></tr>')
    parts+=['</table><p>Averages cover accepted windows only. Gaps and rejected windows are not repaired.</p><h2>SpO₂</h2><p>'+html.escape(result['spo2']['reason'])+'</p>']
    if result['spo2'].get('paired_windows'):parts.append('<p>Median diagnostic R: %.3f (not oxygen saturation)</p>'%np.median([w['R'] for w in result['spo2']['paired_windows']]))
    parts.extend(f'<img src="{img}" alt="Raw PPG, processed PPG and heart-rate trend">' for img in images)
    (out/'report.html').write_text('\n'.join(parts))
    return str(out/'report.html'),result
