
import sys
import socket
import threading
import time
import struct
import select
from collections import defaultdict
import argparse
from router import RoutingEntry
from parse_topology import TopologyParser

# constants
INFINITY = 999999  # used for binary packet encoding
TIMEOUT_MULTIPLIER = 3  # number of intervals before neighbor timeout


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
        
        # Parse topology file
        self.parse_topology_file()

        # Initialize routing table
        self.initialize_routing_table()

        # Create UDP socket
        self.create_socket()


    def parse_topology_file(self):
        """Parse topology file and populate server and neighbor information"""
        try:
            parser = TopologyParser(self.topology_file)
            topology_data = parser.parse()

            # extract server information
            self.server_id = topology_data['my_server_id']
            self.server_ip = topology_data['my_ip']
            self.server_port = topology_data['my_port']

            # store all servers in network
            for server_id, (ip, port) in topology_data['servers'].items():
                self.all_servers[server_id] = {'ip': ip, 'port': port}

            # store neighbor information with costs
            for neighbor_id, cost in topology_data['neighbors'].items():
                neighbor_info = self.all_servers[neighbor_id]
                self.neighbors[neighbor_id] = {
                    'ip': neighbor_info['ip'],
                    'port': neighbor_info['port'],
                    'cost': cost
                }
                # initialize last update time
                self.neighbor_last_update[neighbor_id] = time.time()

            print(f"Server {self.server_id} initialized at {self.server_ip}:{self.server_port}")
            print(f"Neighbors: {list(self.neighbors.keys())}")

        except Exception as e:
            print(f"Error parsing topology file: {e}")
            sys.exit(1)


    def initialize_routing_table(self):
        """Initialize routing table with direct neighbor costs and infinity for others

        DATA STRUCTURE: Routing Table
        - Key: destination_id (int)
        - Value: RoutingEntry object containing:
            * destination_id: ID of destination server
            * next_hop_id: ID of next hop server (direct neighbor)
            * cost: Total cost to reach destination
            * last_update_time: Timestamp of last update
        """
        with self.lock:
            # add route to self (cost 0)
            self.routing_table[self.server_id] = RoutingEntry(
                destination_id=self.server_id,
                next_hop_id=self.server_id,
                cost=0
            )

            # add routes to direct neighbors
            for neighbor_id, neighbor_info in self.neighbors.items():
                self.routing_table[neighbor_id] = RoutingEntry(
                    destination_id=neighbor_id,
                    next_hop_id=neighbor_id,  # direct neighbor (next hop is itself)
                    cost=neighbor_info['cost']
                )

            # add routes to non-neighbors with inf cost
            for server_id in self.all_servers.keys():
                if server_id not in self.routing_table:
                    self.routing_table[server_id] = RoutingEntry(
                        destination_id=server_id,
                        next_hop_id=None,  # no path known
                        cost=float('inf')
                    )


    def create_socket(self):
        """Create and bind UDP socket to server's port"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.server_ip, self.server_port))
            print(f"UDP socket bound to {self.server_ip}:{self.server_port}")
        except Exception as e:
            print(f"Error creating socket: {e}")
            sys.exit(1) 
    
    

    def parse_update_message(self, data, sender_addr):
        """Parse a received distance vector update message

        DATA STRUCTURE: Distance Vector Update Message (Binary Format)
        Format per PDF specification:
        - Number of update fields (4 bytes)
        - Server port (4 bytes)
        - Server IP (4 bytes)
        - For each entry:
            * Server IP address (4 bytes)
            * Server port (4 bytes)
            * Padding 0x0 (4 bytes)
            * Server ID (4 bytes)
            * Cost (4 bytes)
        """
        try:
            offset = 0

            # parse header: num_fields, sender_port, sender_ip
            num_fields, sender_port = struct.unpack('!II', data[offset:offset+8])
            offset += 8

            sender_ip_bytes = data[offset:offset+4]
            sender_ip = socket.inet_ntoa(sender_ip_bytes)
            offset += 4

            # find sender_id by matching IP and port
            sender_id = None
            for sid, info in self.all_servers.items():
                if info['ip'] == sender_ip and info['port'] == sender_port:
                    sender_id = sid
                    break

            if sender_id is None:
                print(f"Warning: Received message from unknown server {sender_ip}:{sender_port}")
                return None, []

            # parse routing entries
            entries = {}
            for _ in range(num_fields):
                # parse: dest_ip (4), dest_port (4), padding (4), dest_id (4), cost (4)
                dest_ip_bytes = data[offset:offset+4]
                dest_ip = socket.inet_ntoa(dest_ip_bytes)
                offset += 4

                dest_port, padding, dest_id, cost = struct.unpack('!IIII', data[offset:offset+16])
                offset += 16

                # convert INFINITY constant back to float('inf')
                if cost >= INFINITY:
                    cost = float('inf')

                entries[dest_id] = cost

            return sender_id, entries

        except Exception as e:
            print(f"Error parsing update message: {e}")
            return None, [] 
    


    def create_update_message(self):
        """Create a distance vector update message in binary format

        Returns bytes following the DV message format specification
        """
        with self.lock:
            # get routing table entries (exclude self for distance vector)
            entries = [(dest_id, entry) for dest_id, entry in self.routing_table.items()]

        # build message
        num_fields = len(entries)
        sender_port = self.server_port
        sender_ip_bytes = socket.inet_aton(self.server_ip)

        # pack header: num_fields, sender_port, sender_ip
        message = struct.pack('!II', num_fields, sender_port)
        message += sender_ip_bytes

        # pack each routing entry
        for dest_id, entry in entries:
            # get destination server info
            if dest_id in self.all_servers:
                dest_info = self.all_servers[dest_id]
                dest_ip_bytes = socket.inet_aton(dest_info['ip'])
                dest_port = dest_info['port']
            else:
                # unlikely, but handle gracefully
                dest_ip_bytes = socket.inet_aton('0.0.0.0')
                dest_port = 0

            # convert cost: float('inf') -> INFINITY constant
            cost = entry.cost
            if cost == float('inf'):
                cost = INFINITY

            # pack: dest_ip (4), dest_port (4), padding (4), dest_id (4), cost (4)
            message += dest_ip_bytes
            message += struct.pack('!IIII', dest_port, 0, dest_id, int(cost))

        return message


    def send_update_to_neighbors(self):
        """Send routing update to all neighbors"""
        if not self.running:
            return

        message = self.create_update_message()
        print(message)

        # send to each neighbor
        for neighbor_id, neighbor_info in self.neighbors.items():
            try:
                neighbor_addr = (neighbor_info['ip'], neighbor_info['port'])
                print(f"NEIGHBOR ADDR: {neighbor_addr}")
                self.socket.sendto(message, neighbor_addr)
                print(f"SOCKET SENT!")
            except Exception as e:
                print(f"Error sending update to neighbor {neighbor_id}: {e}") 
    

    
    def update_routing_table(self, sender_id, entries):
        """Update routing table using Bellman-Ford algorithm

        Bellman-Ford equation: D_x(y) = min_v{c(x,v) + D_v(y)}
        Where:
        - D_x(y) = cost from x to y
        - c(x,v) = cost from x to neighbor v
        - D_v(y) = cost from neighbor v to destination y

        Args:
            sender_id: ID of the neighbor sending the update
            entries: Dictionary of {destination_id: cost} from sender's routing table
        """
        # verify sender is a neighbor
        if sender_id not in self.neighbors:
            return

        # Ggt cost to sender (neighbor)
        cost_to_sender = self.neighbors[sender_id]['cost']

        table_changed = False

        with self.lock:
            # for each destination in the received distance vector
            for dest_id, sender_cost in entries.items():
                # skip if destination is self
                if dest_id == self.server_id:
                    continue

                # calculate new cost via this neighbor
                # new_cost = cost(self -> sender) + cost(sender -> dest)
                new_cost = cost_to_sender + sender_cost

                # get current cost to destination
                if dest_id in self.routing_table:
                    current_entry = self.routing_table[dest_id]
                    current_cost = current_entry.cost
                else:
                    # unknown destination, initialize with inf
                    current_cost = float('inf')
                    self.routing_table[dest_id] = RoutingEntry(
                        destination_id=dest_id,
                        next_hop_id=None,
                        cost=float('inf')
                    )
                    current_entry = self.routing_table[dest_id]

                # update if new path is better
                if new_cost < current_cost:
                    current_entry.next_hop_id = sender_id
                    current_entry.cost = new_cost
                    current_entry.last_update_time = time.time()
                    table_changed = True

                # if current path goes through sender, update cost even if not better
                # (sender's view of the network changed)
                elif current_entry.next_hop_id == sender_id and new_cost != current_cost:
                    current_entry.cost = new_cost
                    current_entry.last_update_time = time.time()
                    table_changed = True

        return table_changed 
    


    def check_neighbor_timeouts(self):
        """Check for neighbors that haven't sent updates recently

        If no update received for 3 consecutive intervals, mark neighbor as dead
        by setting link cost to infinity
        """
        current_time = time.time()
        timeout_threshold = TIMEOUT_MULTIPLIER * self.update_interval

        with self.lock:
            for neighbor_id, last_update in list(self.neighbor_last_update.items()):
                time_since_update = current_time - last_update

                # check if neighbor has timed out
                if time_since_update > timeout_threshold:
                    # set neighbor cost to infinity (but keep entry)
                    if self.neighbors[neighbor_id]['cost'] != float('inf'):
                        print(f"Neighbor {neighbor_id} timed out (no update for {time_since_update:.1f}s)")
                        self.neighbors[neighbor_id]['cost'] = float('inf')

                        # update routing table entries that use this neighbor
                        for dest_id, entry in self.routing_table.items():
                            if entry.next_hop_id == neighbor_id:
                                entry.cost = float('inf')
                                entry.last_update_time = time.time() 
    

    def handle_update_command(self, server1, server2, new_cost):
        """Handle the update command to change link cost

        Args:
            server1: First server ID
            server2: Second server ID
            new_cost: New link cost (can be 'inf' for infinity)

        Returns:
            Success message or error message
        """
        try:
            server1 = int(server1)
            server2 = int(server2)

            # parse cost - handle 'inf' string
            if isinstance(new_cost, str) and new_cost.lower() == 'inf':
                new_cost = float('inf')
            else:
                new_cost = float(new_cost)

            # verify one of the servers is this server
            if server1 != self.server_id and server2 != self.server_id:
                return f"update {server1} {server2} {new_cost} Error: Neither server is this server ({self.server_id})"

            # determine which is the neighbor
            neighbor_id = server2 if server1 == self.server_id else server1

            # verify the other server is actually a neighbor
            if neighbor_id not in self.neighbors:
                return f"update {server1} {server2} {new_cost} Error: Server {neighbor_id} is not a neighbor"

            # update the link cost
            with self.lock:
                self.neighbors[neighbor_id]['cost'] = new_cost

                # update routing table entry for this neighbor
                if neighbor_id in self.routing_table:
                    self.routing_table[neighbor_id].cost = new_cost
                    self.routing_table[neighbor_id].last_update_time = time.time()

            return f"update {server1} {server2} {new_cost} SUCCESS"

        except ValueError as e:
            return f"update {server1} {server2} {new_cost} Error: Invalid parameters - {e}" 
    


    def handle_disable_command(self, server_id):
        """Handle the disable command to disable link to a neighbor

        Args:
            server_id: ID of neighbor to disable

        Returns:
            Success message or error message
        """
        try:
            server_id = int(server_id)

            # verify server is a neighbor
            if server_id not in self.neighbors:
                return f"disable {server_id} Error: Server {server_id} is not a neighbor"

            # set link cost to infinity
            with self.lock:
                self.neighbors[server_id]['cost'] = float('inf')

                # update routing table
                if server_id in self.routing_table:
                    self.routing_table[server_id].cost = float('inf')
                    self.routing_table[server_id].last_update_time = time.time()

                # update all routes that go through this neighbor
                for dest_id, entry in self.routing_table.items():
                    if entry.next_hop_id == server_id:
                        entry.cost = float('inf')
                        entry.last_update_time = time.time()

            return f"disable {server_id} SUCCESS"

        except ValueError as e:
            return f"disable {server_id} Error: Invalid server ID - {e}" 
    
    
    def handle_crash_command(self):
        """Handle the crash command to close all connections

        Stops the server and closes the socket
        """
        print("crash SUCCESS")
        print("Server crashing - closing all connections")
        self.running = False

        # Close socket
        if self.socket:
            self.socket.close()

        # Exit the program
        sys.exit(0)  
    


    def display_routing_table(self):
        """Display the current routing table in sorted order

        Format: <destination-server-ID> <next-hop-server-ID> <cost-of-path>
        One entry per line, sorted by destination server ID
        """
        with self.lock:
            # get all routing entries sorted by destination ID
            sorted_entries = sorted(self.routing_table.items(), key=lambda x: x[0])

        print("display SUCCESS")
        for dest_id, entry in sorted_entries:
            # format next hop - use '-' if no path known
            next_hop = entry.next_hop_id if entry.next_hop_id is not None else '-'

            # format cost - use 'inf' for infinity
            if entry.cost == float('inf'):
                cost_str = 'inf'
            else:
                cost_str = str(int(entry.cost))

            print(f"{dest_id} {next_hop} {cost_str}")

        # Print detailed routing table view
        print("\n=== Detailed Routing Table ===")
        for dest_id, entry in sorted_entries:
            next_hop_str = str(entry.next_hop_id) if entry.next_hop_id is not None else "None"
            cost_str = "inf" if entry.cost == float('inf') else str(entry.cost)
            print(f"  Dest: {dest_id:3d} | Next Hop: {next_hop_str:4s} | Cost: {cost_str:>6s}")
        print("=" * 30)  
    


    def periodic_update_thread(self):
        """Thread for sending periodic routing updates

        Sends updates at regular intervals and checks for neighbor timeouts
        """
        while self.running:
            time.sleep(self.update_interval)

            if not self.running:
                break

            # check for neighbor timeouts
            self.check_neighbor_timeouts()

            # send updates to all neighbors
            self.send_update_to_neighbors()  
    


    def receive_thread(self):
        """Thread for receiving and processing messages

        Listens for UDP packets and processes distance vector updates
        """
        while self.running:
            try:
                # set timeout to check self.running periodically
                self.socket.settimeout(1.0)

                try:
                    data, sender_addr = self.socket.recvfrom(4096)
                except socket.timeout:
                    continue

                if not self.running:
                    break

                # increment packet counter
                self.packets_received += 1

                # parse the update message
                sender_id, entries = self.parse_update_message(data, sender_addr)

                if sender_id is not None:
                    print(f"RECEIVED A MESSAGE FROM SERVER {sender_id}")

                    # update neighbor's last update time
                    if sender_id in self.neighbor_last_update:
                        self.neighbor_last_update[sender_id] = time.time()

                    # update routing table with Bellman-Ford
                    self.update_routing_table(sender_id, entries)

            except Exception as e:
                if self.running:
                    print(f"Error in receive thread: {e}")  
    


    def command_thread(self):
        """Thread for handling user commands

        Reads commands from stdin and executes them
        """
        print("\nServer ready. Enter commands (update, step, packets, display, disable, crash):")

        while self.running:
            try:
                command_line = input().strip()

                if not command_line:
                    continue

                parts = command_line.split()
                command = parts[0].lower()

                if command == 'update':
                    if len(parts) != 4:
                        print("update Error: Usage: update <server-ID1> <server-ID2> <cost>")
                    else:
                        result = self.handle_update_command(parts[1], parts[2], parts[3])
                        print(result)

                elif command == 'step':
                    print("step SUCCESS")
                    self.send_update_to_neighbors()

                elif command == 'packets':
                    print(f"packets SUCCESS")
                    print(f"{self.packets_received}")
                    self.packets_received = 0

                elif command == 'display':
                    self.display_routing_table()

                elif command == 'disable':
                    if len(parts) != 2:
                        print("disable Error: Usage: disable <server-ID>")
                    else:
                        result = self.handle_disable_command(parts[1])
                        print(result)

                elif command == 'crash':
                    self.handle_crash_command()

                else:
                    print(f"Unknown command: {command}")

            except EOFError:
                # handle EOF
                break
            except Exception as e:
                if self.running:
                    print(f"Error processing command: {e}") 
    
    def run(self):
        """Main server execution

        Starts all threads and waits for them to complete
        """
        # start periodic update thread
        update_thread = threading.Thread(target=self.periodic_update_thread, daemon=True)
        update_thread.start()

        # start receive thread
        recv_thread = threading.Thread(target=self.receive_thread, daemon=True)
        recv_thread.start()

        # start command thread (runs in main thread to handle input properly)
        try:
            self.command_thread()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            self.running = False



def main():
    """Main entry point

    Parse command line arguments and start the DV server
    """
    parser = argparse.ArgumentParser(description='Distance Vector Routing Protocol Server')
    parser.add_argument('-t', '--topology', required=True, help='Topology file name')
    parser.add_argument('-i', '--interval', required=True, type=int, help='Routing update interval in seconds')

    args = parser.parse_args()

    # create and run server
    try:
        server = DVServer(args.topology, args.interval)
        server.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()