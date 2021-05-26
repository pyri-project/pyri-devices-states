from pyri.plugins.service_node_launch import ServiceNodeLaunch, PyriServiceNodeLaunchFactory


launches = [
    ServiceNodeLaunch("devices_states", "pyri.devices_states", "pyri.devices_states", default_devices=[("pyri_devices_states","devices_states")])
]

class DevicesStatesLaunchFactory(PyriServiceNodeLaunchFactory):
    def get_plugin_name(self):
        return "pyri.devices_states"

    def get_service_node_launch_names(self):
        return ["devices_states"]

    def get_service_node_launches(self):
        return launches

def get_service_node_launch_factory():
    return DevicesStatesLaunchFactory()

        
