import unittest
import numpy as np
from scipy.spatial.transform import Rotation
from session_pipeline.orientation import estimate


def streams(t,angles):
    # angles extrinsic xyz in radians; derive body angular velocity from true rotations.
    r=Rotation.from_euler('xyz',angles)
    gravity=r.inv().apply(np.tile([0.,0.,1.],(len(t),1)))
    rates=(r[:-1].inv()*r[1:]).as_rotvec()/np.diff(t)[:,None]
    rates=np.vstack([rates[0],(rates[:-1]+rates[1:])/2,rates[-1]])
    return np.column_stack([t,gravity,np.ones(len(t))]),np.column_stack([t,np.rad2deg(rates),np.ones(len(t))])

class OrientationTests(unittest.TestCase):
    def test_known_static_tilt(self):
        t=np.arange(0,5,.02);e=np.tile(np.deg2rad([30,20,0]),(len(t),1));a,g=streams(t,e)
        blocks,info=estimate(a,g)
        np.testing.assert_allclose(blocks[0]['angles'][-1],[20,0,30],atol=.01)
        self.assertEqual(info['calibration'],'first_two_seconds_stationary')
    def test_known_dynamic_axes(self):
        t=np.arange(0,20,.02)
        for axis in range(3):
            e=np.zeros((len(t),3));e[:,axis]=np.deg2rad(30)*np.sin(2*np.pi*t/4)
            a,g=streams(t,e);blocks,_=estimate(a,g)
            expected=np.rad2deg(e[:,[1,2,0]])
            np.testing.assert_allclose(blocks[0]['angles'],expected,atol=.7)
    def test_large_gap_splits_and_small_gap_is_flagged(self):
        t=np.arange(0,8,.02);e=np.zeros((len(t),3));a,g=streams(t,e)
        a[100,4]=g[100,4]=0;a[200:210,4]=g[200:210,4]=0
        blocks,info=estimate(a,g)
        self.assertEqual(len(blocks),2);self.assertGreater(info['interpolated_samples'],0)
        self.assertLess(blocks[0]['time'][-1],blocks[1]['time'][0])
    def test_gyro_bias_is_calibrated(self):
        t=np.arange(0,5,.02);a,g=streams(t,np.zeros((len(t),3)));g[:,1:4]+=[1,2,3]
        blocks,info=estimate(a,g)
        np.testing.assert_allclose(info['gyro_bias_dps'],[1,2,3])
        np.testing.assert_allclose(blocks[0]['angles'],0,atol=.001)
if __name__=='__main__':unittest.main()
