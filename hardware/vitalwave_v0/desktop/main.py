#!/usr/bin/env python3
import argparse,os,sys,logging,faulthandler
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.cache/matplotlib'))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--demo',action='store_true',help='Clearly labelled simulated watch; no Bluetooth');args=ap.parse_args()
    logs=ROOT/'logs';logs.mkdir(exist_ok=True)
    logging.basicConfig(filename=logs/'app.log',level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    crash=(logs/'crash.log').open('a');faulthandler.enable(crash)
    import tkinter as tk
    from desktop.controller import Controller
    from desktop.ui.window import Window
    root=tk.Tk();controller=Controller(args.demo);window=Window(root,controller)
    def report(exc,value,tb):
        logging.error('Tk callback error',exc_info=(exc,value,tb));window.message.set('Display error recorded in logs/app.log: '+str(value))
    root.report_callback_exception=report;root.mainloop()
    controller.loop.call_soon_threadsafe(controller.loop.stop)
if __name__=='__main__':main()
