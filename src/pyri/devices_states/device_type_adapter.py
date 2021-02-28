from pyri.plugins.device_type_adapter import PyriDeviceTypeAdapterExtendedState, \
    PyriDeviceTypeAdapter, PyriDeviceTypeAdapterPluginFactory
from typing import List, Dict, Any, NamedTuple
import RobotRaconteur as RR

class RRDevice_TypeAdapter(PyriDeviceTypeAdapter):
    """Adapter for com.robotraconteur.device.Device"""

    def __init__(self, client_subscription, node):
        self._sub: "RobotRaconteur.ServiceSubscription" = client_subscription

    async def get_extended_device_infos(self, timeout) -> Dict[str,RR.VarValue]:

        res, c = self._sub.TryGetDefaultClientWait(timeout)
        if not res:
            return dict()
        
        info = await c.async_get_device_info(None,timeout)
        return {"com.robotraconteur.device.DeviceInfo": RR.VarValue(info,"com.robotraconteur.device.DeviceInfo")}

    async def get_extended_device_states(self, timeout) -> Dict[str,PyriDeviceTypeAdapterExtendedState]:
        return dict()

class PyriDeviceStatesTypeAdapterPluginFactory(PyriDeviceTypeAdapterPluginFactory):
    
    def get_plugin_name(self):
        return "pyri-devices-states"

    def get_robotraconteur_types(self) -> List[str]:
        return ["com.robotraconteur.device.Device"]

    def create_device_type_adapter(self, robotraconteur_type: str, client_subscription: Any, node) -> PyriDeviceTypeAdapter:

        if robotraconteur_type == "com.robotraconteur.device.Device":
            return RRDevice_TypeAdapter(client_subscription, node)
        assert False, "Invalid robotraconteur_type device type adapter requested"

def get_device_type_adapter_factory():
    return PyriDeviceStatesTypeAdapterPluginFactory()
        