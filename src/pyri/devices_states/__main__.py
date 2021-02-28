import sys
import RobotRaconteur as RR
RRN = RR.RobotRaconteurNode.s
import RobotRaconteurCompanion as RRC
from .pyri_devices_states import PyriDevicesStatesService
import argparse
from RobotRaconteurCompanion.Util.InfoFileLoader import InfoFileLoader
from RobotRaconteurCompanion.Util.AttributesUtil import AttributesUtil
from pyri.plugins import robdef as robdef_plugins


def main():

    parser = argparse.ArgumentParser(description="PyRI Devices States Service")    
    parser.add_argument("--device-info-file", type=argparse.FileType('r'),default=None,required=True,help="Device info file for devices states service (required)")
    parser.add_argument('--device-manager-url', type=str, default=None,required=True,help="Robot Raconteur URL for device manager service (required)")
    parser.add_argument("--wait-signal",action='store_const',const=True,default=False, help="wait for SIGTERM or SIGINT (Linux only)")
    
    args, _ = parser.parse_known_args()

    RRC.RegisterStdRobDefServiceTypes(RRN)
    robdef_plugins.register_all_plugin_robdefs(RRN)

    with args.device_info_file:
        device_info_text = args.device_info_file.read()

    info_loader = InfoFileLoader(RRN)
    device_info, device_ident_fd = info_loader.LoadInfoFileFromString(device_info_text, "com.robotraconteur.device.DeviceInfo", "device")

    attributes_util = AttributesUtil(RRN)
    device_attributes = attributes_util.GetDefaultServiceAttributesFromDeviceInfo(device_info)

    extra_imports = RRN.GetRegisteredServiceTypes()

    with RR.ServerNodeSetup("tech.pyri.devices_states",59905,argv=sys.argv):

        dev_states = PyriDevicesStatesService(args.device_manager_url, device_info=device_info, node = RRN) 

        service_ctx = RRN.RegisterService("devices_states","tech.pyri.devices_states.PyriDevicesStatesService",dev_states)
        service_ctx.SetServiceAttributes(device_attributes)

        for e in extra_imports:
            service_ctx.AddExtraImport(e)

        if args.wait_signal:  
            #Wait for shutdown signal if running in service mode          
            print("Press Ctrl-C to quit...")
            import signal
            signal.sigwait([signal.SIGTERM,signal.SIGINT])
        else:
            #Wait for the user to shutdown the service
            if (sys.version_info > (3, 0)):
                input("Server started, press enter to quit...")
            else:
                raw_input("Server started, press enter to quit...")

        dev_states.close()

if __name__ == "__main__":
    sys.exit(main() or 0)