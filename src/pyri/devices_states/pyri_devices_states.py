import RobotRaconteur as RR
from RobotRaconteur.RobotRaconteurPythonUtil import SplitQualifiedName
import threading
from pyri.device_manager_client import DeviceManagerClient
from pyri.plugins.device_type_adapter import get_device_type_adapter_plugin_factories
from asgiref.sync import async_to_sync

import traceback


class PyriDevicesStatesService:

    def __init__(self, device_manager_url, device_info = None, node : RR.RobotRaconteurNode = None):
        self._lock = threading.RLock()
        if node is None:
            self._node = RR.RobotRaconteurNode.s
        else:
            self._node = node
        self.device_info = device_info

        self._device_state = self._node.GetStructureType('tech.pyri.devices_states.PyriDeviceState')
        self._device_state_typed = self._node.GetStructureType('tech.pyri.devices_states.PyriDeviceStateTyped')
        self._devices_states = self._node.GetStructureType('tech.pyri.devices_states.PyriDevicesStates')
        self._device_not_found = self._node.GetExceptionType('tech.pyri.device_manager.DeviceNotFound')

        self._device_manager = DeviceManagerClient(device_manager_url)
        self._device_manager.refresh_devices(1)

        self._timer = self._node.CreateTimer(0.1, self._timer_cb)
        self._timer.Start()

        self._refresh_counter = 0

        self._devices = dict()

        self._refresh_devices(1)

    def _refresh_devices(self, timeout):
        self._device_manager.refresh_devices(timeout)

        for d in self._device_manager.get_device_names():
            if d not in self._devices:                
                sub = self._device_manager.get_device_subscription(d)
                self._devices[d] = PyriDevicesStatesActiveDevice(d, sub, self._node)

        for dev in self._devices.values():
            dev.refresh_types()

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

        return dev.get_extended_device_info(1)

    def _timer_cb(self,evt):
        with self._lock:
            #print("Timer callback!")

            if self._refresh_counter >= 50:
                self._refresh_devices(0)
            else:
                self._refresh_counter += 1
            for d in self._device_manager.get_device_names():
                
                dev = self._device_manager.get_device_subscription(d)

                dev_connected, _ = dev.TryGetDefaultClient()

                print(f"Device: {d} is connected? {dev_connected}")


    def close(self):
        try:
            self._timer.Stop()
        except:
            pass
        
class PyriDevicesStatesActiveDevice:
    def __init__(self, local_device_name, sub, node = None):
        self._lock = threading.Lock()
        self._local_device_name = local_device_name
        self._sub = sub

        if node is None:
            self._node = RR.RobotRaconteurNode.s
        else:
            self._node = node

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
                    self._adapters[t] = f.create_device_type_adapter(t,self._sub)
                except:
                    traceback.print_exc()

    
        self._checked_adapter_types.update(rr_types)        

    @property
    def local_device_name(self):
        return self._local_device_name

    @async_to_sync
    async def get_extended_device_info(self,timeout = 1):
        with self._lock:
            a = list(self._adapters.values())
        
        infos = dict()        
        for f in a:
            f_infos = await f.get_extended_device_infos(timeout)
            infos.update(f_infos)

        return infos



    