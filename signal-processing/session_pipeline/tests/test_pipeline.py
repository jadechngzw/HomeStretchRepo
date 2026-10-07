import csv
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from session_pipeline.reader import load_recording
from session_pipeline.pipeline import process, save_result
from session_pipeline.ppg import summarize
from session_pipeline.motion import summarize as motion
from session_pipeline.upload import make_document

CONFIG=json.loads(Path(__file__).parents[1].joinpath('exercises.json').read_text())['bicep_curl']


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def recording(self, invalid=False, wrap=False, flat=False):
        path=self.root/'input.csv';rows=[];sid=42
        for i,t in enumerate(np.arange(1601)*.02):
            ms=(round(t*1000)+(2**32-1000 if wrap else 1000))%2**32
            valid=0 if invalid and 400<=i<=405 else 1
            rows += [dict(session_id=sid,sequence=len(rows)%65536,watch_ms=ms,sensor='acceleration',valid=valid,
                          x=0,y=0 if flat else np.cos(2*np.pi*t/2.5),z=1),
                     dict(session_id=sid,sequence=(len(rows)+1)%65536,watch_ms=ms,sensor='gyroscope',valid=valid,
                          x=0 if flat else 100*np.sin(2*np.pi*t/2.5),y=0,z=0),
                     dict(session_id=sid,sequence=(len(rows)+2)%65536,watch_ms=ms,sensor='ppg_green',valid=1,
                          x=50000 if flat else 50000+1000*np.sin(2*np.pi*1.2*t),y='',z='')]
        with path.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        meta=dict(format_version=2,protocol_version=3,session_id=sid,started_utc='2026-10-04T00:00:00+00:00',
                  ended_utc='2026-10-04T00:00:32+00:00',complete=not invalid,received=len(rows),
                  final_status=dict(generated=len(rows),dropped=0,state=0,reason=0,session=sid))
        path.with_suffix('.json').write_text(json.dumps(meta));return path
    def result(self, **kwargs):
        return process(self.recording(**kwargs),patient_id='test',exercise_id='bicep_curl',body_side='right')
    def test_all_orientation_exercises_use_orientation_adapter(self):
        configs=json.loads(Path(__file__).parents[1].joinpath('exercises.json').read_text())
        self.assertEqual(len(configs),15)
        source=self.recording()
        for exercise in configs:
            if exercise=='bicep_curl':continue
            with self.subTest(exercise=exercise):
                r=process(source,patient_id='test',exercise_id=exercise,body_side='right',orientation_classification=False)
                self.assertIsNotNone(r['imu']['accepted_reps'])
                self.assertEqual(r['processing']['classifier']['status'],'experimental_transfer')
                self.assertGreater(r['hr']['bpm'],0)
                self.assertTrue(any(f['code']=='EXPERIMENTAL_ORIENTATION' for f in r['guidance']['flags']))
                json.dumps(make_document(r),allow_nan=False)

    def test_schema_counts_and_strict_json(self):
        r=self.result();json.dumps(r,allow_nan=False)
        self.assertTrue(r['recording']['complete'])
        self.assertEqual(len(r['imu']['rep_durations']),r['imu']['accepted_reps'])
        self.assertEqual(r['imu']['unknown_reps'],r['imu']['accepted_reps'])
        self.assertIsNone(r['imu']['typical_reps'])
        self.assertEqual(r['guidance']['patient_state'],'Unknown')
    def test_rollover_keeps_shared_time(self):
        rec=load_recording(self.recording(wrap=True))
        self.assertAlmostEqual(rec['duration'],32)
        np.testing.assert_allclose(rec['streams']['acceleration'][:,0],rec['streams']['ppg_green'][:,0])
    def test_identity_mismatch_rejected(self):
        p=self.recording();m=json.loads(p.with_suffix('.json').read_text());m['session_id']=99
        p.with_suffix('.json').write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'session IDs'):load_recording(p)
    def test_incomplete_and_long_gap_not_bridged(self):
        r=self.result(invalid=True)
        self.assertFalse(r['recording']['complete'])
        self.assertGreater(r['imu']['unscorable_time'],0)
        self.assertFalse(any(rep['start_sec']<8 and rep['end_sec']>8.12 for rep in r['imu']['repetitions']))
    def test_timing_partition(self):
        r=self.result(invalid=True);imu=r['imu']
        self.assertAlmostEqual(imu['active_time']+imu['rest_time']+imu['unscorable_time'],imu['duration'],places=5)
    def test_flat_has_no_pulse_and_no_reps(self):
        r=self.result(flat=True)
        self.assertEqual(r['imu']['accepted_reps'],0)
        self.assertIsNone(r['hr']['bpm']);self.assertIsNone(r['imu']['smoothness'])
    def test_known_pulse_and_coverage_no_double_count(self):
        r=self.result();hr=r['hr']
        self.assertAlmostEqual(hr['bpm'],72,delta=2)
        self.assertLessEqual(hr['valid_signal_duration_sec'],hr['analysis_duration_sec'])
        iv=hr['valid_intervals']
        self.assertTrue(all(a['end_sec']<=b['start_sec'] for a,b in zip(iv,iv[1:])))
    def test_missing_channel_and_threshold(self):
        h=summarize(None,30,'ppg_red',100)
        self.assertIsNone(h['bpm']);self.assertIsNone(h['time_above_max_hr_sec'])
    def test_no_implicit_threshold(self):
        self.assertIsNone(self.result()['hr']['time_above_max_hr_sec'])
    def test_exclusive_output(self):
        r=self.result();p=self.root/'result.json';save_result(r,p)
        with self.assertRaises(FileExistsError):save_result(r,p)
    def test_firestore_adapter_no_cloud_needed(self):
        r=self.result();d=make_document(r)
        self.assertEqual(d['num_reps'],r['imu']['accepted_reps']);self.assertIsNone(d['num_typical'])
    def test_unknown_exercise_fails(self):
        with self.assertRaisesRegex(ValueError,'Unsupported exercise'):
            process(self.recording(),patient_id='test',exercise_id='unknown',body_side='right')

if __name__=='__main__':unittest.main()
