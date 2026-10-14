"""Exercise real Tk with simulated all-sensor BLE; saves only under /tmp."""
import sys,tempfile,time,os,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.cache/matplotlib'))
import tkinter as tk
from desktop.controller import Controller
from desktop.ui.window import Window
root=tk.Tk();controller=Controller(demo=True);window=Window(root,controller)
folder=Path(tempfile.mkdtemp(prefix='vitalwave-v3-gui-'));window.folder.set(str(folder))
window.select_leds(15);window.imu_rate.set('50');window.temp_rate.set('2')
phase=0;began=time.monotonic();started=0;failure=None

def step():
    global phase,started,failure
    try:
        if time.monotonic()-began>70:raise AssertionError('GUI integration timed out')
        if phase==0:window.action('scan');phase=1
        elif phase==1 and window.devices and not window.busy:window.connect();phase=2
        elif phase==2 and window.connected and not window.busy:window.button_press(1,0);phase=3
        elif phase==3 and window.recording:
            started=time.monotonic();window.button_press(2,1234);phase=4
        elif phase==4 and time.monotonic()-started>17:
            assert 'bpm' in window.live_text.get(),window.live_text.get()
            assert float(window.scroll.cget('scrollregion').split()[3])>root.winfo_height()
            window.show_vars[2].set(False);window.layout_plots();assert not window.plots[2].frame.winfo_manager()
            window.button_press(1,17000);phase=5
        elif phase==5 and not window.recording and not window.busy:
            reports=list((folder/'.recovery').glob('*.json'));assert len(reports)==1
            report=json.loads(reports[0].read_text());assert report['complete'] and report['demo'] and report['received']>4000
            assert not list(folder.glob('*.csv'))
            assert len(report['markers'])==1 and report['markers'][0]['watch_ms']==1234
            assert all(window.history[k] for k in range(1,8))
            assert max(t for h in window.history.values() for t,_ in h)<30
            assert 'unavailable' in window.power.get()
            window.plots[6].figure.savefig(folder/'green-live.png')
            controller.submit('export',folder/'export.csv');phase=6
        elif phase==6 and (folder/'export.json').exists():
            controller.submit('process');phase=7
        elif phase==7 and list(folder.glob('*analysis*/report.html')) and not window.processing:
            print('PASS: all-sensor Tk recording, live HR, plots, scrolling, buttons, Stop drain, separate Save and PPG report:',folder,flush=True)
            phase=8;root.after(500,window.close);return
    except Exception as e:
        failure=e;print('FAIL:',repr(e),flush=True);window.close();return
    root.after(100,step)
root.after(100,step);root.mainloop();controller.loop.call_soon_threadsafe(controller.loop.stop)
if failure:raise failure
