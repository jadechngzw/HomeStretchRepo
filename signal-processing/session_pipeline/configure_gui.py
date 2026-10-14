"""Link a v0 GUI checkout to this pipeline environment. No credentials stored."""
import argparse
import json
import sys
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--gui-root',required=True)
    p.add_argument('--project',required=True)
    p.add_argument('--recordings-dir')
    args=p.parse_args();root=Path(args.gui_root).resolve();package=Path(__file__).resolve().parent
    if not (root/'desktop/homestretch.py').exists():p.exit(2,'This GUI checkout needs the HomeStretch bridge update first.\n')
    repo=package.parents[1]
    config=dict(python=sys.executable,pipeline_parent=str(package.parent),project=args.project,
                model=str(repo/'mbientcode/isolation_forest.pkl'),scaler=str(repo/'mbientcode/scaler.pkl'))
    config['recordings_dir']=str(Path(args.recordings_dir).resolve()) if args.recordings_dir else str(repo.parent/'recordings')
    path=root/'homestretch_integration.json';path.write_text(json.dumps(config,indent=2)+'\n')
    print('Configured',path)

if __name__=='__main__':main()
