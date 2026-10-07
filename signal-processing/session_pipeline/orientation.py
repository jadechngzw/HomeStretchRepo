"""Experimental six-axis body-to-world orientation; relative yaw, no heading sensor."""
import warnings
import numpy as np
from scipy.spatial.transform import Rotation


def estimate(accel, gyro, fs=50.0):
    info=dict(method='six-axis-gravity-feedback-0.1',status='unavailable',
              convention='body-to-world extrinsic xyz (Rz Ry Rx): roll X, pitch Y, relative yaw Z; output pitch,yaw,roll',
              yaw_reference='zero at each continuous block; unobservable absolute heading',
              sampling_rate_hz=fs,max_bridge_sec=.06,gravity_feedback_gain_per_sec=.5,
              calibration='unavailable',gyro_bias_dps=[0,0,0],blocks=0,
              notes=['Sensor axes are not calibrated to the REHAB anatomical frame.',
                     'Relative yaw can drift; it does not reproduce nine-axis heading.',
                     'Dynamic acceleration can disturb tilt; correction gated to 0.85–1.15 g.',
                     'Long gaps reset orientation; repetitions never cross them.'])
    if accel is None or gyro is None:return [],info
    _,ai,gi=np.intersect1d(accel[:,0],gyro[:,0],return_indices=True)
    a,g=accel[ai],gyro[gi]
    good=(a[:,4]>0)&(g[:,4]>0)&np.isfinite(a[:,1:4]).all(axis=1)&np.isfinite(g[:,1:4]).all(axis=1)
    a,g=a[good],g[good]
    if len(a)<3:return [],info
    bias=np.zeros(3)
    early=a[:,0]<=a[0,0]+2
    if early.sum()>=80 and np.max(np.diff(a[early,0]))<=.060001 and np.max(np.std(a[early,1:4],axis=0))<.03 and np.max(np.linalg.norm(g[early,1:4],axis=1))<10:
        bias=np.median(g[early,1:4],axis=0);info['calibration']='first_two_seconds_stationary'
    else:info['calibration']='no_stationary_baseline; bias not corrected'
    info['gyro_bias_dps']=bias.tolist()
    groups=np.split(np.arange(len(a)),np.flatnonzero(np.diff(a[:,0])>.060001)+1)
    blocks=[]
    for idx in groups:
        if len(idx)<20:continue
        aa,gg=a[idx],g[idx];t=np.arange(aa[0,0],aa[-1,0]+1e-7,1/fs)
        av=np.column_stack([np.interp(t,aa[:,0],aa[:,j]) for j in (1,2,3)])
        gv=np.column_stack([np.interp(t,gg[:,0],gg[:,j]) for j in (1,2,3)])-bias
        norm=np.linalg.norm(av[0]);
        if not .5<norm<1.5:continue
        ax,ay,az=av[0];roll=np.arctan2(ay,az);pitch=np.arctan2(-ax,np.hypot(ay,az))
        r=Rotation.from_euler('xyz',[roll,pitch,0]);rotations=[r.as_quat()]
        for k in range(1,len(t)):
            omega=np.deg2rad((gv[k-1]+gv[k])/2)
            magnitude=np.linalg.norm(av[k])
            if .85<=magnitude<=1.15:
                measured=av[k]/magnitude;predicted=r.inv().apply([0,0,1])
                omega+=.5*np.cross(measured,predicted)
            r=r*Rotation.from_rotvec(omega/fs);rotations.append(r.as_quat())
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UserWarning)
            euler=Rotation.from_quat(rotations).as_euler('xyz')
        singular=np.abs(np.cos(euler[:,1]))<.1
        angles=np.rad2deg(np.unwrap(euler[:,[1,2,0]],axis=0))
        right=np.clip(np.searchsorted(aa[:,0],t),0,len(aa)-1);left=np.maximum(0,right-1)
        repaired=np.minimum(abs(t-aa[right,0]),abs(t-aa[left,0]))>.002
        blocks.append(dict(time=t,angles=angles,interpolated=repaired,gimbal=singular))
    info.update(status='experimental_transfer' if blocks else 'unavailable',blocks=len(blocks),
                samples=sum(len(b['time']) for b in blocks),
                interpolated_samples=sum(int(b['interpolated'].sum()) for b in blocks),
                near_gimbal_samples=sum(int(b['gimbal'].sum()) for b in blocks))
    return blocks,info


def save_csv(blocks,path):
    import csv
    from pathlib import Path
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['block','seconds','pitch_deg','relative_yaw_deg','roll_deg','interpolated','near_gimbal_lock'])
        for index,b in enumerate(blocks):
            for t,v,repair,gimbal in zip(b['time'],b['angles'],b['interpolated'],b['gimbal']):
                writer.writerow([index,t,*v,int(repair),int(gimbal)])
