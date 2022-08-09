import socket
import _thread

class Rendezvous(object):
    """Abstraction of rendezvous features.

    This class implements the trasport layer dedicated to rendezvous.

    Args:
        __instance(Rendezvous): singleton instance of the class.
        ...
    """
    __instance = None

    def __new__(self) -> __instance:
        """Implement Singleton class.
		
		Returns
			(Rendezvous) singleton instance of the class.
		"""
        if self.__instance is None:
            print('creating the %s object ...' % (self.__name__))
            self.__instance = super(Rendezvous, self).__new__(self)
            self.__buffer_size = 2048
        return self.__instance
    
    def build_socket(self, port) -> __instance:
        """Build a rendezvous server.
		
		It is based on UDP.

        Returns:
            (Rendezvous) singleton instance of the class.
		"""
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print('binding rendezvous ...')
        self.__sock.bind(('0.0.0.0', port))
        return self.__instance

    def build_callback(self, callback) -> __instance:
        self.__callback = callback
        return self.__instance


    def destroy(self) -> None:
        self.__sock.close()


    def run_forever(self) -> None:
        _thread.start_new_thread(self.__run_forever_job, ())
    
    def __run_forever_job(self) -> None:
        while True:
            data, address = self.__sock.recvfrom(self.__buffer_size)
            if not data:
                continue
            data = data.decode()
            print('> rdv recv %s' % (data))
            
            self.__callback(data, address) # TODO: move to a thread
        

    def sync_reply(self, message, address) -> None:
        message = message.encode('utf-8')
        self.__sock.sendto(message, address)