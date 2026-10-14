"""Pure local orchestration. Firebase is intentionally absent."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import math
from . import __version__
from .reader import load_recording
from .motion import summarize as summarize_motion
from .ppg import summarize as summarize_ppg


def clean(value):
    if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
    if isinstance(value,list):return [clean(v) for v in value]
    if isinstance(value,float):return round(value,6) if math.isfinite(value) else None
    return value


def process(csv_path, *, patient_id, exercise_id, body_side, metadata_path=None,
            axis=None, ppg_channel='ppg_green', rep_goal=None, max_hr_bpm=None,
            experimental_model=None, experimental_scaler=None, orientation_classification=True,
            orientation_sidecar=None, sensor_placement="wrist"):
    if not patient_id.strip():raise ValueError('Patient ID must not be empty.')
    if body_side not in ('left','right'):raise ValueError('Choose left or right body side.')
    if rep_goal is not None and rep_goal<=0:raise ValueError('Rep goal must be positive.')
    if max_hr_bpm is not None and (not math.isfinite(max_hr_bpm) or max_hr_bpm<=0):
        raise ValueError('HR threshold must be a positive finite number.')
    configs=json.loads(Path(__file__).with_name('exercises.json').read_text())
    if exercise_id not in configs:raise ValueError(f'Unsupported exercise: {exercise_id}. Supported: {list(configs)}')
    cfg=configs[exercise_id].copy()
    if axis is not None:
        if axis not in ('x','y','z'):raise ValueError('Axis must be x, y or z.')
        cfg['axis']=axis
    rec=load_recording(csv_path,metadata_path); meta=rec['metadata']; streams=rec['streams']
    imu=summarize_motion(streams.get('acceleration'),streams.get('gyroscope'),rec['duration'],cfg)
    hr=summarize_ppg(streams.get(ppg_channel),rec['duration'],ppg_channel,max_hr_bpm)
    classifier_info=None
    registry=json.loads(Path(__file__).with_name('model_registry.json').read_text())
    selected_model=registry.get(exercise_id)
    if not cfg.get('segmentation_available',True):
        from .orientation_models import summarize as summarize_orientation
        classifier_info=summarize_orientation(imu,streams.get('acceleration'),streams.get('gyroscope'),
            selected_model,classify=orientation_classification,sidecar=orientation_sidecar,placement=sensor_placement)
    elif experimental_model is not None or experimental_scaler is not None:
        if experimental_model is None or experimental_scaler is None:
            raise ValueError('Supply both experimental model and scaler paths.')
        from .classifier import classify
        classifier_info=classify(imu,streams.get('acceleration'),experimental_model,experimental_scaler)
    flags=[]
    def flag(code,message,source,severity='info',**details):
        flags.append(dict(code=code,message=message,source=source,severity=severity,**details))
    if meta.get('demo'):flag('DEMO_RECORDING','This is simulated data.','recording','warning')
    if not rec['complete']:flag('INCOMPLETE_RECORDING','Recording has incomplete or invalid data; review quality counts.','recording','warning')
    if any(r['estimated_interpolated_fraction']>0 for r in imu['repetitions']):
        flag('SHORT_GAPS_INTERPOLATED','Some estimated cycles use short interpolated gaps.','imu','warning')
    if classifier_info is None or classifier_info.get('classification_enabled') is False:
        flag('CLASSIFICATION_UNAVAILABLE','No validated model is configured for this exercise and watch.','imu','warning')
    elif classifier_info['status']=='requires_orientation_adapter':
        flag('ORIENTATION_REQUIRED','Exercise selected and raw data saved; rep segmentation and model scoring require orientation conversion.','imu','warning')
    else:
        flag('EXPERIMENTAL_CLASSIFICATION','Model predictions are unvalidated on this watch; see model and orientation provenance.','imu','warning')
    if classifier_info and classifier_info.get('orientation'):
        flag('EXPERIMENTAL_ORIENTATION','Pitch/roll are fused estimates; yaw is relative and can drift. Anatomical-axis transfer is unvalidated.','imu','warning')
    if hr['bpm'] is None:flag('PPG_UNAVAILABLE','No valid pulse estimate available.','hr','warning')
    elif hr['valid_signal_coverage_pct']<100:
        flag('PPG_PARTIAL_COVERAGE','Pulse summary covers only accepted analysis intervals.','hr',value=hr['valid_signal_coverage_pct'])
    if rep_goal is not None and imu['accepted_reps'] is not None:
        met=imu['accepted_reps']>=rep_goal
        flag('REP_GOAL_MET' if met else 'REP_GOAL_NOT_MET','Estimated rep goal met.' if met else 'Estimated rep goal not met.',
             'imu',value=imu['accepted_reps'],threshold=rep_goal)
    if max_hr_bpm is not None and hr['peak_hr_bpm'] is not None and hr['peak_hr_bpm']>max_hr_bpm:
        flag('HR_THRESHOLD_EXCEEDED','An accepted pulse window exceeded the configured threshold.','hr','warning',value=hr['peak_hr_bpm'],threshold=max_hr_bpm)
    # Source hashes plus declared identity/exercise/settings produce stable rerun IDs.
    identity={'csv_sha256':rec['csv_sha256'],'metadata_sha256':rec['metadata_sha256'],
              'patient_id':patient_id,'exercise_id':exercise_id,'body_side':body_side}
    sid='hs-'+hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:24]
    source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}
    return clean(dict(schema_version='1.0',session_id=sid,patient_id=patient_id,
        exercise=dict(id=exercise_id,name=cfg['name'],body_side=body_side,sensor_placement=sensor_placement,rep_goal=rep_goal),
        started_at=meta['started_utc'],ended_at=meta['ended_utc'],timezone='UTC',
        recording=dict(complete=rec['complete'],declared_complete=meta.get('complete'),demo=meta.get('demo',False),
            duration_sec=rec['duration'],raw_file=Path(rec['csv_path']).name,metadata_file=Path(rec['metadata_path']).name,
            source_session_id=meta['session_id'],csv_sha256=rec['csv_sha256'],metadata_sha256=rec['metadata_sha256'],
            received=rec['samples'],invalid_samples=rec['invalid_samples'],missing_by_sequence=rec['sequence_gaps'],
            sensors={k:dict(samples=len(a),invalid_samples=int(sum(a[:,4]==0))) for k,a in streams.items()}),
        imu=imu,hr=hr,
        guidance=dict(status='experimental',rules_version='0.1.0',patient_state='Unknown',
                      reason='No validated patient-state assessment is configured; experimental predictions do not establish clinical status.',flags=flags),
        processing=dict(pipeline_version=__version__,firmware_version=meta.get('firmware_version'),
            protocol_version=meta['protocol_version'],imu_method_version=cfg['method_version'],
            ppg_method_version='v0-estimate-overlap-union-0.2',
            model_version=classifier_info.get('model_sha256') if classifier_info else None,
            selected_model=selected_model,
            classifier=classifier_info,exercise_config=cfg,
            source_hashes=source_hashes,processed_at=datetime.now(timezone.utc).isoformat(),
            warnings=['Unvalidated research estimates.','PPG quality checks cannot rule out rhythmic motion artifacts.',
                      'Rep count omits incomplete edge cycles; no manual ground-truth count is available.'])))


def save_result(result, path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    text=json.dumps(result,indent=2,allow_nan=False)+'\n'
    with path.open('x') as handle:handle.write(text)
