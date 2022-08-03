import sys
import json
import machine
from managers.node_manager import NodeManager
from managers.network_manager import NetworkManager
from managers.service_manager import ServiceManager

def main():
	"""Application entry point.
	"""
	try:
		with open('conf.json', 'r') as f:
			conf = json.load(f)
	
		builtin_led = machine.Pin(
			conf['hardware']['builtin_led'],
			machine.Pin.OUT
		)
		# permanente blue light is generic software error
		builtin_led.value(0)

		network_manager = NetworkManager() \
			.build_mesh_credentials(conf['network']['mesh_credentials']) \
			.build_rendezvous(conf['network']['rendezvous']) \
			.build_peer(conf['network']['peer'])

		NodeManager() \
			.build_node_id(network_manager.get_mac_address())

		services = ["service-1", "service-2"]
		service_manager = ServiceManager()
		
		network_manager.setup()
		network_manager.start()

		service_manager.setup(services)
		service_manager.start(services)

		# machine.Timer(-1).init(
		# 	period=1000 * 30,
		# 	mode=machine.Timer.PERIODIC,
		# 	callback=lambda _: task
		# )
	except Exception as e:
		builtin_led.value(1)
		sys.print_exception(e)

def task(_):
	network_manager = NetworkManager()
	msg = 'direct message'
	network_manager.send_unicast(msg, 706214256)

main()