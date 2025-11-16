import time
from typing import Dict, Any, Tuple, Optional

INFINITY = float('inf')

class CommandHandler:
    """Handles all user commands for the DV server"""
    
    def __init__(self, server):
        #server args is the DVServer object 
        
        self.server = server
        self.command_dict = {
            'update': self.handle_update,
            'step': self.handle_step,
            'packets': self.handle_packets,
            'display': self.handle_display,
            'disable': self.handle_disable,
            'crash': self.handle_crash
        }

    def process_command(self, command_line: str) -> Tuple[bool, str]:
        
        #process a command line and execute the appropriate handler
        
        #.strip : removes any accidental whitespace from the beginning or end of a string
        #include \t and \n 
        command_line = command_line.strip()

        #if empty string return with false and printing to user 
        if not command_line:
            return False, "Empty command"
        
        #breaks the string into smaller string using whitespace (defualt)
        parts = command_line.split()

        #lowers characters of the first string which is usually thhe command 
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        #if not within our dicitonary return false and print out to user
        if command not in self.command_dict:
            return False, f"{command_line} Error: Unknown command"
        
        try:
            # Execute the command handler
            handler = self.command_dict[command]
            success, message = handler(args)
            
            if success:
                return True, f"{command_line} SUCCESS"
            else:
                return False, f"{command_line} {message}"
                
        except Exception as e:
            return False, f"{command_line} Error: {str(e)}"
        


    def handle_update(self, args: list) -> Tuple[bool, str]:
        
        #Handle update command: update <server-ID1> <server-ID2> <Link Cost>
        #Updates the link cost between two servers
        #returns tuple (succes,, error_message
        
        if len(args) != 3:
            return False, "Error: Invalid format. Usage: update <server1> <server2> <cost>"
        
        try:
            server1 = int(args[0])
            server2 = int(args[1])
            cost_str = args[2]
            
            # Parse cost (handle 'inf' case)
            if cost_str.lower() == 'inf':
                cost = INFINITY
            else:
                cost = float(cost_str)
                if cost < 0:
                    return False, "Error: Cost cannot be negative"
            
            # Check if this update affects our server
            if self.server.server_id not in [server1, server2]:
                return False, "Error: Update does not affect this server"
            
            # Determine which server is the neighbor
            neighbor_id = server2 if server1 == self.server.server_id else server1
            
            #update neighbor cost
            with self.server.lock:
                if neighbor_id not in self.server.neighbors:
                    return False, "Error: Not a direct neighbor"
                
                # Update the link cost
                self.server.neighbors[neighbor_id]['cost'] = cost
                self.server.neighbor_last_update[neighbor_id] = time.time()
                
                # Update routing table
                if cost == INFINITY:
                    # Link is down, invalidate all routes through this neighbor
                    self._invalidate_routes_through_neighbor(neighbor_id)
                else:
                    # Link cost changed, update direct route if applicable
                    if neighbor_id in self.server.routing_table:
                        if self.server.routing_table[neighbor_id].next_hop_id == neighbor_id:
                            self.server.routing_table[neighbor_id].cost = cost
                            self.server.routing_table[neighbor_id].last_update_time = time.time()
            
            return True, ""
        
        except ValueError:
            return False, "Error: Invalid server ID or cost value"
        

    def handle_step(self, args: list) -> Tuple[bool, str]:
    
        #Handle step command: Send routing update to neighbors immediately
        #args: Command arguments (should be empty)
        #Returns: Tuple of (success, error_message)
        
        if args:
            return False, "Error: step command takes no arguments"
        
        # Send update to all neighbors
        self.server.send_update_to_neighbors()
        return True, ""
    


    def handle_packets(self, args: list) -> Tuple[bool, str]:
            """
            Handle packets command: Display number of packets received
            
            Args:
                args: Command arguments (should be empty)
                
            Returns:
                Tuple of (success, error_message)
            """
            if args:
                return False, "Error: packets command takes no arguments"
            
            with self.server.lock:
                count = self.server.packets_received
                self.server.packets_received = 0
            
            # Print the count after the SUCCESS message
            print(f"Number of packets received: {count}")
            return True, ""
    
    def handle_display(self, args: list) -> Tuple[bool, str]:
        """
        Handle display command: Show current routing table
        
        Args:
            args: Command arguments (should be empty)
            
        Returns:
            Tuple of (success, error_message)
        """
        if args:
            return False, "Error: display command takes no arguments"
        
        # Display routing table after SUCCESS message
        self._display_routing_table()
        return True, ""
    

    
    
    def handle_disable(self, args: list) -> Tuple[bool, str]:
        """
        Handle disable command: disable <server-ID>
        Disables the link to a given neighbor
        
        Args:
            args: Command arguments [server_id]
            
        Returns:
            Tuple of (success, error_message)
        """
        if len(args) != 1:
            return False, "Error: Invalid format. Usage: disable <server-id>"
        
        try:
            server_id = int(args[0])
            
            # Check if it's a valid server ID
            if server_id == self.server.server_id:
                return False, "Error: Cannot disable link to self"
            
            with self.server.lock:
                if server_id not in self.server.neighbors:
                    return False, "Error: Not a neighbor"
                
                # Set link cost to infinity
                self.server.neighbors[server_id]['cost'] = INFINITY
                
                # Invalidate all routes through this neighbor
                self._invalidate_routes_through_neighbor(server_id)
            
            return True, ""
            
        except ValueError:
            return False, "Error: Invalid server ID"
    
    def handle_crash(self, args: list) -> Tuple[bool, str]:
        """
        Handle crash command: Simulate server crash by closing all connections
        
        Args:
            args: Command arguments (should be empty)
            
        Returns:
            Tuple of (success, error_message)
        """
        if args:
            return False, "Error: crash command takes no arguments"
        
        with self.server.lock:
            # Set all neighbor costs to infinity
            for neighbor_id in self.server.neighbors:
                self.server.neighbors[neighbor_id]['cost'] = INFINITY
            
            # Set all routing table costs to infinity (except self)
            for dest_id, entry in self.server.routing_table.items():
                if dest_id != self.server.server_id:
                    entry.cost = INFINITY
                    entry.next_hop_id = -1
        
        # Stop the server
        self.server.running = False
        
        return True, ""
    
    def _invalidate_routes_through_neighbor(self, neighbor_id: int):
        """
        Helper method to invalidate all routes that go through a specific neighbor
        
        Args:
            neighbor_id: The neighbor whose routes should be invalidated
        """
        for dest_id, entry in self.server.routing_table.items():
            if entry.next_hop_id == neighbor_id:
                entry.cost = INFINITY
                entry.next_hop_id = -1
                entry.last_update_time = time.time()
    
    def _display_routing_table(self):
        """
        Helper method to display the routing table in sorted order
        Format: <destination-server-ID> <next-hop-server-ID> <cost-of-path>
        """
        with self.server.lock:
            print("\nRouting Table:")
            sorted_destinations = sorted(self.server.routing_table.keys())
            
            for dest_id in sorted_destinations:
                entry = self.server.routing_table[dest_id]
                
                # Format cost
                if entry.cost == INFINITY:
                    cost_str = "inf"
                else:
                    cost_str = str(int(entry.cost))
                
                # Only display entries with valid next hops
                if entry.next_hop_id != -1 or dest_id == self.server.server_id:
                    print(f"{dest_id} {entry.next_hop_id} {cost_str}")


def validate_server_id(server_id: Any, valid_range: range = range(1, 5)) -> Optional[int]:
    """
    Validate that a server ID is valid
    
    Args:
        server_id: The ID to validate
        valid_range: Valid range of server IDs (default 1-4)
        
    Returns:
        Valid integer server ID or None if invalid
    """
    try:
        sid = int(server_id)
        if sid in valid_range:
            return sid
    except (ValueError, TypeError):
        pass
    return None


def parse_cost(cost_str: str) -> Optional[float]:
    """
    Parse a cost value, handling 'inf' case
    
    Args:
        cost_str: String representation of cost
        
    Returns:
        Float cost value or None if invalid
    """
    if cost_str.lower() == 'inf':
        return INFINITY
    
    try:
        cost = float(cost_str)
        if cost >= 0:
            return cost
    except ValueError:
        pass
    return None
