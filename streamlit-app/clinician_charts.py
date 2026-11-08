"""Chart adapters never substitute zeros or synthetic data for missing measurements."""
import math
METRICS={
 'completion_error_deg':'Completion error (°)',
 'peak_excursion_deg':'Peak movement range (°)',
 'gyro_mean_deg_s':'Mean angular speed (°/s)',
 'gyro_peak_deg_s':'Peak angular speed (°/s)',
 'gyro_std_deg_s':'Angular speed variation (°/s)',
 'accel_magnitude_std_g':'Acceleration variation (g)',
 'gyro_high_low_power_ratio':'High / low frequency power',
 'axis_deviation_deg':'Movement direction (°)',
 'off_axis_energy_fraction':'Off-axis movement fraction',
}
def finite(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)
def metric_frame(recording,key):
    stats=((recording.get('baseline') or {}).get('reference') or {}).get('stats') or {}
    band=stats.get(key)
    if not isinstance(band,dict) or not all(finite(band.get(k)) for k in ('mean','lower','upper')): band=None
    values=[]
    for row in recording.get('rep_assessments') or []:
        value=(row.get('metrics') or {}).get(key)
        if row.get('assessable') is not True or not finite(value) or not finite(row.get('rep')): continue
        status='No baseline' if not band else 'Outside baseline' if value<band['lower'] or value>band['upper'] else 'Within baseline'
        values.append({'rep':row['rep'],'value':value,'status':status})
    return values,band

# ---- Cross-session trends (e.g. bicep curls over time) ----
from datetime import datetime

def exercise_of(recording):
    """Return (id, name) for a recording; legacy string exercises use the name as id."""
    exercise=recording.get('exercise')
    if isinstance(exercise,dict):
        name=exercise.get('name') or exercise.get('id') or 'Exercise'
        return str(exercise.get('id') or name), str(name)
    name=str(exercise) if exercise else 'Exercise'
    return name, name

def is_bicep_curl(recording):
    exercise_id,name=exercise_of(recording)
    text=f'{exercise_id} {name}'.casefold()
    return 'bicep' in text or 'curl' in text

def recording_time(recording):
    for key in ('started_at','ended_at'):
        value=recording.get(key)
        if isinstance(value,datetime): return value
        if isinstance(value,str):
            try: return datetime.fromisoformat(value.replace('Z','+00:00'))
            except ValueError: pass
    return None

def _count(recording,key):
    value=recording.get(key)
    return int(value) if finite(value) else None

def session_trend_frame(recordings):
    """One row per recording and classification; recordings without counts are skipped."""
    rows=[]
    for recording in recordings:
        when=recording_time(recording)
        if when is None: continue
        counts={'Typical':_count(recording,'num_typical'),'Outside baseline':_count(recording,'num_atypical'),'Unassessed':_count(recording,'num_unassessed')}
        if all(v is None for v in counts.values()):
            total=_count(recording,'num_reps')
            if total is None: continue
            counts={'Unassessed':total}
        for label,value in counts.items():
            if value is not None: rows.append({'session':recording.get('id'),'time':when,'classification':label,'reps':value})
    return rows

def rep_duration_frame(recordings):
    """Mean measured rep duration per recording; null durations (manual sets) are excluded."""
    rows=[]
    for recording in recordings:
        when=recording_time(recording)
        durations=[r.get('duration_sec') for r in recording.get('rep_assessments') or [] if finite(r.get('duration_sec'))]
        if when is None or not durations: continue
        rows.append({'session':recording.get('id'),'time':when,'mean':sum(durations)/len(durations),'min':min(durations),'max':max(durations),'reps':len(durations)})
    return rows

def metric_trend_frame(recordings,key):
    """Per-recording mean of one assessable per-rep metric, with that recording's own baseline band."""
    rows=[]
    for recording in recordings:
        when=recording_time(recording)
        values,band=metric_frame(recording,key)
        if when is None or not values: continue
        nums=[v['value'] for v in values]
        row={'session':recording.get('id'),'time':when,'mean':sum(nums)/len(nums),'min':min(nums),'max':max(nums),'outside':sum(v['status']=='Outside baseline' for v in values),'reps':len(nums)}
        if band: row.update(lower=band['lower'],upper=band['upper'])
        rows.append(row)
    return rows

def metric_by_rep_frame(recordings,key):
    """Stored per-rep metric values exactly as read, one row per rep; reps with no stored value are skipped."""
    rows=[]
    for recording in recordings:
        when=recording_time(recording)
        if when is None: continue
        for row in recording.get('rep_assessments') or []:
            value=(row.get('metrics') or {}).get(key)
            if finite(value) and finite(row.get('rep')):
                rows.append({'session':recording.get('id'),'time':when,'rep':int(row['rep']),'value':value,'classification':row.get('classification')})
    return rows

PAIN_PHASES=(('before','Before exercise'),('after','After exercise'))

def pain_answers(recording,daily=None):
    """{phase: (answer, source)}: dailySurveys doc first, else the copy embedded in the session. Values unchanged."""
    embedded=recording.get('pain') if isinstance(recording.get('pain'),dict) else {}
    result={}
    for phase,_ in PAIN_PHASES:
        if isinstance((daily or {}).get(phase),dict): result[phase]=(daily[phase],'dailySurveys')
        elif isinstance(embedded.get(phase),dict): result[phase]=(embedded[phase],'session record')
    return result

def pain_frame(recordings,daily_by_date):
    """One row per local_date and phase with the stored 0-10 pain value; dates without a value are skipped."""
    rows,seen=[],set()
    for recording in recordings:
        date=recording.get('local_date')
        if not date or date in seen: continue
        seen.add(date)
        for phase,label in PAIN_PHASES:
            answer=pain_answers(recording,daily_by_date.get(date)).get(phase)
            if answer and finite(answer[0].get('pain')):
                rows.append({'date':date,'phase':label,'pain':answer[0]['pain'],'source':answer[1]})
    return rows
