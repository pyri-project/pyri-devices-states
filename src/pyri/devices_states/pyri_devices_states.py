from contextlib import suppress
import RobotRaconteur as RR
from RobotRaconteur.RobotRaconteurPythonUtil import SplitQualifiedName
import threading
from pyri.device_manager_client import DeviceManagerClient
from pyri.plugins.device_type_adapter import get_device_type_adapter_plugin_factories
from RobotRaconteurCompanion.Util.DateTimeUtil import DateTimeUtil

import traceback
import numpy as np
import asyncio
import time


class PyriDevicesStatesService:

    def __init__(self, device_manager, device_info = None, node : RR.RobotRaconteurNode = None):
        self._lock = threading.RLock()
        if node is None:
            self._node = RR.RobotRaconteurNode.s
        else:
            self._node = node
        self.device_info = device_info

        self._devices_states = self._node.GetStructureType('tech.pyri.devices_states.PyriDevicesStates')
        self._device_not_found = self._node.GetExceptionType('tech.pyri.device_manager.DeviceNotFound')

        self._device_manager = device_manager
        
        self._refresh_counter = 0

        self._devices = dict()
        self._seqno = 0

        self._date_time_util = DateTimeUtil(self._node)
        self._date_time_utc_type = self._node.GetPodDType('com.robotraconteur.datetime.DateTimeUTC')
        self._isoch_info = self._node.GetStructureType('com.robotraconteur.device.isoch.IsochInfo')

        self._aio_thread = None
        self._loop = None

        self._start_aio_thread()
        time.sleep(0.1)

        self._start_refresh_devices()

        self._refresh_devices_fut = None
        self._send_devices_states_fut = None

    def RRServiceObjectInit(self, ctx, service_path):
        self._downsampler = RR.BroadcastDownsampler(ctx)
        self._downsampler.AddWireBroadcaster(self.devices_states)

        self._start_send_devices_states()

    def _start_aio_thread(self):
        self._aio_thread = threading.Thread(target=self._run_aio_thread)
        self._aio_thread.daemon=True
        self._aio_thread.start()

    def _run_aio_thread(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _stop_aio_thread(self):
        self._loop.close()

    def _start_refresh_devices(self):
        self.refresh_devices_fut = asyncio.run_coroutine_threadsafe(self._refresh_devices(), self._loop)

    def _start_send_devices_states(self):
        self._send_devices_states_fut = asyncio.run_coroutine_threadsafe(self._send_devices_states(), self._loop)

    async def _do_refresh_devices(self, timeout):
        await self._device_manager.async_refresh_devices(timeout)

        active_devices = self._device_manager.get_device_names()

        with self._lock:
            for d in active_devices:
                if d not in self._devices:                
                    sub = self._device_manager.get_device_subscription(d)
                    device_ident = self._device_manager.get_device_info(d).device
                    self._devices[d] = PyriDevicesStatesActiveDevice(d, device_ident, sub, self._node)

            for d in list(self._devices.keys()):
                if d not in active_devices:
                    del self._devices[d]

            for dev in self._devices.values():
                dev.refresh_types()

    async def _refresh_devices(self):
        
        try:
            try:
                await self._do_refresh_devices(5)
            except:
                traceback.print_exc()
            await asyncio.sleep(1)
            while True:
                try:
                    await self._do_refresh_devices(0)
                except:
                    traceback.print_exc()
                await asyncio.sleep(1)
        except:
            traceback.print_exc()
            raise

    def getf_device_info(self, local_device_name):

        return self._device_manager.get_device_info(local_device_name)

    def getf_standard_device_info(self, local_device_name):

        device_client = self._device_manager.get_device_client(local_device_name, 0.2)
        return device_client.device_info

    def getf_extended_device_info(self, local_device_name):
        with self._lock:
            dev = self._devices.get(local_device_name, None)

        if dev is None:
            raise self._device_not_found(f"Unknown local_device_name: {local_device_name}")

        return asyncio.run_coroutine_threadsafe(dev.get_extended_device_info(1),self._loop).result()

    async def _send_devices_states(self):
        
        while True:
            
            try:
                with self._lock:
                    self._seqno += 1
                    devices = list(self._devices.values())

                devices_states = dict()
                for d in devices:
                    devices_states[d.local_device_name] = await d.get_device_state()

                s = self._devices_states()

                s.ts = self._date_time_util.TimeSpec3Now()
                s.seqno = self._seqno
                s.devices_states = devices_states
                self.devices_states.OutValue = s
            except:
                traceback.print_exc()

            await asyncio.sleep(0.1)

            #print(self._seqno)

    def close(self):

        with suppress(Exception):
            self._send_devices_states_fut.cancel()
        with suppress(Exception):
            self._refresh_devices_fut.cancel()
        time.sleep(0.1)
        self._loop.stop()

    @property
    def isoch_downsample(self):
        return self._downsampler.GetClientDownsample(RR.ServerEndpoint.GetCurrentEndpoint())

    @isoch_downsample.setter
    def isoch_downsample(self, value):
        return self._downsampler.SetClientDownsample(RR.ServerEndpoint.GetCurrentEndpoint(),value)

    @property
    def isoch_info(self):
        ret = self._isoch_info()
        ret.update_rate = self._fps
        ret.max_downsample = 100
        ret.isoch_epoch = np.zeros((1,),dtype=self._date_time_utc_type)
        
class PyriDevicesStatesActiveDevice:
    def __init__(self, local_device_name, device_ident, sub, node = None):
        self._lock = threading.Lock()
        self._local_device_name = local_device_name
        self._device_ident = device_ident
        self._sub = sub

        if node is None:
            self._node = RR.RobotRaconteurNode.s
        else:
            self._node = node

        self._device_state = self._node.GetStructureType('tech.pyri.devices_states.PyriDeviceState')
        self._device_state_typed = self._node.GetStructureType('tech.pyri.devices_states.PyriDeviceStateTyped')

        self._adapters = dict()
        self._checked_adapter_types = set()

        self.refresh_types()

    def refresh_types(self):
        res, default_client = self._sub.TryGetDefaultClient()
        if not res:
            return
        # TODO: Use a less invasive method to get this info?
        obj_type = default_client.rrinnerstub.RR_objecttype

        service_type_name = obj_type.GetServiceDefinition().Name
        
        rr_types = set([service_type_name + "." + obj_type.Name ])
        for imp in obj_type.Implements:
            if not '.' in imp:
                rr_types.add(service_type_name + "." + imp)
            else:
                rr_types.add(imp)

        update_factories = False

        for r in rr_types:
            if r not in self._adapters and r not in self._checked_adapter_types:
                update_factories = True
                break

        if not update_factories:
            return

        factories = get_device_type_adapter_plugin_factories()

        for f in factories:
            f_types = set(f.get_robotraconteur_types())
            for t in f_types.intersection(rr_types):
                rr_types.remove(t)
                try:
                    self._adapters[t] = f.create_device_type_adapter(t,self._sub,self._node)
                except:
                    traceback.print_exc()
                    self._checked_adapter_types.add(t)


    
        self._checked_adapter_types.update(rr_types)        

    @property
    def local_device_name(self):
        return self._local_device_name

    async def get_extended_device_info(self,timeout = 1):
        with self._lock:
            a = list(self._adapters.values())
        
        infos = dict()        
        for f in a:
            f_infos = await f.get_extended_device_infos(timeout)
            infos.update(f_infos)

        return infos

    async def get_device_state(self):
        device_state = self._device_state()

        device_state.local_device_name = self._local_device_name
        device_state.device = self._device_ident

        res, _ = self._sub.TryGetDefaultClient()
        if not res:
            device_state.connected = False
            return device_state
        device_state.connected = True
        ready =True
        error = False

        typed_states = []
        for a in self._adapters.values():
            s = await a.get_extended_device_states(0)
            for s1 in s.values():
                if not s1.ready:
                    ready = False
                if s1.error:
                    error = True
                
                s_typed = self._device_state_typed()
                s_typed.type = s1.robotraconteur_type
                s_typed.state_data = s1.state_data
                s_typed.display_flags = s1.display_flags
                typed_states.append(s_typed)

        device_state.ready = ready
        device_state.error = error
        device_state.state = typed_states

        return device_state


    