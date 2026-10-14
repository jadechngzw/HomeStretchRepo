#!/usr/bin/env python3
"""Download a pinned Nordic SDK; extract only build inputs and licenses."""
import hashlib,tempfile,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
URL='https://developer.nordicsemi.com/nRF5_SDK/nRF5_SDK_v17.x.x/nRF5_SDK_17.1.0_ddde560.zip'
SHA256='5bfe38e744c39fd7f30e10077ba12df306ef91f368894795d6a3e7a62dc68061'
with tempfile.TemporaryDirectory() as td:
    archive=Path(td)/'sdk.zip';print('Downloading Nordic SDK 17.1.0…');urllib.request.urlretrieve(URL,archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=SHA256:raise SystemExit('SDK checksum mismatch; refusing extraction')
    dest=ROOT/'firmware/vendor';dest.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for n in z.namelist():
            if '..' in Path(n).parts or Path(n).is_absolute():raise ValueError('Unsafe archive path')
            if any(s in n for s in ('components/softdevice/s140/','modules/nrfx/mdk/','components/toolchain/cmsis/include/','documentation/licenses')) or n.endswith('license.txt'):z.extract(n,dest)
print('SDK installed. Review firmware/vendor/nRF5_SDK_17.1.0_ddde560/documentation/licenses.txt.')
