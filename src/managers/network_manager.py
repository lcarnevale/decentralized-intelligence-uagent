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
			
			self.__wlan_sta = network.WLAN(network.STA_IF)
			self.__wlan_ap = network.WLAN(network.AP_IF)
			self.__node_manager = NodeManager()

			self.__neighbours = {}
			self.__is_rendezvous = False

			self.__timer_fetch_nodes = Timer(0)
			self.__node_sync_timer = Timer(1)
			self.__listener_timer = Timer(2)
			self.__sender_timer = Timer(3)


		return self.__instance
	
	def build_mesh_credentials(self, mesh_credentials):
		self.__mesh_ssid = mesh_credentials['ssid']
		self.__mesh_passwd = mesh_credentials['passwd']
		return self.__instance

	def build_rendezvous(self, rendezvous_conf):
		self.__rendezvous_port = rendezvous_conf['port']
		return self.__instance

	def build_peer(self, peer_conf):
		self.__peer_source_port = peer_conf['source_port']
		self.__peer_destination_port = peer_conf['destination_port']
		return self.__instance
	
		
	def get_mac_address(self):
		"""Get MAC address.
		
		Returns:
			(str) node's mac addresses
		"""
		mac_address_bytes = self.__wlan_sta.config('mac')
		mac_address_str = ubinascii.hexlify(mac_address_bytes,':').decode()
		return mac_address_str


	def setup(self):
		# self.__coordination_manager = CoordinationManager()

		self.__wlan_sta.active(True)
		if self.__network_exists():
			self.__set_station()
			# self.__coordination_manager \
				# .build_client_socket(host=self.sta_gateway, port=self.__mesh_port)
			print(self.__wlan_sta.ifconfig())
		else: # network not exists
			self.__wlan_ap.active(True)
			self.__set_access_point()
			self.__set_rendezvous()
			# self.__coordination_manager \
				# .build_server_socket(port=self.__mesh_port)
			# self.__timer_fetch_nodes.init(
			# 	period=1000 * 60,
			# 	mode=Timer.PERIODIC,
			# 	callback=lambda _: _thread.start_new_thread(self.__fetch_nodes, ())
			# )
			print(self.__wlan_ap.ifconfig())

		self.__set_peer()
		# self.__coordination_manager.setup()

	def __network_exists(self) -> bool:
		print("scan for %s network ..." % (self.__mesh_ssid))
		for (ssid, _, __, ___, ___, ____) in self.__wlan_sta.scan():
			ssid = ssid.decode()
			if ssid == self.__mesh_ssid:
				print("%s network already exists" % (self.__mesh_ssid))
				return True
		print("%s network does not exist" % (self.__mesh_ssid))
		return False

	def __set_station(self) -> bool:
		"""
		"""
		self.__wlan_sta.active(True)
		if not self.__wlan_sta.isconnected():
			print('connecting to network %s ...' % (self.__mesh_ssid))
			self.__wlan_sta.connect(self.__mesh_ssid, self.__mesh_passwd)
			while not self.__wlan_sta.isconnected():
				pass
			print('station %s network connection is successful' % (self.__mesh_ssid))
		self.__sta_ip, _, self.sta_gateway, _ = self.__wlan_sta.ifconfig()
		return self.__wlan_sta.isconnected()

	def __set_peer(self):
		self.__sock_peer_recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.__sock_peer_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		print('binding peer ...')
		self.__sock_peer_recv.bind(('0.0.0.0', self.__peer_source_port))
		self.__sock_peer_send.bind(('0.0.0.0', self.__peer_destination_port))

	def __set_access_point(self):
		self.__wlan_ap.config(
			essid=self.__mesh_ssid, 
			password=self.__mesh_passwd,
			authmode=3,
			hidden=False
		)
		print('set up access point %s ...' % (self.__mesh_ssid))
		while self.__wlan_ap.active() == False:
			pass
		self.__ap_ip, _, self.ap_gateway, _ = self.__wlan_ap.ifconfig()
		print('access point %s connection is successful' % (self.__mesh_ssid))

	def __set_rendezvous(self):
		"""Set up a rendez vous server.
		
		It is based on UDP.
		"""
		self.__sock_rdv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		print('binding rendezvous server ...')
		self.__sock_rdv.bind(('0.0.0.0', self.__rendezvous_port))
		self.__is_rendezvous = True

	def __fetch_nodes(self) -> None:
		print('fetching stations ...')
		for station in self.__wlan_ap.status('stations'):
			mac_address_str = ubinascii.hexlify(station[0],':').decode()
			id = ''.join( mac_address_str.split(':')[2:] )
			id = int(id, 16)
			print("%s %s" % (id, mac_address_str))
		_thread.exit()


	def start(self):
		# self.__coordination_manager.start()
		if self.__is_rendezvous:
			_thread.start_new_thread(self.__rendezvous_job, ())
		_thread.start_new_thread(self.__listener_job, ())
		# time.sleep(2)
		# _thread.start_new_thread(self.__peer_sync_job, ())
		self.__node_sync_timer.init(
			period=1000 * 10,
			mode=Timer.PERIODIC,
			callback=lambda _: _thread.start_new_thread(self.__peer_sync_job, ())
		)
		# time.sleep(2)
		self.__sender_timer.init(
			period=1000 * 30,
			mode=Timer.PERIODIC,
			callback=lambda _: _thread.start_new_thread(self.__sender_job, ())
		)
		# _thread.start_new_thread(self.__sender_job, ())

	def __rendezvous_job(self):
		while True:
			data, address = self.__sock_rdv.recvfrom(2048)
			data = data.decode()
			print('> rdv recv %s' % (data))

			data_json = json.loads(data)
			client_node_id = data_json['node_id']
			
			if client_node_id not in self.__neighbours:
				print('new connection from %s - %s:%s' % (data_json['node_id'], address[0], address[1]))
			self.__neighbours[data_json['node_id']] = {
				"host": address[0], 
				"source_port": self.__peer_source_port,
				"destination_port": address[1]
			}

			neighbours_str = json.dumps(self.__neighbours)
			msg = '{"node_id": %s, "type": "node_sync_reply", "neighbours": %s}' % (self.__node_manager.id, neighbours_str)
			self.__sock_rdv.sendto(msg.encode('utf-8'), (address[0], self.__peer_source_port))
		_thread.exit()

	def __peer_sync_job(self):
		print("sending peer sync ...")
		if self.__is_rendezvous:
			msg = b'{"node_id": %s, "type": "node_sync_request", "gateway": true}' % (self.__node_manager.id)
			self.__sock_peer_send.sendto(msg, (self.ap_gateway, self.__rendezvous_port))
		else:
			msg = b'{"node_id": %s, "type": "node_sync_request"}' % (self.__node_manager.id)
			self.__sock_peer_send.sendto(msg, (self.sta_gateway, self.__rendezvous_port))
		_thread.exit()

	def __listener_job(self):
		print("listener starting ...")
		while True:
			data = self.__sock_peer_recv.recv(2048)
			if not data:
				continue
			data = data.decode()
			print('> peer recv %s' % (data))
			data_json = json.loads(data)
			if data_json["type"] == "node_sync_reply":
				self.__neighbours = data_json["neighbours"]
		_thread.exit()

	def __sender_job(self):
		neighbour = random.choice(list(self.__neighbours.keys()))
		print("sending TBD message to %s" % (neighbour))
		msg = '{"node_id": %s,"type": "tbd"}' % (self.__node_manager.id)
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
