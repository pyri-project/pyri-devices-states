from typing import List
from RobotRaconteurCompanion.Util import RobDef as robdef_util
from pyri.plugins.robdef import PyriRobDefPluginFactory

class DevicesStatesRobDefPluginFactory(PyriRobDefPluginFactory):
    def __init__(self):
        super().__init__()

    def get_plugin_name(self):
        return "pyri-devices-states"

    def get_robdef_names(self) -> List[str]:
        return ["tech.pyri.devices_states"]

    def  get_robdefs(self) -> List[str]:
        return get_devices_states_robdef()

def get_robdef_factory():
    return DevicesStatesRobDefPluginFactory()

def get_devices_states_robdef():
    return robdef_util.get_service_types_from_resources(__package__,["tech.pyri.devices_states"])