"""Overlapping PPG windows with non-overlapping time accounting."""
from collections import Counter
import numpy as np
from .ppg_reference import estimate


def merge_estimates(windows):
    """Partition accepted window centers; use median BPM where windows overlap."""
    edges=sorted({v for w in windows for v in (w['start_sec'],w['end_sec'])})
    merged=[]
    for left,right in zip(edges[:-1],edges[1:]):
        mid=(left+right)/2
        rates=[w['bpm'] for w in windows if w['start_sec']<=mid<w['end_sec']]
        if not rates or right<=left:continue
        bpm=float(np.median(rates))
        if merged and abs(merged[-1]['end_sec']-left)<1e-8 and abs(merged[-1]['bpm']-bpm)<1e-8:
            merged[-1]['end_sec']=right
        else:merged.append(dict(start_sec=left,end_sec=right,bpm=bpm))
    return merged


def summarize(stream, duration, channel, threshold=None):
    result=dict(status='unavailable',channel=channel,bpm=None,peak_hr_bpm=None,
                max_hr_bpm=threshold,time_above_max_hr_sec=None,
                valid_signal_coverage_pct=0.0,valid_signal_duration_sec=0.0,
                analysis_duration_sec=duration,threshold_status='configured' if threshold else 'not_configured',
                window_sec=8,window_step_sec=1,warmup_sec=5,valid_intervals=[],rejected_windows={},
                evaluated_duration_sec=0.0,evaluated_coverage_pct=0.0,accepted_of_evaluated_pct=0.0,
                accepted_window_count=0,evaluated_window_count=0,
                coverage_definition='Union of accepted central window intervals / full session duration; overlapping estimates use median BPM.')
    if stream is None:
        result['reason']='Selected PPG channel not recorded.';return result
    rejected=Counter();accepted=[];evaluated=[]
    for start in np.arange(float(stream[0,0])+5,float(stream[-1,0])-8+1e-6,1):
        window=stream[(stream[:,0]>=start-1e-6)&(stream[:,0]<=start+8+1e-6)]
        result['evaluated_window_count']+=1
        left,right=max(0,float(start+1)),min(duration,float(start+7))
        if right>left:evaluated.append(dict(start_sec=left,end_sec=right,bpm=0))
        if len(window)<2 or not np.all(window[:,4]):
            rejected['Invalid samples']+=1;continue
        try:e=estimate(window[:,0],window[:,1])
        except (ValueError,FloatingPointError):
            rejected['Unsupported sampling or numerical failure']+=1;continue
        bpm=e['bpm']
        if bpm is None or not np.isfinite(bpm):rejected[e['quality']]+=1;continue
        if right>left:accepted.append(dict(start_sec=left,end_sec=right,bpm=float(bpm)))
    result['rejected_windows']=dict(rejected);result['accepted_window_count']=len(accepted)
    available=sum(w['end_sec']-w['start_sec'] for w in merge_estimates(evaluated))
    result.update(evaluated_duration_sec=available,evaluated_coverage_pct=100*available/duration if duration>0 else 0)
    intervals=merge_estimates(accepted);result['valid_intervals']=intervals
    if intervals:
        weights=[w['end_sec']-w['start_sec'] for w in intervals];rates=[w['bpm'] for w in intervals];total=sum(weights)
        result.update(status='preliminary',bpm=float(np.average(rates,weights=weights)),peak_hr_bpm=max(rates),
                      valid_signal_duration_sec=total,valid_signal_coverage_pct=100*total/duration if duration>0 else 0,
                      accepted_of_evaluated_pct=100*total/available if available>0 else 0,
                      time_above_max_hr_sec=sum(w for b,w in zip(rates,weights) if b>threshold) if threshold else None)
    else:result['reason']='No analysis windows passed the exploratory PPG quality checks.'
    return result
