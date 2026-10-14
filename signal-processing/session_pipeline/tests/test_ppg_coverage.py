import unittest
from unittest.mock import patch
import numpy as np
from session_pipeline.ppg import summarize,merge_estimates

class CoverageTests(unittest.TestCase):
    def test_overlaps_partition_and_median(self):
        windows=[dict(start_sec=0,end_sec=6,bpm=60),dict(start_sec=3,end_sec=9,bpm=100)]
        pieces=merge_estimates(windows)
        self.assertEqual(pieces,[dict(start_sec=0,end_sec=3,bpm=60),dict(start_sec=3,end_sec=6,bpm=80),dict(start_sec=6,end_sec=9,bpm=100)])
        self.assertEqual(sum(w['end_sec']-w['start_sec'] for w in pieces),9)
    def test_full_acceptance_counts_seconds_not_windows(self):
        t=np.arange(1601)*.02;s=np.column_stack([t,np.ones(len(t))*50000,np.zeros((len(t),2)),np.ones(len(t))])
        with patch('session_pipeline.ppg.estimate',return_value=dict(bpm=110,quality='test')):
            r=summarize(s,32,'ppg_green',100)
        self.assertEqual(r['valid_signal_duration_sec'],25)
        self.assertEqual(r['time_above_max_hr_sec'],25)
        self.assertEqual(r['accepted_of_evaluated_pct'],100)
        self.assertEqual(r['valid_signal_coverage_pct'],78.125)
    def test_invalid_samples_not_accepted(self):
        t=np.arange(1601)*.02;s=np.column_stack([t,np.ones(len(t))*50000,np.zeros((len(t),2)),np.zeros(len(t))])
        with patch('session_pipeline.ppg.estimate') as detector:
            r=summarize(s,32,'ppg_green')
        detector.assert_not_called();self.assertEqual(r['valid_signal_duration_sec'],0)
        self.assertEqual(r['evaluated_duration_sec'],25)
if __name__=='__main__':unittest.main()
