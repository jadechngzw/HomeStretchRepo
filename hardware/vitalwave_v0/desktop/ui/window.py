"""Scrollable recorder; Tk is isolated from BLE, file work and PPG analysis."""
import queue,time,json,logging,webbrowser
from collections import deque
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from desktop.protocol import Settings
from desktop.processing.ppg import filtered_segments

NAMES={1:'Accelerometer',2:'Gyroscope',3:'Temperature',8:'Humidity',4:'Infrared PPG',5:'Red PPG',6:'Green PPG',7:'Blue PPG'}
COLOURS={4:'#7256a0',5:'#c94a4a',6:'#238550',7:'#3876cb'}

class Plot:
    def __init__(self,parent,kind):
        self.kind=kind;self.frame=ttk.Frame(parent);self.figure=Figure(figsize=(10,2.25),dpi=90,layout='constrained')
        self.ax=self.figure.add_subplot();self.ax.set_title(NAMES[kind],loc='left',fontsize=11)
        self.ax.set_xlabel('Recording time (s)',fontsize=9);self.ax.grid(alpha=.2)
        self.lines=[self.ax.plot([],[],lw=1,color=c,label=n)[0] for c,n in (zip(('#167c80','#d47831','#7c59aa'),('X','Y','Z')) if kind in (1,2) else [(COLOURS.get(kind,'#167c80'),'')])]
        if kind in (1,2):self.ax.legend(loc='upper right',ncol=3,fontsize=8)
        self.canvas=FigureCanvasTkAgg(self.figure,master=self.frame);self.canvas.get_tk_widget().configure(height=225);self.canvas.get_tk_widget().pack(fill='x')
    def draw(self,history,mode):
        source=3 if self.kind==8 else self.kind;h=list(history[source])
        if not h:
            for line in self.lines:line.set_data([],[])
            self.canvas.draw_idle();return
        t=np.array([r[0] for r in h]);v=np.array([r[1] for r in h]);select=t>=t[-1]-20;t=t[select];v=v[select]
        if self.kind>=4 and self.kind!=8:
            x=v[:,0]
            if mode=='Filtered':x=filtered_segments(t,x,causal=True)
            elif mode=='Centred':x=x-np.nanmean(x) if np.any(np.isfinite(x)) else x
            v=x[:,None];unit='Filtered counts' if mode=='Filtered' else 'ADC counts'
        elif self.kind==8:v=v[:,1:2];unit='% RH'
        else:unit={1:'g',2:'°/s',3:'°C'}[self.kind]
        for i,line in enumerate(self.lines):line.set_data(t,v[:,i])
        self.ax.set_ylabel(unit,fontsize=9);self.ax.relim();self.ax.autoscale_view();self.ax.set_xlim(max(0,t[-1]-20),max(20,t[-1]));self.canvas.draw_idle()

