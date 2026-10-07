"""Exploratory curl cycles and conservative time accounting, not clinical scoring."""
import numpy as np
from scipy.signal import butter, sosfiltfilt, find_peaks
from .imu_reference import compute_snr_db, compute_tremor_energy_ratio


def summarize(accel, gyro, duration, cfg):
    out = dict(status='unavailable', accepted_reps=None, rep_durations=[], average_rep_duration=None,
               active_time=None, rest_time=None, unscorable_time=duration, rest_status='Unknown',
               snr_db=None, tremor_score=None, smoothness=None, typical_reps=None,
               atypical_reps=None, unknown_reps=None, rep_classifications=[], classification='Unknown',
               classification_status='No validated exercise model configured', duration=duration,
               repetitions=[], rejected_candidates=[], axis=cfg['axis'],
               feature_status='No uninterrupted accepted repetitions available')
    if accel is None or len(accel)<3:
        out['reason']='Insufficient accelerometer data.'
        return out
    # Time bins require both sensors, adjacent valid endpoints, and no large time gap.
    if gyro is not None:
        _, ai, gi = np.intersect1d(accel[:,0],gyro[:,0],return_indices=True)
        a,g=accel[ai],gyro[gi]
        active=rest=0.0
        if len(a)>1:
            dt=np.diff(a[:,0]); period=np.median(np.diff(accel[:,0]))
            valid=(a[:-1,4]>0)&(a[1:,4]>0)&(g[:-1,4]>0)&(g[1:,4]>0)&(dt<=1.6*period)
            rate=np.linalg.norm(np.diff(a[:,1:4],axis=0),axis=1)/dt
            speed=np.maximum(np.linalg.norm(g[:-1,1:4],axis=1),np.linalg.norm(g[1:,1:4],axis=1))
            still=(speed<cfg['rest_gyro_dps'])&(rate<cfg['rest_accel_change_g_per_sec'])
            rest=float(dt[valid&still].sum()); active=float(dt[valid&~still].sum())
        out.update(active_time=active,rest_time=rest,unscorable_time=max(0,duration-active-rest),
                   rest_status='Rest detected' if rest>0 else 'No rest detected')
    if not cfg.get('segmentation_available',True):
        out.update(status='requires_orientation_adapter',reason='This exercise model requires pitch/yaw/roll in degrees; raw acceleration and gyroscope are not compatible inputs.')
        return out
    axis='xyz'.index(cfg['axis'])+1
    good=accel[(accel[:,4]>0)&np.isfinite(accel[:,axis])]
    if len(good)<3:
        out['reason']='Insufficient valid accelerometer readings.'
        return out
    period=float(np.median(np.diff(accel[:,0])))
    fs=1/period
    if fs<=2*cfg['lowpass_hz']:
        out['reason']='Sampling rate too low for configured filter.'
        return out
    groups=np.split(good,np.flatnonzero(np.diff(good[:,0])>cfg['max_bridge_sec']+1e-6)+1)
    snrs, tremors=[],[]
    for group in groups:
        if len(group)<30 or group[-1,0]-group[0,0]<cfg['min_rep_sec']:
            continue
        t=np.arange(group[0,0],group[-1,0]+1e-8,period)
        raw=np.interp(t,group[:,0],group[:,axis])
        if len(t)<30:
            continue
        y=sosfiltfilt(butter(2,cfg['lowpass_hz'],fs=fs,output='sos'),raw)
        peaks,_=find_peaks(y,prominence=cfg['peak_prominence_g'],distance=max(1,int(fs*cfg['min_rep_sec'])))
        # One cycle is peak-to-next-positive-peak. Edge partial reps are omitted.
        for left,right in zip(peaks[:-1],peaks[1:]):
            start,end=float(t[left]),float(t[right]); length=end-start
            if not cfg['min_rep_sec']<=length<=cfg['max_rep_sec']:
                out['rejected_candidates'].append(dict(start_sec=start,end_sec=end,reason='Duration outside configured range'))
                continue
            original=accel[(accel[:,0]>=start-period/2)&(accel[:,0]<=end+period/2)]
            valid_count=int(np.sum(original[:,4]>0))
            expected=max(1,round(length/period)+1)
            repair=max(0,1-valid_count/expected, float(np.mean(original[:,4]==0)) if len(original) else 1)
            if repair>cfg['max_rep_interpolated_fraction']:
                out['rejected_candidates'].append(dict(start_sec=start,end_sec=end,reason='Too much missing/invalid data'))
                continue
            record=dict(start_sec=start,end_sec=end,duration_sec=length,
                        classification='Unknown',estimated_interpolated_fraction=repair,
                        quality='short_gaps_interpolated' if repair>0 else 'observed')
            out['repetitions'].append(record)
            # Do not infer high-frequency features from interpolated invalid samples.
            if repair==0 and fs>16 and len(original)>30 and np.all(original[:,4]):
                try:
                    snr=compute_snr_db(raw[left:right+1],fs)
                    tremor=compute_tremor_energy_ratio(raw[left:right+1],fs)
                    if np.isfinite(snr):snrs.append(float(snr))
                    if np.isfinite(tremor):tremors.append(float(tremor))
                except ValueError:
                    pass
    reps=out['repetitions']; n=len(reps)
    out.update(status='experimental',accepted_reps=n,rep_durations=[r['duration_sec'] for r in reps],
               average_rep_duration=float(np.mean([r['duration_sec'] for r in reps])) if n else None,
               unknown_reps=n,rep_classifications=['Unknown']*n)
    if snrs:out['snr_db']=float(np.mean(snrs))
    if tremors:
        out['tremor_score']=float(np.mean(tremors));out['smoothness']=1/(1+out['tremor_score'])
    out['feature_repetitions']=dict(snr=len(snrs),tremor=len(tremors))
    if snrs or tremors:out['feature_status']='Mean of uninterrupted accepted repetitions only; exploratory'
    return out
