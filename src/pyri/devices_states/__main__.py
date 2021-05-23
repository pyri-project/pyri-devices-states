import sys
import RobotRaconteur as RR
RRN = RR.RobotRaconteurNode.s
import RobotRaconteurCompanion as RRC
from .pyri_devices_states import PyriDevicesStatesService
import argparse
from RobotRaconteurCompanion.Util.InfoFileLoader import InfoFileLoader
from RobotRaconteurCompanion.Util.AttributesUtil import AttributesUtil
from pyri.plugins import robdef as robdef_plugins
from pyri.util.service_setup import PyriServiceNodeSetup

import asyncio


def main():
   
    with PyriServiceNodeSetup("tech.pyri.devices_states",59905, \
        display_description = "PyRI Devices States Service", register_plugin_robdef=True, \
        default_info=(__package__,"pyri_devices_states_default_info.yml")) as service_node_setup:

        extra_imports = RRN.GetRegisteredServiceTypes()

        dev_states = PyriDevicesStatesService(service_node_setup.device_manager, device_info=service_node_setup.device_info_struct, node = RRN) 

        service_ctx = service_node_setup.register_service("devices_states","tech.pyri.devices_states.PyriDevicesStatesService",dev_states)
        for e in extra_imports:
            service_ctx.AddExtraImport(e)

        loop = asyncio.new_event_loop()
        #asyncio.ensure_future(foo(loop))
        loop.run_forever()

        service_node_setup.wait_exit()

        dev_states.close()

if __name__ == "__main__":
    sys.exit(main() or 0)