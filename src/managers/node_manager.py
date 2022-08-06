from machine import Pin
from managers.ota_manager import OTAManager

class NodeManager(object):
	"""
	Args:
		id(str): the node id
		ota(OTAManager): OTA manager used to download and update software in run-time
	"""
	__instance = None

	def __new__(self):
		"""Implement Singleton class.
				
		Returns
			(NodeManager) singleton instance of the class
		"""
		if self.__instance is None:
			print('creating the %s object ...' % (self.__name__))
			self.__instance = super(NodeManager, self).__new__(self)
			
			self.ota = OTAManager()

		return self.__instance


	def build_node_id(self, mac_address) -> None:
		""" Node ID builder.

		Args:
			mac_address(str): the station MAC address of the board

		Returns
			(NodeManager) singleton instance of the class
		"""
		self.id = self.__create_id(mac_address)
		print('node id: %s' % (self.id))
		return self.__instance

	def __create_id(self, mac_address) -> str:
		"""Generate the node id

		TODO: explain how this is created

		Args:
			mac_address(str): the station MAC address of the board

		Returns:
			(str)
		"""
		id = ''.join( mac_address.split(':')[2:] )
		id = int(id, 16)
		return str(id)

	def build_error_pin(self, pin):
		self.__builtin_led = Pin(pin, Pin.OUT)
		# permanent blue light is generic software error
		self.__builtin_led.value(0)
		return self.__instance


	def turn_on_error_pin(self) -> None:
		self.__builtin_led.value(1)
		return