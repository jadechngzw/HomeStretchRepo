import numpy as np
from desktop.processing.ppg import filtered_segments

def test_plot_omits_settling_and_does_not_join_missing_data():
    t=np.arange(0,24,.02);x=10000+100*np.sin(2*np.pi*1.2*t)
    x[(t>=10)&(t<11)]=np.nan
    y=filtered_segments(t,x)
    assert np.all(np.isnan(y[t<5]))
    assert np.any(np.isfinite(y[(t>5)&(t<9)]))
    assert np.all(np.isnan(y[(t>=10)&(t<16)]))
    assert np.any(np.isfinite(y[(t>16)&(t<22)]))
    assert np.all(np.isnan(y[t>23]))
    live=filtered_segments(t,x,causal=True)
    assert np.all(np.isnan(live[t<3])) and np.isfinite(live[-1])
