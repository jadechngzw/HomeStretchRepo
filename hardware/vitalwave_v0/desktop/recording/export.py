"""Export closed recovery files without replacing existing data."""
from pathlib import Path
import json,shutil

def export_recording(source,destination):
    source=Path(source);dest=Path(destination).with_suffix('.csv');meta=dest.with_suffix('.json')
    if dest.resolve()==source.resolve():return str(source)
    if dest.exists() or meta.exists():raise FileExistsError('Choose a new filename; recordings are never overwritten.')
    dest.parent.mkdir(parents=True,exist_ok=True)
    made=[]
    try:
        with source.open('rb') as src,dest.open('xb') as dst:made.append(dest);shutil.copyfileobj(src,dst)
        data=json.loads(source.with_suffix('.json').read_text());data['exported_from']=str(source)
        with meta.open('x') as f:made.append(meta);json.dump(data,f,indent=2)
    except BaseException:
        for p in made:p.unlink(missing_ok=True)
        raise
    return str(dest)
