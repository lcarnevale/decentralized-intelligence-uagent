import time
import socket
import _thread # TODO: move to custom scheduler class
from machine import Timer # TODO: move to custom scheduler class

class Peer(object):
    """Abstraction of peer features.

    This class implements the trasport layer dedicated to peers.

    Args:
        __instance(Peer): singleton instance of the class.
        ...
    """
    __instance = None

    def __new__(self) -> None:
        """Implement Singleton class.
		
		Returns
			(Peer) singleton instance of the class.
		"""
        if self.__instance is None:
            print('creating the %s object ...' % (self.__name__))
            self.__instance = super(Peer, self).__new__(self)
            self.__buffer_size = 2048
        return self.__instance
    
    def build_reader_socket(self, recv_port) -> __instance:
        """Build the reader feature of peer.
		
		It is based on UDP.

        Returns:
            (Peer) singleton instance of the class.
		"""
        self.__sock_recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print('binding reader peer ...')
        self.__sock_recv.bind(('0.0.0.0', recv_port))
        return self.__instance

    def build_writer_socket(self, send_port) -> __instance:
        """Build the writer feature of peer.
		
		It is based on UDP.

        Returns:
            (Peer) singleton instance of the class.
		"""
        self.__sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print('binding writer peer ...')
        self.__sock_send.bind(('0.0.0.0', send_port))
        return self.__instance

    def build_callback(self, callback) -> __instance:
        self.__callback = callback
        return self.__instance


    def destroy(self) -> None:
        self.__sock_send.close()
        self.__sock_recv.close()


    def run_forever(self):
        _thread.start_new_thread(self.__run_forever_job, ())       

    def __run_forever_job(self):
        while True:
            data = self.__sock_recv.recv(self.__buffer_size)
            if not data:
                continue
            data = data.decode()
            print('> peer recv %s' % (data))
            
            self.__callback(data) # TODO: move to a thread
  

    def sync_request(self, message, sta_address, ap_address, period = 1000 * 30):
        Timer(1).init(
			period=period,
			mode=Timer.PERIODIC,
			callback=lambda _: _thread.start_new_thread(
                self.__sync_request_job, (message, sta_address, ap_address)
            )
		)

    def __sync_request_job(self, message, sta_address, ap_address):
        # TODO: I do not like at all the parameters
        print("sending peer sync ...")
        if sta_address[0]:
            self.__sock_send.sendto(message, sta_address)
        self.__sock_send.sendto(message, ap_address)
        # TODO: do test on double sendto
        print("sending peer sync ... completed")
        _thread.exit()

    
    def unicast(self, message, address) -> None:
        """Send message to single node.

        Args:
            msg(str): message to be delivered
            address(tuple): the host, port tuple
        """
        message = message.encode('utf-8')
        self.__sock_send.sendto(message, address)
    
    def multicast(self, message, addresses) -> None:
        """Send message to multiple nodes.

        Args:
            msg(str): message to be delivered
            address(tuple): the host, port tuple
        """
        message = message.encode('utf-8')
        for address in addresses:
            self.__sock_send.sendto(message, address)
            time.sleep(100) # TODO: move to async

    def broadcast(self, message) -> None:
        """Send message to all nodes.

        Args:
            msg(str): message to be delivered
            address(tuple): the host, port tuple
        """
        # TODO: implement it
        # TODO: it should have knowledge about all nodes
        print("warnings: broadcast delivery not implemented yet")