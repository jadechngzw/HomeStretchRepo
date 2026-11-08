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
