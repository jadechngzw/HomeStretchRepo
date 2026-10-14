"""Bluetooth transport. One asyncio loop, one connection, serialized commands."""
import asyncio
from desktop.protocol import SERVICE,CONTROL,STATUS,SAMPLES,TELEMETRY,command,decode_status,decode_telemetry

class Watch:
    def __init__(self,on_sample,on_status,on_disconnect,on_telemetry=None):
        self.on_sample=on_sample;self.on_status=on_status;self.on_disconnect=on_disconnect
        self.on_telemetry=on_telemetry or (lambda _:None)
        self.client=None;self.request_id=0;self.pending=None;self.lock=asyncio.Lock()
    async def scan(self):
        from bleak import BleakScanner
        found=await BleakScanner.discover(timeout=6,return_adv=True,service_uuids=[SERVICE])
        return [(device,adv.local_name or device.name or 'VitalWave-v0',adv.rssi) for device,adv in found.values() if SERVICE in [u.lower() for u in adv.service_uuids]]
    def _disconnected(self,_):
        if self.pending and not self.pending[1].done():self.pending[1].set_exception(ConnectionError('Watch disconnected'))
        self.on_disconnect()
    def _status(self,_,data):
        try:s=decode_status(data)
        except ValueError:return
        if self.pending and s.request==self.pending[0] and not self.pending[1].done():self.pending[1].set_result(s)
        self.on_status(s)
    def _samples(self,_,data):
        data=bytes(data)
        if not data or len(data)%20:self.on_sample(data);return
        for offset in range(0,len(data),20):self.on_sample(data[offset:offset+20])
    def _telemetry(self,_,data):
        try:self.on_telemetry(decode_telemetry(data))
        except ValueError:pass
    async def connect(self,device):
        from bleak import BleakClient
        self.client=BleakClient(device,disconnected_callback=self._disconnected,timeout=15)
        try:
            await self.client.connect()
            for uuid in (CONTROL,STATUS,SAMPLES,TELEMETRY):
                if self.client.services.get_characteristic(uuid) is None:raise RuntimeError('Incompatible watch firmware: please flash the updated v3 firmware')
            await self.client.start_notify(STATUS,self._status)
            await self.client.start_notify(SAMPLES,self._samples)
            await self.client.start_notify(TELEMETRY,self._telemetry)
            self._telemetry(None,await self.client.read_gatt_char(TELEMETRY))
            s=decode_status(await asyncio.wait_for(self.client.read_gatt_char(STATUS),1));self.on_status(s);return s
        except BaseException:
            await self.disconnect();raise
    async def request(self,op,session,mask=0):
        async with self.lock:
            if not self.client or not self.client.is_connected:raise ConnectionError('Watch is not connected')
            self.request_id=self.request_id%65535+1
            f=asyncio.get_running_loop().create_future();self.pending=(self.request_id,f)
            try:
                await asyncio.wait_for(self.client.write_gatt_char(CONTROL,command(op,self.request_id,session,mask),response=True),1.5)
                try:return await asyncio.wait_for(asyncio.shield(f),1)
                except asyncio.TimeoutError:
                    s=decode_status(await asyncio.wait_for(self.client.read_gatt_char(STATUS),1))
                    if s.request!=self.request_id:raise TimeoutError('Watch did not acknowledge the command')
                    self.on_status(s);return s
            finally:
                if not f.done():f.cancel()
                self.pending=None
    async def disconnect(self):
        if self.client:
            client=self.client;self.client=None
            if client.is_connected:await client.disconnect()
