"""Optional legacy four-feature Isolation Forest, explicitly experimental on v0."""
import hashlib
import warnings
from pathlib import Path
import numpy as np
from .imu_reference import compute_tremor_energy_ratio

FEATURES=['duration','norm_amp','dom_freq','log_tremor']
LEGACY_THRESHOLD=-0.19


def classify(imu, accel, model_path, scaler_path, *, threshold=LEGACY_THRESHOLD):
    import joblib
    import pandas as pd
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    from sklearn.exceptions import InconsistentVersionWarning
    if not np.isfinite(threshold):raise ValueError('Classifier threshold must be finite.')
    # Load only the user's explicitly selected, trusted local model artifacts.
    with warnings.catch_warnings():
        warnings.simplefilter('error',InconsistentVersionWarning)
        model=joblib.load(model_path);scaler=joblib.load(scaler_path)
    if not isinstance(model,IsolationForest) or not isinstance(scaler,StandardScaler):
        raise ValueError('Expected an IsolationForest and StandardScaler pair.')
    if model.n_features_in_!=4 or list(getattr(scaler,'feature_names_in_',[]))!=FEATURES:
        raise ValueError('Legacy model/scaler feature schema mismatch.')
    info=dict(status='experimental_transfer',threshold=threshold,feature_order=FEATURES,
              method_version='mbient-four-feature-v0-transfer-0.1',
              model_sha256=hashlib.sha256(Path(model_path).read_bytes()).hexdigest(),
              scaler_sha256=hashlib.sha256(Path(scaler_path).read_bytes()).hexdigest(),
              model_file=Path(model_path).name,scaler_file=Path(scaler_path).name,
              notes=['Notebook training uses Apple Watch gravityX, whereas this pipeline uses total acceleration.',
                     'Threshold -0.19 comes from Mbient tuning; no new-watch calibration is established.',
                     'Rep boundaries come from the configured v0 segmenter, not the legacy segmenter.',
                     'Short-gap interpolation can suppress tremor energy and change anomaly scores.',
                     'Typical/Atypical are model predictions, not verified exercise correctness.'])
    reps=imu['repetitions']
    if accel is None or not reps:
        info['status']='no_repetitions_to_classify';return info
    axis='xyz'.index(imu['axis'])+1
    valid=accel[(accel[:,4]>0)&np.isfinite(accel[:,axis])]
    if len(valid)<3:return dict(info,status='insufficient_data')
    period=float(np.median(np.diff(accel[:,0])));fs=1/period
    # Session normalization approximates the legacy trimmed-session normalization;
    # it is a declared transfer assumption, not exact training-pipeline equivalence.
    region=valid[(valid[:,0]>=reps[0]['start_sec'])&(valid[:,0]<=reps[-1]['end_sec'])]
    if len(region)<3:return dict(info,status='insufficient_data')
    mean=float(np.mean(region[:,axis]));std=float(np.std(region[:,axis]))
    prepared=[]
    for rep in reps:
        start,end=rep['start_sec'],rep['end_sec']
        left=max(0,np.searchsorted(valid[:,0],start,side='right')-1)
        right=min(len(valid),np.searchsorted(valid[:,0],end,side='left')+1)
        source=valid[left:right]
        if len(source)<2 or np.any(np.diff(source[:,0])>.060001):
            prepared.append(None);continue
        t=np.arange(start,end+period/2,period)
        x=(np.interp(t,source[:,0],source[:,axis])-mean)/(std+1e-8)
        prepared.append((t,x))
    amplitudes=[float(np.ptp(v[1])) for v in prepared if v is not None]
    average_amp=float(np.mean(amplitudes)) if amplitudes else 0
    rows=[];indices=[]
    for i,item in enumerate(prepared):
        if item is None:continue
        t,x=item
        if len(x)<10 or fs<=16 or average_amp<=0:continue
        f=np.fft.rfftfreq(len(x),d=1/fs);power=np.abs(np.fft.rfft(x))**2
        features=dict(duration=float(t[-1]-t[0]),norm_amp=float(np.ptp(x)/average_amp),
                      dom_freq=float(f[np.argmax(power)]),
                      log_tremor=float(np.log10(compute_tremor_energy_ratio(x,fs)+1)))
        if not all(np.isfinite(list(features.values()))):continue
        rows.append(features);indices.append(i)
    if rows:
        scores=model.decision_function(scaler.transform(pd.DataFrame(rows,columns=FEATURES)))
        for index,features,score in zip(indices,rows,scores):
            rep=reps[index]
            rep.update(classification='Typical' if score>threshold else 'Atypical',
                       classification_status='experimental_transfer',anomaly_score=float(score),
                       classifier_features=features)
    labels=[r['classification'] for r in reps]
    typical=labels.count('Typical');atypical=labels.count('Atypical');unknown=labels.count('Unknown')
    imu.update(typical_reps=typical,atypical_reps=atypical,unknown_reps=unknown,
               rep_classifications=labels,classification_status='experimental_transfer',
               classification=('Unknown' if unknown or typical==atypical else
                               'Typical' if typical>atypical else 'Atypical'))
    info['scored_reps']=typical+atypical;info['unscorable_reps']=unknown
    return info
