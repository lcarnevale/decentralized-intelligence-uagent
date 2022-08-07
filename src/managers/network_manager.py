import json
import time
import random
import socket
import _thread
import network
import ubinascii
from machine import Timer
from protocols.sntp.sntp_client import SNTP
from managers.node_manager import NodeManager
from managers.coordination_manager import CoordinationManager

class NetworkManager(object):
	__instance = None
	
	def __new__(self):
		"""Implement Singleton class.
		
		Returns
			(NetworkManager) singleton instance of the class
		"""
		if self.__instance is None:
			print('creating the %s object ...' % (self.__name__))
			self.__instance = super(NetworkManager, self).__new__(self)
			
			self.__nic_sta = network.WLAN(network.STA_IF)
			self.__nic_ap = network.WLAN(network.AP_IF)
			self.__node_manager = NodeManager()

			self.__neighbours = {}
			self.__neighbours_sta = {}
			self.__neighbours_ap = {}

			self.__is_rendezvous = False

			self.__timer_fetch_nodes = Timer(0)
			self.__node_sync_timer = Timer(1)
			self.__sender_timer = Timer(2)

		return self.__instance
	
	def build_mesh_credentials(self, conf):
		self.__mesh_ssid = conf['ssid']
		self.__mesh_passwd = conf['passwd']
		return self.__instance

	def build_access_point(self, conf):
		self.__default_access_point_ip = conf['host_ip']
		self.__default_access_point_netmask = conf['netmask']
		self.__default_access_point_gateway = conf['host_gateway']
		self.__default_access_point_dns = conf['host_dns']
		return self.__instance

	def build_rendezvous(self, conf):
		self.__rendezvous_port = conf['port']
		return self.__instance

	def build_peer(self, conf):
		self.__peer_source_port = conf['source_port']
		self.__peer_destination_port = conf['destination_port']
		return self.__instance
	
		
	def get_mac_address(self):
		"""Get MAC address.
		
		Returns:
			(str) node's mac addresses
		"""
		mac_address_bytes = self.__nic_sta.config('mac')
		mac_address_str = ubinascii.hexlify(mac_address_bytes,':').decode()
		return mac_address_str


	def setup(self):
		self.__station_gateway = None
		if self.__network_exists():
			self.__station_gateway = self.__set_station()
		self.__access_point_gateway = self.__set_access_point()
		self.__set_rendezvous()
		self.__timer_fetch_nodes.init(
			period=1000 * 50,
			mode=Timer.PERIODIC,
			callback=lambda _: _thread.start_new_thread(self.__fetch_nodes, ())
		)

		print(self.__nic_sta.ifconfig())
		print(self.__nic_ap.ifconfig())

		self.__set_peer()

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
		_, _, gateway, _ = self.__nic_sta.ifconfig()
		return gateway

	def __set_access_point(self):
		"""Create an access point with default ssid and password.

		The method updates the default access point configuration if there is
		a conflict between the default access point gateway and the station
		gateway.

		Returns:
			(str) IP address of access point gateway.
		"""
		self.__nic_ap.active(True)
		self.__nic_ap.config(
			essid = self.__mesh_ssid, 
			password = self.__mesh_passwd,
			authmode = 3,
			hidden = False # TODO: make it hidden
		)
		access_point_configuration = (
			self.__default_access_point_ip, 
			self.__default_access_point_netmask,
			self.__default_access_point_gateway,
			self.__default_access_point_dns
		)
		if self.__gateway_conflict_exists():
			access_point_configuration = self.__update_access_point_configuration()
		self.__nic_ap.ifconfig(access_point_configuration)

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

	def __set_peer(self):
		self.__sock_peer_recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.__sock_peer_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		print('binding peer ...')
		self.__sock_peer_recv.bind(('0.0.0.0', self.__peer_source_port))
		self.__sock_peer_send.bind(('0.0.0.0', self.__peer_destination_port))

	def __set_rendezvous(self):
		"""Set up a rendez vous server.
		
		It is based on UDP.
		"""
		self.__sock_rdv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		print('binding rendezvous server ...')
		self.__sock_rdv.bind(('0.0.0.0', self.__rendezvous_port))

	def __fetch_nodes(self) -> None:
		print('> info fetching stations ...')
		for station in self.__nic_ap.status('stations'):
			mac_address_str = ubinascii.hexlify(station[0],':').decode()
			id = ''.join( mac_address_str.split(':')[2:] )
			id = int(id, 16)
			print("> info %s %s" % (id, mac_address_str))
		print('> info neighbours %s' % (self.__neighbours))
		_thread.exit()


	def start(self):
		# self.__coordination_manager.start()
		_thread.start_new_thread(self.__rendezvous_job, ())
		_thread.start_new_thread(self.__peer_job, ())
		self.__node_sync_timer.init(
			period=1000 * 30,
			mode=Timer.PERIODIC,
			callback=lambda _: _thread.start_new_thread(self.__peer_sync_job, ())
		)
		self.__sender_timer.init(
			period=1000 * 75,
			mode=Timer.PERIODIC,
			callback=lambda _: _thread.start_new_thread(self.__sender_job, ())
		) # for testing purposing only

	def __rendezvous_job(self):
		while True:
			data, address = self.__sock_rdv.recvfrom(2048)
			data = data.decode()
			print('> rdv recv %s' % (data))

			data_json = json.loads(data)
			client_node_id = data_json['node_id']
			
			if client_node_id not in self.__neighbours:
				print('new connection from %s - %s:%s' % (client_node_id, address[0], address[1]))
			self.__neighbours_ap[client_node_id] = {
				"host": address[0], 
				"source_port": self.__peer_source_port,
				"destination_port": address[1]
			}
			self.__update_neighbours()

			neighbours_str = json.dumps(self.__neighbours_ap)
			msg = '{"node_id": "%s", "type": "node_sync_reply", "neighbours": %s}' % (self.__node_manager.id, neighbours_str)
			self.__sock_rdv.sendto(msg.encode('utf-8'), (address[0], self.__peer_source_port))

	def __peer_job(self):
		print("listener starting ...")
		while True:
			data = self.__sock_peer_recv.recv(2048)
			if not data:
				continue
			data = data.decode()
			print('> peer recv %s' % (data))
			data_json = json.loads(data)
			if data_json["type"] == "node_sync_reply":
				self.__neighbours_sta = data_json["neighbours"]
				self.__update_neighbours()

	def __update_neighbours(self) -> None:
		self.__neighbours.update(self.__neighbours_sta)
		self.__neighbours.update(self.__neighbours_ap)

	def __peer_sync_job(self):
		print("sending peer sync ...")
		if self.__station_gateway:
			msg = b'{"node_id": "%s", "type": "node_sync_request"}' % (self.__node_manager.id)
			self.__sock_peer_send.sendto(msg, (self.__station_gateway, self.__rendezvous_port))
		else:
			msg = b'{"node_id": "%s", "type": "node_sync_request", "gateway": true}' % (self.__node_manager.id)
			self.__sock_peer_send.sendto(msg, (self.__access_point_gateway, self.__rendezvous_port))
		print("sending peer sync ... completed!")
		_thread.exit()


	def __sender_job(self):
		if self.__neighbours.keys():
			neighbour = random.choice(list(self.__neighbours.keys()))
			print("sending TBD message to %s" % (neighbour))
			msg = '{"node_id": "%s","type": "tbd"}' % (self.__node_manager.id)
			self.send_unicast(msg, neighbour) # manda su source_port
		_thread.exit()


	def send_unicast(self, msg, destination_node):
		"""
		Args:
			msg(str)
			destination_node(int): node id
		"""
		host, port = self.__get_address(destination_node)
		self.__sock_peer_send.sendto(msg.encode(), (host, port))

	def __get_address(self, destination_node):
		host = self.__neighbours[destination_node]['host']
		port = self.__neighbours[destination_node]['source_port']
		return host, port
