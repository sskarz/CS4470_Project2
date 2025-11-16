
#libraries 
import sys
import socket
import threading
import time
import struct
import select
from collections import defaultdict
import argparse


from commands import CommandHandler




class DVServer:

    def __init__(self, topology_file, update_interval):
        # Server identification
        self.server_id = None
        self.server_ip = None
        self.server_port = None
        
        # Routing table: destination_id -> RoutingEntry
        self.routing_table = {}
        
        # Neighbor information
        self.neighbors = {}  # neighbor_id -> {'ip': ip, 'port': port, 'cost': cost}
        self.neighbor_last_update = {}  # neighbor_id -> timestamp
        
        # Network information
        self.all_servers = {}  # server_id -> {'ip': ip, 'port': port}
        
        # Configuration
        self.update_interval = update_interval
        self.topology_file = topology_file
        
        # Statistics
        self.packets_received = 0
        
        # Socket for UDP communication
        self.socket = None
        
        # Threading
        self.running = True
        self.lock = threading.Lock()


        # Command handler
        self.command_handler = CommandHandler(self)
        
        # Parse topology file
        self.parse_topology_file()
        
        # Initialize routing table
        self.initialize_routing_table()
        
        # Create UDP socket
        self.create_socket()



    """Check if the given IP and port match this machine"""
    def is_local_server(self, ip, port):
        
        #TODO
        return 
    


    """Initialize the routing table based on topology information"""
    def initialize_routing_table(self):
        #TODO
        return 
    

    #create socket 
    def create_socket(self):

        #TODO
        return 
    

    
    """Create a distance vector update message"""
    def create_update_message(self):
        #TODO
        return 
        

    """Parse a received distance vector update message"""
    def parse_update_message(self, data, sender_addr):
        #TODO
        return 
    


    """Send routing update to all neighbors"""
    def send_update_to_neighbors(self):
        #TODO
        return 
    

    
    """Update routing table using Bellman-Ford algorithm"""
    def update_routing_table(self, sender_id, entries):
        #TODO
        return 
    


    """Check for neighbors that haven't sent updates recently"""
    def check_neighbor_timeouts(self):
        #TODO
        return 
    

  

    """Thread for sending periodic routing updates"""
    def periodic_update_thread(self):
        #TODO
        return  
    


    """Thread for receiving and processing messages"""
    def receive_thread(self):
        #TODO
        return  
    


    """Thread for handling user commands"""
    def command_thread(self):

         #TODO
        return 
    
    """Main server execution"""
    def run(self):
        
         #TODO
        return 



"""Main entry point"""
def main():
    """Main entry point"""


if __name__ == '__main__':
    main()