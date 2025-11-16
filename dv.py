
#libraries 
import sys
import socket
import threading
import time
import struct
import select
from collections import defaultdict
import argparse

from router import Router
from commands import CommandHandler
from parse_topology import TopologyParser



#GLOBAL/CONSTANT VARIABLES
INFINITY = float('inf') 
PACKET_TIMEOUT = 3  # Number of missed updates before marking neighbor as down


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



    #----------------------------------------------------------------------------
    #Confugiration Functions
    #----------------------------------------------------------------------------
    
    #TEMP 
    #just using this for now but will switch to the file sanksar made
    def parse_topology_file(self):
        """Parse the topology file and extract server and neighbor information"""
        with open(self.topology_file, 'r') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        
        # Parse number of servers
        num_servers = int(lines[0])
        
        # Parse number of neighbors
        num_neighbors = int(lines[1])
        
        # Parse server information
        for i in range(2, 2 + num_servers):
            parts = lines[i].split()
            server_id = int(parts[0])
            server_ip = parts[1]
            server_port = int(parts[2])
            
            self.all_servers[server_id] = {'ip': server_ip, 'port': server_port}
            
            # Check if this is our server based on matching IP and port
            if self.is_local_server(server_ip, server_port):
                self.server_id = server_id
                self.server_ip = server_ip
                self.server_port = server_port
        
        # Parse neighbor information
        neighbor_start_line = 2 + num_servers
        for i in range(neighbor_start_line, neighbor_start_line + num_neighbors):
            parts = lines[i].split()
            server1 = int(parts[0])
            server2 = int(parts[1])
            cost = float(parts[2]) if parts[2].lower() != 'inf' else INFINITY
            
            # Determine which server is the neighbor
            if server1 == self.server_id:
                neighbor_id = server2
            else:
                neighbor_id = server1
            
            self.neighbors[neighbor_id] = {
                'ip': self.all_servers[neighbor_id]['ip'],
                'port': self.all_servers[neighbor_id]['port'],
                'cost': cost
            }
            self.neighbor_last_update[neighbor_id] = time.time()

        
    """Check if the given IP and port match this machine"""
    def is_local_server(self, ip, port):
        
        """Check if the given IP and port match this machine"""
        # Try to bind to the port to check if it's available
        try:

            #Creating new socket object 
            #socket.AF_INET -> specific address family , using IPv4 internet protocol
            #socket.SOCK_DGRAM -> specifies socet type -> Datagram which means UDP
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   
            
            #binding a socket to a specific network 
            #tuple passed in
            #'' means the empty string will listen on all available network 
            test_socket.bind(('', port))

            #close the socket 
            test_socket.close()
            return True
        
        except:
            return False
    

    """Initialize the routing table based on topology information"""
    def initialize_routing_table(self):

        """Initialize the routing table based on topology information"""
        # Add entry for self
        self.routing_table[self.server_id] = Router(self.server_id, self.server_id, 0)
  
       # Add entries for all servers
        for server_id in self.all_servers:

            if server_id != self.server_id:

                if server_id in self.neighbors:
            
                    # Direct neighbor
                    cost = self.neighbors[server_id]['cost']
                    # Not a neighbor, cost is infinity                 
                    self.routing_table[server_id] = Router(server_id, server_id, cost)

                else:
                
                    self.routing_table[server_id] = Router(server_id, -1, INFINITY)


    #create socket 
    def create_socket(self):
        
        #Creating new socket object 
        #socket.AF_INET -> specific address family , using IPv4 internet protocol
        #socket.SOCK_DGRAM -> specifies socet type -> Datagram which means UDP
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        #binding a socket to a specific network 
        #tuple passed i
        #'' means the empty string will listen on all available network 
        self.socket.bind(('', self.server_port))

        #configures teh scoket to be non blocking
        #setting to false will immediately raise an error if no data is available
        self.socket.setblocking(False)
        print(f"Server {self.server_id} listening on {self.server_ip}:{self.server_port}")
       


    #----------------------------------------------------------------------------
    #Message Functions
    #----------------------------------------------------------------------------
    
    def create_update_message(self):
        """Create a distance vector update message"""

        # Message format: num_updates(2) + port(2) + ip(4) + [ip(4) + port(2) + pad(2) + id(2) + cost(2)]
        #note each () represenets how many each each field takes

        #using byte array to build message 
        message = bytearray()
        
        #count valid entries (not infinity)
        #converting routing table to a list of tuples 
        valid_entries = [(dest_id, entry) for dest_id, entry in self.routing_table.items()]
        
        #get total bynver of routing entries that will be included in this message
        num_updates = len(valid_entries)
        
        # Number of update fields (2 bytes)
        #struck.pack -> converts python values to binary values
        #! -> use byte order (standard for network communication)
        #H -> pack the value as an unsigned short intger (2 bytes long)
        message.extend(struct.pack('!H', num_updates))
        
        #server port (2 bytes)
        message.extend(struct.pack('!H', self.server_port))
        
        #Server IP (4 bytes)
        #prepare the ipaddress (splits at each '.' into strings )
        ip_parts = [int(x) for x in self.server_ip.split('.')]

        #packs the ip address
        #!BBBB -> format of the string 
        #B -> pack the value as an unsigned char (1 byte)
        #hence BBBB means expecting 4 byte value 
        #*ip_parts unpacks the list into 4 arguments ex [192, 168, 1, 10] into the pack argument 
        message.extend(struct.pack('!BBBB', *ip_parts))
        
        # Add entries
        for dest_id, entry in valid_entries:
            # Destination IP (4 bytes)
            dest_ip = self.all_servers[dest_id]['ip']

            #same as above by splitting the destination IP string into a list of integers
            dest_ip_parts = [int(x) for x in dest_ip.split('.')]
            message.extend(struct.pack('!BBBB', *dest_ip_parts))
            
            # Destination port (2 bytes)
            dest_port = self.all_servers[dest_id]['port']
            #packs the destinatiojns port as a 2byte unsigned short
            message.extend(struct.pack('!H', dest_port))
            
            # Padding (2 bytes)
            #packs the number 0 for padding the message to keep data aligned 
            message.extend(struct.pack('!H', 0))
            
            # Server ID (2 bytes)
            message.extend(struct.pack('!H', dest_id))
            
            # Cost (2 bytes)
            #this block hadles the code 
            if entry.cost == INFINITY:
                cost_val = 65535  # Max value for unsigned short
            else:
                cost_val = int(entry.cost)
            message.extend(struct.pack('!H', cost_val))
        
        #converts the mutable bytearray into an immutable bytes object
        #which is the standard type for sending binary data.
        return bytes(message)

    
    """Parse a received distance vector update message"""
    def parse_update_message(self, data, sender_addr):
       
        #a pointer to track current position in the data
        #i.e. how many bytes are read so far 
        offset = 0
        
        # Number of updates (2 bytes)
        #read the first field of the message
        # data[offset:offset+2]) slices the data taking the first 2 bytes from 0 index
        num_updates = struct.unpack('!H', data[offset:offset+2])[0]
        #read 2 bytes so increment by 2 
        offset += 2
        
        # Sender port (2 bytes)
        sender_port = struct.unpack('!H', data[offset:offset+2])[0]
        offset += 2
        
        # Sender IP (4 bytes)
        #unpacks into tuple of numbers : (192, 168, 1, 10)
        sender_ip_parts = struct.unpack('!BBBB', data[offset:offset+4])
        #converts tuple into string: "192.168.1.10".
        sender_ip = '.'.join(str(x) for x in sender_ip_parts)
        offset += 4
        
        # Find sender ID
        sender_id = None
        for server_id, info in self.all_servers.items():
            if info['ip'] == sender_ip and info['port'] == sender_port:
                sender_id = server_id
                break
        
        if sender_id is None:
            return None
        
        #Parse entries
        #this will be creating rounter entires from the rest of the message 
        entries = []
        for _ in range(num_updates):
            # Destination IP (4 bytes)
            dest_ip_parts = struct.unpack('!BBBB', data[offset:offset+4])
            dest_ip = '.'.join(str(x) for x in dest_ip_parts)
            offset += 4
            
            # Destination port (2 bytes)
            dest_port = struct.unpack('!H', data[offset:offset+2])[0]
            offset += 2
            
            # Padding (2 bytes)
            offset += 2
            
            # Server ID (2 bytes)
            dest_id = struct.unpack('!H', data[offset:offset+2])[0]
            offset += 2
            
            # Cost (2 bytes)
            cost = struct.unpack('!H', data[offset:offset+2])[0]
            if cost == 65535:
                cost = INFINITY
            offset += 2
            
            entries.append({'id': dest_id, 'cost': cost})
        
        return {'sender_id': sender_id, 'entries': entries}

    
    """Send routing update to all neighbors"""
    def send_update_to_neighbors(self):
       
        message = self.create_update_message()
        
        with self.lock:
            for neighbor_id, neighbor_info in self.neighbors.items():
                if neighbor_info['cost'] != INFINITY:
                    try:
                        addr = (neighbor_info['ip'], neighbor_info['port'])
                        self.socket.sendto(message, addr)
                    except Exception as e:
                        print(f"Error sending update to neighbor {neighbor_id}: {e}")

    

    #----------------------------------------------------------------------------
    #Update Functions
    #----------------------------------------------------------------------------
    
    """Update routing table using Bellman-Ford algorithm"""
    def update_routing_table(self, sender_id, entries):
        """Update routing table using Bellman-Ford algorithm"""
        changed = False
        
        with self.lock:
            # Update last heard time for sender
            self.neighbor_last_update[sender_id] = time.time()
            
            # Get cost to sender
            if sender_id not in self.neighbors:
                return False
            
            cost_to_sender = self.neighbors[sender_id]['cost']
            
            if cost_to_sender == INFINITY:
                return False
            
            # Apply Bellman-Ford algorithm
            for entry in entries:
                dest_id = entry['id']
                cost_via_sender = entry['cost']
                
                if cost_via_sender == INFINITY:
                    continue
                
                total_cost = cost_to_sender + cost_via_sender
                
                # Update if this is a better path
                if dest_id in self.routing_table:
                    current_cost = self.routing_table[dest_id].cost
                    
                    # Update if: new path is better OR current next hop is the sender
                    if total_cost < current_cost or self.routing_table[dest_id].next_hop_id == sender_id:
                        if total_cost != current_cost:
                            self.routing_table[dest_id].cost = total_cost
                            self.routing_table[dest_id].next_hop_id = sender_id
                            changed = True
                else:
                    # New destination
                    self.routing_table[dest_id] = Router(dest_id, sender_id, total_cost)
                    changed = True
        
        return changed


    """Check for neighbors that haven't sent updates recently"""
    def check_neighbor_timeouts(self):
        """Check for neighbors that haven't sent updates recently"""
        current_time = time.time()
        timeout_threshold = self.update_interval * PACKET_TIMEOUT

        with self.lock:
            for neighbor_id in list(self.neighbor_last_update.keys()):
                if neighbor_id in self.neighbors and self.neighbors[neighbor_id]['cost'] != INFINITY:
                    last_update = self.neighbor_last_update.get(neighbor_id, 0)
                    if current_time - last_update > timeout_threshold:
                        print(f"Neighbor {neighbor_id} timed out")
                        self.neighbors[neighbor_id]['cost'] = INFINITY
                        
                        # Update routing table entries using this neighbor
                        for dest_id, entry in self.routing_table.items():
                            if entry.next_hop_id == neighbor_id:
                                entry.cost = INFINITY
                                entry.next_hop_id = -1
    

    """Thread for sending periodic routing updates"""
    def periodic_update_thread(self):
        '''
            purpose of this method is to checkf or dead neighbors 

        '''
        while self.running:
            #this is the periodic part 
            time.sleep(self.update_interval)

            if self.running:
                self.check_neighbor_timeouts()
                self.send_update_to_neighbors()
    

    def receive_thread(self):
        """
            - Thread for receiving and processing messages
            - The Listesner and Process 
        """
        while self.running:
            try:
                # Use select with timeout to allow checking self.running
                #select.select monitors lists of osckets
                #blocks (pauses) until one of the other sockets is ready 
                #interest in self.socket
                #1.0 is the timeout
                readable, _, _ = select.select([self.socket], [], [], 1.0)
                
                if readable:
                    #this reads the waiting data (a UDP datagram) from the socket.
                    #4096 is the bugger size 
                    #data  will hold the raw binary data 
                    # addr this variable will hold the IP address 
                    data, addr = self.socket.recvfrom(4096)
                    
                    # Parse the update message
                    update_info = self.parse_update_message(data, addr)
                    
                    if update_info:
                        sender_id = update_info['sender_id']
                        print(f"RECEIVED A MESSAGE FROM SERVER {sender_id}")
                        
                        with self.lock:
                            self.packets_received += 1
                        
                        # Update routing table
                        self.update_routing_table(sender_id, update_info['entries'])
                        
            except Exception as e:
                if self.running:
                    print(f"Error receiving message: {e}")


    def command_thread(self):
        """Thread for handling user commands"""
        while self.running:
            try:
                command = input().strip()
                
                if not command:
                    continue
                
                # Process command using the command handler
                success, message = self.command_handler.process_command(command)
                print(message)
                    
            except KeyboardInterrupt:
                self.running = False
                break
            except Exception as e:
                print(f"Error processing command: {e}")

    
    def run(self):
        """Main server execution"""
        # Start threads
        update_thread = threading.Thread(target=self.periodic_update_thread)
        receive_thread = threading.Thread(target=self.receive_thread)
        
        update_thread.daemon = True
        receive_thread.daemon = True
        
        update_thread.start()
        receive_thread.start()
        
        # Send initial update
        self.send_update_to_neighbors()
        
        # Handle commands in main thread
        self.command_thread()
        
        # Clean up
        self.socket.close()
        print(f"Server {self.server_id} shutting down")



#----------------------------------------------------------------------------
#Execution
#----------------------------------------------------------------------------
    
def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Distance Vector Routing Server')
    parser.add_argument('-t', '--topology', required=True, help='Topology file name')
    parser.add_argument('-i', '--interval', type=int, required=True, help='Routing update interval in seconds')
    
    args = parser.parse_args()
    
    # Create and run server
    server = DVServer(args.topology, args.interval)
    server.run()

if __name__ == '__main__':
    main()