class Window:
    def __init__(self,root,controller):
        self.root=root;self.controller=controller;self.connected=False;self.recording=False;self.busy=False;self.processing=False;self.watch_fault=False;self.devices=[];self.first_ms=None;self.received=0;self.started=None;self.last_seconds=0;self.finished_path=None;self.button_counts=None;self.last_telemetry_ms=None;self.closed=False;self.last_draw=0;self.dirty=True
        self.history={i:deque(maxlen=2400) for i in range(1,8)};self.plots={};self.setup_widgets=[];self.setting_widgets=[]
        root.title('VitalWave'+(' — DEMO / SIMULATED' if controller.demo else ''));root.geometry('1120x820');root.minsize(900,620)
        style=ttk.Style();style.theme_use('clam');style.configure('.',font=('Helvetica',11),background='#f4f7fa',foreground='#172b3a');style.configure('TButton',padding=(9,6));style.configure('TLabelframe',padding=10)
        shell=ttk.Frame(root);shell.pack(fill='both',expand=True)
        self.scroll=tk.Canvas(shell,highlightthickness=0,bg='#f4f7fa');bar=ttk.Scrollbar(shell,orient='vertical',command=self.scroll.yview);bar.pack(side='right',fill='y');self.scroll.pack(side='left',fill='both',expand=True);self.scroll.configure(yscrollcommand=bar.set)
        outer=ttk.Frame(self.scroll,padding=16);item=self.scroll.create_window((0,0),window=outer,anchor='nw')
        outer.bind('<Configure>',lambda e:self.scroll.configure(scrollregion=self.scroll.bbox('all')));self.scroll.bind('<Configure>',lambda e:self.scroll.itemconfigure(item,width=e.width))
        root.bind('<MouseWheel>',self.wheel,add='+');root.bind('<Button-4>',lambda e:self.scroll.yview_scroll(-3,'units'));root.bind('<Button-5>',lambda e:self.scroll.yview_scroll(3,'units'))
        header=ttk.Frame(outer);header.pack(fill='x');ttk.Label(header,text='VitalWave / Sensor recorder',font=('Helvetica',21,'bold')).pack(side='left')
        self.connection=tk.StringVar(value='Disconnected');ttk.Label(header,textvariable=self.connection).pack(side='right')
        if controller.demo:ttk.Label(outer,text='DEMO — simulated signals; no watch connection.',foreground='#a04400').pack(anchor='w')
        conn=ttk.LabelFrame(outer,text='Connect');conn.pack(fill='x',pady=10)
        self.scan_button=ttk.Button(conn,text='Scan',command=lambda:self.action('scan'));self.scan_button.pack(side='left')
        self.device_combo=ttk.Combobox(conn,state='readonly');self.device_combo.pack(side='left',fill='x',expand=True,padx=8)
        self.connect_button=ttk.Button(conn,text='Connect',command=self.connect);self.connect_button.pack(side='left')
        self.disconnect_button=ttk.Button(conn,text='Disconnect',command=lambda:self.action('disconnect'));self.disconnect_button.pack(side='left',padx=6)
        setup=ttk.LabelFrame(outer,text='Record these sensors');setup.pack(fill='x');setup.columnconfigure(1,weight=1)
        self.name=tk.StringVar(value='demo_session' if controller.demo else 'session');self.folder=tk.StringVar(value=str(Path(__file__).resolve().parents[2]/'recordings'))
        for row,(label,var) in enumerate([('Recording name',self.name),('Save folder',self.folder)]):
            ttk.Label(setup,text=label).grid(row=row,column=0,sticky='w',padx=5);entry=ttk.Entry(setup,textvariable=var);entry.grid(row=row,column=1,sticky='ew',pady=4);self.setup_widgets.append(entry)
        self.browse=ttk.Button(setup,text='Choose…',command=self.choose);self.browse.grid(row=1,column=2,padx=6);self.setup_widgets.append(self.browse)
        sensors=ttk.Frame(setup);sensors.grid(row=2,column=0,columnspan=3,sticky='w',pady=8)
        self.acceleration=tk.BooleanVar(value=True);self.gyroscope=tk.BooleanVar(value=True);self.temperature=tk.BooleanVar(value=True);self.ppg_enabled=tk.BooleanVar(value=False)
        for label,var in [('Accelerometer',self.acceleration),('Gyroscope',self.gyroscope),('Temperature + humidity',self.temperature),('PPG enabled',self.ppg_enabled)]:
            w=ttk.Checkbutton(sensors,text=label,variable=var);w.pack(side='left',padx=6);self.setup_widgets.append(w)
        optical=ttk.Frame(setup);optical.grid(row=3,column=0,columnspan=3,sticky='w')
        ttk.Label(optical,text='PPG colours:').pack(side='left');self.led_vars={}
        for bit,label in [(1,'Infrared'),(2,'Red'),(4,'Green'),(8,'Blue')]:
            var=tk.BooleanVar(value=bit==4);self.led_vars[bit]=var;w=ttk.Checkbutton(optical,text=label,variable=var);w.pack(side='left',padx=5);self.setup_widgets.append(w)
        for label,bits in [('Red + IR',3),('All',15),('None',0)]:
            w=ttk.Button(optical,text=label,command=lambda b=bits:self.select_leds(b));w.pack(side='left',padx=4);self.setup_widgets.append(w)
        rates=ttk.Frame(setup);rates.grid(row=4,column=0,columnspan=3,sticky='w',pady=8)
        def choice(parent,label,values,default,width=9):
            ttk.Label(parent,text=label).pack(side='left',padx=5);var=tk.StringVar(value=default);w=ttk.Combobox(parent,textvariable=var,values=values,state='readonly',width=width);w.pack(side='left',padx=5);self.setting_widgets.append(w);return var
        self.imu_rate=choice(rates,'IMU Hz',(10,25,50),'25');self.temp_rate=choice(rates,'Temp/RH Hz',(.5,1,2),'1');self.ppg_rate=choice(rates,'PPG Hz',(50,100),'50')
        ttk.Label(setup,text='Multiple PPG colours: 50 Hz each. Raw data are always preserved.',foreground='#526575').grid(row=5,column=0,columnspan=3,sticky='w')
        buttons=ttk.Frame(setup);buttons.grid(row=6,column=0,columnspan=3,sticky='w',pady=6);actions=('Start / Stop','Add marker','Disabled')
        self.button1=choice(buttons,'Button 1',actions,'Start / Stop',14);self.button2=choice(buttons,'Button 2',actions,'Add marker',14)
        controls=ttk.Frame(outer);controls.pack(fill='x',pady=10)
        self.start_button=ttk.Button(controls,text='Start',command=self.start);self.start_button.pack(side='left')
        self.stop_button=ttk.Button(controls,text='Stop',command=lambda:self.action('stop'));self.stop_button.pack(side='left',padx=6)
        self.save_button=ttk.Button(controls,text='Save as…',command=self.save);self.save_button.pack(side='left',padx=6)
        self.process_button=ttk.Button(controls,text='Process PPG',command=lambda:self.controller.submit('process'));self.process_button.pack(side='left',padx=6)
        self.open_button=ttk.Button(controls,text='Analyse existing CSV…',command=self.analyse_existing);self.open_button.pack(side='left',padx=6)
        self.elapsed=tk.StringVar(value='00:00');ttk.Label(controls,textvariable=self.elapsed).pack(side='right')
        self.power=tk.StringVar(value='Charging status unavailable');ttk.Label(outer,textvariable=self.power).pack(anchor='w')
        self.values=tk.StringVar(value='Waiting for samples');ttk.Label(outer,textvariable=self.values,wraplength=950).pack(anchor='w',pady=5)
        view=ttk.LabelFrame(outer,text='Show these plots (does not change recording)');view.pack(fill='x',pady=8);self.show_vars={}
        for i,kind in enumerate([1,2,3,8,4,5,6,7]):
            var=tk.BooleanVar(value=kind in (1,2,3));self.show_vars[kind]=var;ttk.Checkbutton(view,text=NAMES[kind],variable=var,command=self.layout_plots).grid(row=i//4,column=i%4,sticky='w',padx=8,pady=3)
        display=ttk.Frame(outer);display.pack(fill='x')
        ttk.Label(display,text='PPG display:').pack(side='left');self.display_mode=tk.StringVar(value='Filtered');w=ttk.Combobox(display,textvariable=self.display_mode,values=('Raw','Centred','Filtered'),state='readonly',width=12);w.pack(side='left',padx=8);w.bind('<<ComboboxSelected>>',lambda e:self.mark_dirty())
        self.live_enabled=tk.BooleanVar(value=True);ttk.Checkbutton(display,text='Show preliminary live heart rate',variable=self.live_enabled,command=self.clear_live).pack(side='left')
        self.live_text=tk.StringVar(value='Heart rate: waiting for 13 seconds of data. Estimates use recent 8-second windows.');ttk.Label(outer,textvariable=self.live_text,wraplength=950,foreground='#526575').pack(anchor='w',pady=6)
        self.plot_parent=ttk.Frame(outer);self.plot_parent.pack(fill='x');self.layout_plots()
        self.message=tk.StringVar(value='Stop retains a recovery copy. Save as exports it. Filtering is not motion compensation.');ttk.Label(root,textvariable=self.message,wraplength=1000,padding=10).pack(fill='x')
        self.preferences=Path(__file__).resolve().parents[2]/'desktop_preferences.json';self.load_preferences()
        root.protocol('WM_DELETE_WINDOW',self.close);self.refresh_buttons();root.after(100,self.poll)
    def wheel(self,e):
        if isinstance(e.widget,ttk.Combobox):return
        self.scroll.yview_scroll(-int(e.delta if abs(e.delta)<120 else e.delta/120),'units')
    def mark_dirty(self):self.dirty=True
    def clear_live(self):
        if not self.live_enabled.get():self.live_text.set('Live heart-rate display off.')
    def select_leds(self,bits):
        for bit,var in self.led_vars.items():var.set(bool(bits&bit))
        self.ppg_enabled.set(bool(bits))
        if bits&(bits-1):self.ppg_rate.set('50')
    def layout_plots(self):
        for p in self.plots.values():p.frame.pack_forget()
        for k in [1,2,3,8,4,5,6,7]:
            if self.show_vars[k].get():
                if k not in self.plots:self.plots[k]=Plot(self.plot_parent,k)
                self.plots[k].frame.pack(fill='x',pady=5)
        self.dirty=True
    def load_preferences(self):
        if self.controller.demo:return
        try:
            d=json.loads(self.preferences.read_text())
            for name,allowed in [('imu_rate',('10','25','50')),('temp_rate',('.5','0.5','1','2')),('ppg_rate',('50','100')),('button1',('Start / Stop','Add marker','Disabled')),('button2',('Start / Stop','Add marker','Disabled'))]:
                if d.get(name) in allowed:getattr(self,name).set(d[name])
            if isinstance(d.get('leds'),int) and 0<=d['leds']<=15:self.select_leds(d['leds'])
            self.ppg_enabled.set(bool(d.get('ppg_enabled',False)))
        except (OSError,ValueError,TypeError,AttributeError):pass
    def save_preferences(self):
        if self.controller.demo:return
        d={n:getattr(self,n).get() for n in ('imu_rate','temp_rate','ppg_rate','button1','button2','ppg_enabled')};d['leds']=sum(b for b,v in self.led_vars.items() if v.get())
        try:self.preferences.write_text(json.dumps(d,indent=2)+'\n')
        except OSError:logging.exception('Preferences could not be saved')
    def action(self,method,*args):
        if self.busy:return
        self.busy=True;self.refresh_buttons();self.message.set({'stop':'Stopping; waiting for remaining samples…','start':'Starting…','scan':'Scanning…'}.get(method,'Working…'));self.controller.submit(method,*args)
    def choose(self):
        p=filedialog.askdirectory(initialdir=self.folder.get())
        if p:self.folder.set(p)
    def connect(self):
        i=self.device_combo.current()
        if i>=0:device,name,_=self.devices[i];self.action('connect',device,name)
    def start(self):
        if self.busy or self.recording:return
        leds=sum(b for b,v in self.led_vars.items() if v.get()) if self.ppg_enabled.get() else 0
        if self.ppg_enabled.get() and not leds:self.message.set('Choose at least one PPG colour, or disable PPG.');return
        mask=int(self.acceleration.get())|int(self.temperature.get())<<1|(4 if leds else 0)|(8 if self.gyroscope.get() else 0)
        if not mask:self.message.set('Choose at least one sensor.');return
        rate=int(self.ppg_rate.get())
        if leds&(leds-1):rate=50;self.ppg_rate.set('50')
        settings=Settings(int(self.imu_rate.get()),round(1000/float(self.temp_rate.get())),rate,leds)
        self.first_ms=None;self.received=0;self.started=None;self.last_seconds=0;self.live_text.set('Heart rate: warming up (13 seconds).')
        for h in self.history.values():h.clear()
        while True:
            try:self.controller.plot_samples.get_nowait()
            except queue.Empty:break
        for k in self.show_vars:self.show_vars[k].set(bool({1:mask&1,2:mask&8,3:mask&2,8:0,4:leds&1,5:leds&2,6:leds&4,7:leds&8}[k]))
        self.layout_plots();self.save_preferences();self.action('start',self.folder.get(),self.name.get(),mask,settings)
    def save(self):
        if not self.finished_path:return
        p=filedialog.asksaveasfilename(initialdir=self.folder.get(),initialfile=Path(self.finished_path).name,defaultextension='.csv',filetypes=[('CSV','*.csv')])
        if p:self.controller.submit('export',p)
    def analyse_existing(self):
        p=filedialog.askopenfilename(initialdir=self.folder.get(),filetypes=[('CSV','*.csv')])
        if p:self.controller.submit('process',p)
    def button_press(self,number,watch_ms):
        if self.busy or not self.connected:return
        act=(self.button1 if number==1 else self.button2).get()
        if act=='Start / Stop':
            if self.recording:self.action('stop')
            elif not self.watch_fault:self.start()
        elif act=='Add marker' and self.recording:self.controller.submit('marker',watch_ms,number)
    def refresh_buttons(self):
        def state(w,yes):w.configure(state='normal' if yes else 'disabled')
        state(self.scan_button,not self.connected and not self.busy);state(self.connect_button,bool(self.devices) and not self.connected and not self.busy)
        state(self.disconnect_button,self.connected and not self.busy);state(self.start_button,self.connected and not self.recording and not self.busy and not self.watch_fault)
        state(self.stop_button,self.recording and not self.busy);state(self.save_button,bool(self.finished_path) and not self.recording and not self.busy)
        state(self.process_button,bool(self.finished_path) and not self.recording and not self.processing);state(self.open_button,not self.recording and not self.processing)
        for w in self.setup_widgets:state(w,not self.recording and not self.busy)
        for w in self.setting_widgets:w.configure(state='readonly' if not self.recording and not self.busy else 'disabled')
    def event(self,event,payload):
        if event=='devices':
            self.devices=payload;self.device_combo['values']=[f'{name} · {rssi} dBm' for _,name,rssi in payload]
            if payload:self.device_combo.current(0)
            self.message.set(f'Found {len(payload)} watch(es).')
        elif event=='connection':
            self.connected=payload;self.busy=False;self.connection.set('Connected' if payload else 'Disconnected')
            if not payload:self.button_counts=None;self.power.set('Disconnected · Charging status unavailable')
        elif event=='busy':self.busy=payload
        elif event=='recording':
            self.recording=payload
            if payload:self.started=time.monotonic();self.message.set('Recording. Raw data are written to a recovery file.')
        elif event=='status':
            self.watch_fault=payload.state==2
            if self.watch_fault:self.message.set(f'Watch fault {payload.reason}; data retained. Check sensor/power connection.')
        elif event=='telemetry':
            self.power.set(payload.text);self.last_telemetry_ms=payload.watch_ms;counts=(payload.button1,payload.button2)
            if self.button_counts is not None:
                for i in range(2):
                    if ((counts[i]-self.button_counts[i])&65535)==1:self.button_press(i+1,payload.watch_ms)
            self.button_counts=counts
        elif event=='live' and self.live_enabled.get():
            parts=[NAMES[k]+': '+(f'{v["bpm"]:.0f} bpm (preliminary)' if v['bpm'] is not None else v['quality']) for k,v in payload.items()];self.live_text.set(' | '.join(parts))
        elif event=='marker':self.message.set(f'Marker {payload} retained.')
        elif event=='stopped':
            self.finished_path,meta=payload;self.busy=False
            self.message.set(('Stopped; complete data. ' if meta['complete'] else 'Stopped; incomplete data: '+meta['reason']+'. ')+'Recovery copy retained. Use Save as to export.')
        elif event=='exported':self.finished_path=payload;self.message.set('Saved: '+payload)
        elif event=='processing':self.processing=payload;self.message.set('Processing PPG…' if payload else 'PPG analysis finished.')
        elif event=='processed':
            path,result=payload;win=tk.Toplevel(self.root);win.title('PPG analysis');win.geometry('650x350')
            text='Preliminary heart-rate estimates (accepted windows only)\n\n'
            for k,v in result['channels'].items():text+=k.replace('ppg_','').title()+': '+('Unavailable' if v['average_bpm'] is None else f'{v["average_bpm"]:.1f} bpm')+f' — {v["accepted_windows"]}/{v["total_windows"]} windows\n'
            text+='\nSpO₂: '+result['spo2']['reason']
            ttk.Label(win,text=text,wraplength=610,padding=16).pack(fill='x');ttk.Button(win,text='Open full plots and report',command=lambda:webbrowser.open(Path(path).as_uri())).pack(pady=10)
        elif event=='error':self.message.set('Error: '+payload);self.busy=False
        elif event=='closed':self.closed=True;self.root.destroy()
    def poll(self):
        try:
            for _ in range(200):
                try:event,payload=self.controller.events.get_nowait()
                except queue.Empty:break
                self.event(event,payload)
                if self.closed:return
            for _ in range(800):
                try:s=self.controller.plot_samples.get_nowait()
                except queue.Empty:break
                self.received+=1
                if self.first_ms is None:self.first_ms=s.watch_ms
                # Earlier timestamps from another sensor are small negatives, not 49-day jumps.
                t=((s.watch_ms-self.first_ms+0x80000000)&0xffffffff)-0x80000000
                v=tuple(float('nan') if x is None else x for x in s.values());self.history[s.kind].append((t/1000,v));self.dirty=True
            now=time.monotonic()
            if self.dirty and now-self.last_draw>=.5:
                for k,p in self.plots.items():
                    if self.show_vars[k].get():p.draw(self.history,self.display_mode.get())
                self.last_draw=now;self.dirty=False
                if self.history[3]:
                    v=self.history[3][-1][1];self.values.set(f'Temperature {v[0]:.2f} °C · Humidity {v[1]:.2f}% · {self.received} displayed frames')
            if self.started and self.recording:self.last_seconds=int(now-self.started)
            self.elapsed.set(f'{self.last_seconds//60:02}:{self.last_seconds%60:02}');self.refresh_buttons()
        except Exception:
            logging.exception('GUI update failed');self.message.set('Display error logged; raw recording continues. See logs/app.log.')
        finally:
            if not self.closed:self.root.after(100,self.poll)
    def close(self):
        self.save_preferences();self.busy=True;self.refresh_buttons();self.message.set('Stopping and retaining recovery data…');self.controller.submit('shutdown')
