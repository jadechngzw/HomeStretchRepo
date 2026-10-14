"""Vendored v0 PPG routines; see METHODS.md for source and limitations."""
import numpy as np
from scipy import signal

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

