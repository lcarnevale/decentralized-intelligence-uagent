import json
import random
import _thread
import network
import ubinascii
from machine import Timer
from managers.coordination.peer import Peer
from managers.coordination.rendezvous import Rendezvous
from managers.node_manager import NodeManager

class NetworkManager(object):
	__instance = None
	
	def __new__(self) -> __instance:
		"""Implement Singleton class.
		
		Returns
			(NetworkManager) singleton instance of the class
		"""
		if self.__instance is None:
			print('creating the %s object ...' % (self.__name__))
			self.__instance = super(NetworkManager, self).__new__(self)
			self.__nic_sta = network.WLAN(network.STA_IF)
			self.__nic_ap = network.WLAN(network.AP_IF)
			self.__timer_fetch_nodes = Timer(0)
			self.__sender_timer = Timer(2)
			self.__node_manager = NodeManager()
			self.__neighbours = {}
			self.__neighbours_sta = {}
			self.__neighbours_ap = {}
		return self.__instance
	
	def build_mesh_credentials(self, conf) -> __instance:
		self.__mesh_ssid = conf['ssid']
		self.__mesh_passwd = conf['passwd']
		return self.__instance

	def build_access_point(self, conf) -> __instance:
		self.__default_access_point_ip = conf['host_ip']
		self.__default_access_point_netmask = conf['netmask']
		self.__default_access_point_gateway = conf['host_gateway']
		self.__default_access_point_dns = conf['host_dns']
		return self.__instance

	def build_network(self, conf) -> __instance:
		self.__peer_reader_port = conf['peer_reader_port']
		self.__peer = Peer() \
			.build_reader_socket(conf['peer_reader_port']) \
			.build_writer_socket(conf['peer_writer_port']) \
			.build_callback(self.__peer_callback)
		self.__rendezvous_port = conf['rendezvous_port']
		self.__rendezvous = Rendezvous() \
			.build_socket(self.__rendezvous_port) \
			.build_callback(self.__rendezvous_callback)
		return self.__instance

	def __peer_callback(self, data) -> None:
		try:
			# TODO: move to message protocol
			data = json.loads(data)
			if data["type"] == "node_sync_reply":
				self.__neighbours_sta = data["neighbours"]
				self.__update_neighbours()
		except KeyError as e:
			print("Warning: the key does not exist. %s" % (e))

	def __rendezvous_callback(self, data, address) -> None:
		try:
			# TODO: move to message protocol
			data = json.loads(data)
			if data['type'] == 'peer_sync_request':
				client_node_id = data['node_id']
				if client_node_id not in self.__neighbours:
					print('new connection from %s - %s:%s' % (client_node_id, address[0], address[1]))
				self.__neighbours_ap[client_node_id] = {
					"host": address[0], 
					"source_port": self.__peer_reader_port,
					"destination_port": address[1]
				}
				self.__update_neighbours()
				neighbours_str = json.dumps(self.__neighbours_ap)
				msg = '{"node_id": "%s", "type": "node_sync_reply", "neighbours": %s}' % (self.__node_manager.id, neighbours_str)
				address = (address[0], self.__peer_reader_port)
				self.__rendezvous.sync_reply(msg, address)
		except KeyError as e:
			print("Warning: the key does not exist. %s" % (e))

	def __update_neighbours(self) -> None:
		self.__neighbours.update(self.__neighbours_sta)
		self.__neighbours.update(self.__neighbours_ap)


	def destroy(self):
		self.__peer.destroy()
		self.__rendezvous.destroy()

		
	def get_mac_address(self):
		"""Get MAC address.
		
		Returns:
			(str) node's mac addresses
		"""
		mac_address_bytes = self.__nic_sta.config('mac')
		mac_address_str = ubinascii.hexlify(mac_address_bytes,':').decode()
		return mac_address_str


	def setup(self) -> None:
		self.__station_ip, self.__station_gateway = None, None
		if self.__network_exists():
			self.__station_ip, self.__station_gateway = self.__set_station()
		self.__access_point_gateway = self.__set_access_point()

	def __network_exists(self) -> bool:
		"""Scan for default network.

		Returns:
			(bool) True if network exists, False otherwise.
		"""
		self.__nic_sta.active(True)
		print("scan for %s network ..." % (self.__mesh_ssid))
		for (ssid, _, _, _, _, _) in self.__nic_sta.scan():
			ssid = ssid.decode()
			if ssid == self.__mesh_ssid:
				print("%s network already exists" % (self.__mesh_ssid))
				return True
		print("%s network does not exist" % (self.__mesh_ssid))
		return False

	def __set_station(self) -> bool:
		"""Connect to default network.

		Returns:
			(str) IP address of station gateway.
		"""
		self.__nic_sta.active(True)
		if not self.__nic_sta.isconnected():
			print('connecting to %s network ...' % (self.__mesh_ssid))
			self.__nic_sta.connect(self.__mesh_ssid, self.__mesh_passwd)
			while not self.__nic_sta.isconnected():
				pass # TODO: define timeout
			print('connection to %s station network is successful' % (self.__mesh_ssid))
		ip, _, gateway, _ = self.__nic_sta.ifconfig()
		return ip, gateway
		

	def __set_access_point(self) -> str:
		"""Create an access point with default ssid and password.

		The method updates the default access point configuration if there is
		a conflict between the default access point gateway and the station
		gateway.

		Returns:
			(str) IP address of access point gateway.
		"""
		access_point_configuration = (
			self.__default_access_point_ip, 
			self.__default_access_point_netmask,
			self.__default_access_point_gateway,
			self.__default_access_point_dns
		)
		if self.__gateway_conflict_exists():
			access_point_configuration = self.__update_access_point_configuration()
		self.__nic_ap.ifconfig(access_point_configuration)
		self.__nic_ap.active(True)
		self.__nic_ap.config(
			essid = self.__mesh_ssid, 
			password = self.__mesh_passwd,
			authmode = 3,
			hidden = False # TODO: make it hidden
		)
		print('creating %s access point  ...' % (self.__mesh_ssid))
		while self.__nic_ap.active() == False:
			pass
		_, _, gateway, _ = self.__nic_ap.ifconfig()
		print('creation of %s access point is completed' % (self.__mesh_ssid))
		return gateway

	def __gateway_conflict_exists(self) -> bool:
		"""Check if station and access point gateway are the same.
		
		Returns:
			(bool) True if there is a conflict, False otherwise.
		"""
		if self.__station_gateway == self.__default_access_point_gateway:
			return True
		return False

	def __update_access_point_configuration(self) -> tuple:
		octets = self.__default_access_point_gateway.split('.')
		first, second, third, fourth = octets
		third_target = int(third)
		if third_target > 0: # 1 or more
			third_target -= 1
		else:
			third_target += 1
		octets_target = (first, second, str(third_target), fourth)
		print(octets_target)
		target_gateway = '.'.join(octets_target)

		ip = target_gateway
		netmask = self.__default_access_point_netmask
		gateway = target_gateway
		dns = target_gateway

		return (ip, netmask, gateway, dns)

	
	def start(self):
		self.__rendezvous.run_forever() # reader job
		self.__peer.run_forever() # reader job

		message = self.__get_peer_sync_request_message()
		sta_address = (self.__station_gateway, self.__rendezvous_port)
		ap_address = (self.__access_point_gateway, self.__rendezvous_port)
		self.__peer.sync_request(
			message, 
			sta_address, 
			ap_address, 
			period=1000 * 30
		) # periodic writer job

		# self.__timer_fetch_nodes.init(
		# 	period=1000 * 50,
		# 	mode=Timer.PERIODIC,
		# 	callback=lambda _: _thread.start_new_thread(self.__fetch_nodes, ())
		# ) # TODO: for testing purposing only
		
		# # self.__sender_timer.init(
		# # 	period=1000 * 75,
		# # 	mode=Timer.PERIODIC,
		# # 	callback=lambda _: _thread.start_new_thread(self.__sender_job, ())
		# # ) # for testing purposing only
	
	def __get_peer_sync_request_message(self) -> bytes:
		# TODO: move to message protocol
		# TODO: start from json, convert to bytes
		node_id = self.__node_manager.id
		return '{"node_id": "%s", "type": "peer_sync_request"}' % (node_id)

	def __fetch_nodes(self) -> None:
		print('> info fetching stations ...')
		for station in self.__nic_ap.status('stations'):
			mac_address_str = ubinascii.hexlify(station[0],':').decode()
			id = ''.join( mac_address_str.split(':')[2:] )
			id = int(id, 16)
			print("> info %s %s" % (id, mac_address_str))
		print('> info neighbours %s' % (self.__neighbours))
		_thread.exit()

	def __sender_job(self):
		if self.__neighbours.keys():
			neighbour = random.choice(list(self.__neighbours.keys()))
			print("sending TBD message to %s" % (neighbour))
			msg = '{"node_id": "%s","type": "tbd"}' % (self.__node_manager.id)
			self.send_unicast(msg, neighbour) # manda su source_port
		_thread.exit()


	def __get_address(self, destination_node):
		host = self.__neighbours[destination_node]['host']
		port = self.__neighbours[destination_node]['source_port']
		return host, port