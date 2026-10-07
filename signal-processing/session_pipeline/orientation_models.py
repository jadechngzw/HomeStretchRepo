"""Adapt raw watch IMU to the saved REHAB segmentation and 17-feature models."""
import importlib.util
import json
import hashlib
import subprocess
from pathlib import Path
import numpy as np
from scipy.ndimage import uniform_filter1d
from .orientation import estimate,save_csv


def summarize(imu,accel,gyro,selected,*,classify=True,sidecar=None,placement='wrist'):
    repo=Path(__file__).resolve().parents[2]
    config_path=repo/selected['feature_config'];config=json.loads(config_path.read_text())
    spec=importlib.util.spec_from_file_location('hs_rehab_features',repo/'ml/rehab_pipeline.py')
    features_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(features_module)
    blocks,orientation=estimate(accel,gyro,config['sampling_rate_hz_assumed'])
    if sidecar:save_csv(blocks,sidecar)
    info=dict(status='experimental_transfer',method_version='rehab-watch-orientation-0.1',
              selected_model=selected,orientation=orientation,feature_order=config['feature_columns'],
              model_sha256=hashlib.sha256((repo/selected['model']).read_bytes()).hexdigest(),
              scaler_sha256=hashlib.sha256((repo/selected['scaler']).read_bytes()).hexdigest(),
              feature_config_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),
              feature_source_sha256=hashlib.sha256((repo/'ml/rehab_pipeline.py').read_bytes()).hexdigest(),
              threshold=config['anomaly_threshold'],anomaly_score='negative decision_function; positive is reference outlier',
              placement=placement,training_placement=config['dataset_placement'],
              notes=['Unvalidated watch-to-REHAB transfer; model labels do not establish correct exercise technique.',
                     'Orientation axes, relative yaw and sensor placement differ from the training system.'])
    if not blocks:
        info.update(status='unavailable',scored_reps=0,reason='Insufficient valid paired IMU for orientation.')
        imu.update(status='unavailable',reason=info['reason'])
        return info
    reps=[];rejected=[];rows=[]
    expected=selected['recommended_placement']
    placement_ok=placement==expected or (expected=='forearm' and placement=='wrist')
    for block_id,b in enumerate(blocks):
        session=uniform_filter1d(b['angles'],size=config['smoothing']['window_samples'],axis=0,mode='nearest')
        for segment,rep in features_module.segment_repetitions(session,config['segmentation']):
            start,end=segment['start_sample'],segment['end_sample'];reason=[]
            audit=dict(start_sec=float(b['time'][start]),end_sec=float(b['time'][end]),block=block_id)
            if len(rep)<5:rejected.append(dict(audit,reason='Too short'));continue
            values=features_module.calculate_features(features_module.normalize_repetition(rep),config['sampling_rate_hz_assumed'])
            low,high=config['duration_limits_seconds'];repair=float(np.mean(b['interpolated'][start:end+1]))
            if segment['is_edge']:reason.append('Incomplete edge cycle')
            if not low<=values['duration_seconds']<=high:reason.append('Outside model duration limits')
            if values['completion_error']>config['completion_error']['threshold_degrees']:reason.append('Model return-to-start check failed')
            if repair>.1:reason.append('More than 10% interpolated')
            if np.any(b['gimbal'][start:end+1]):reason.append('Euler singularity proximity')
            if np.any(np.abs(np.diff(b['angles'][start:end+1],axis=0))>90):reason.append('Orientation discontinuity')
            if not placement_ok:reason.append('Use the selected model placement: '+expected)
            if reason:rejected.append(dict(audit,reason='; '.join(reason)));continue
            reps.append(dict(audit,duration_sec=values['duration_seconds'],classification='Unknown',
                             estimated_interpolated_fraction=repair,quality='short_gaps_interpolated' if repair else 'observed',
                             classifier_features=values))
            rows.append([values[name] for name in config['feature_columns']])
    if classify and rows:
        worker=repo/'ml/.venv/bin/python'
        if not worker.is_file():raise ValueError('Missing model scoring environment ml/.venv.')
        request=dict(model_directory=str(config_path.parent),features=rows)
        run=subprocess.run([str(worker),str(repo/'ml/score_features.py')],input=json.dumps(request),text=True,capture_output=True,timeout=45)
        if run.returncode:raise ValueError('Model scoring failed: '+run.stderr[-1200:])
        response=json.loads(run.stdout)
        for rep,score in zip(reps,response['scores'],strict=True):
            rep.update(anomaly_score=score,classification='Atypical' if score>config['anomaly_threshold'] else 'Typical',classification_status='experimental_transfer')
        info['runtime']=response['runtime']
    labels=[r['classification'] for r in reps];n=len(reps);typical=labels.count('Typical');atypical=labels.count('Atypical');unknown=labels.count('Unknown')
    imu.update(status='experimental',accepted_reps=n,rep_durations=[r['duration_sec'] for r in reps],
               average_rep_duration=float(np.mean([r['duration_sec'] for r in reps])) if n else None,
               repetitions=reps,rejected_candidates=rejected,rep_classifications=labels,
               typical_reps=typical if classify else None,atypical_reps=atypical if classify else None,unknown_reps=unknown,
               classification='Unknown' if unknown or typical==atypical else 'Typical' if typical>atypical else 'Atypical',
               classification_status='experimental_transfer' if classify else 'disabled',
               feature_status='Per-rep orientation features retained; acceleration SNR/tremor/smoothness are not substituted.',
               axis=config['segmentation']['channel_name'])
    imu.pop('reason',None)
    info.update(scored_reps=typical+atypical,unscorable_candidates=len(rejected),classification_enabled=classify)
    return info
