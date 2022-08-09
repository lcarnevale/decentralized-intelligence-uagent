import sys
import json
from managers.node_manager import NodeManager
from managers.service_manager import ServiceManager
from managers.coordination.network_manager import NetworkManager

def main():
	try:
		with open('conf.json', 'r') as f:
			conf = json.load(f)
	
		network_manager = NetworkManager() \
			.build_mesh_credentials(conf['network']['mesh_credentials']) \
			.build_access_point(conf['network']['access_point']) \
			.build_network(conf['network']['p2p'])

		node_manager = NodeManager() \
			.build_node_id(network_manager.get_mac_address()) \
			.build_error_pin(conf['hardware']['builtin_led'])

		services = ["service-1", "service-2"]
		service_manager = ServiceManager()

		network_manager.setup()
		network_manager.start()

		service_manager.setup(services)
		service_manager.start(services)
	except Exception as e:
		# node_manager.turn_on_error_pin()
		sys.print_exception(e)

		# service_manager.destroy()
		# node_manager.destroy()
		network_manager.destroy()

main()