class ServiceManager():
	"""
	"""

	def __init__(self) -> None:
		pass

	def setup(self, services):
		for service in services:
			print("%s setup completed" % (service)) # service.setup()

	def start(self, services):
		for service in services:
			print("%s start" % (service)) # service.start()