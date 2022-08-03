from managers.node_manager import NodeManager

class MessageProtocol(object):
    """
    """
    __instance = None
    
    def __new__(self):
        """Implement Singleton
    
        Args:
            mac_address(str): the station MAC address of the board
            
        Returns:
            (NodeManager) singleton instance of the class
        """
        if self.__instance is None:
            print('creating the %s object ...' % (self.__name__))
            self.__instance = super(NodeManager, self).__new__(self)
			
            self.__node_manager = NodeManager()
            
        return self.__instance