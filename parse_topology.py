"""
Topology file parser for Distance Vector Routing Protocol
"""

import re

# Infinity constant for unreachable nodes
INFINITY = float('inf')

def parse_cost(cost_str):
    """
    Parse cost string to float
    
    Args:
        cost_str: String representation of cost (e.g., "10", "inf", "INF")
    
    Returns:
        float: Cost value, or INFINITY if string represents infinity
    
    Raises:
        ValueError: If cost string is invalid
    """
    cost_str = cost_str.strip().lower()
    if cost_str in ['inf', 'infinity', '∞']:
        return INFINITY
    try:
        cost = float(cost_str)
        if cost < 0:
            raise ValueError(f"Cost cannot be negative: {cost}")
        return cost
    except ValueError:
        raise ValueError(f"Invalid cost value: {cost_str}")

def validate_ip(ip_str):
    """
    Validate IP address format (IPv4)
    
    Args:
        ip_str: IP address string
    
    Returns:
        bool: True if valid IPv4 address, False otherwise
    """
    # IPv4 pattern: xxx.xxx.xxx.xxx where xxx is 0-255
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip_str):
        return False
    
    # Check each octet is in valid range
    parts = ip_str.split('.')
    try:
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False
        return True
    except ValueError:
        return False

def validate_port(port):
    """
    Validate port number
    
    Args:
        port: Port number (int)
    
    Returns:
        bool: True if valid port (1-65535), False otherwise
    """
    try:
        port_num = int(port)
        return 1 <= port_num <= 65535
    except (ValueError, TypeError):
        return False

class TopologyParser:
    """
    Parser for topology configuration files
    """
    
    def __init__(self, filename):
        """
        Initialize parser with topology filename
        
        Args:
            filename: Path to topology file
        """
        self.filename = filename
        self.num_servers = 0
        self.num_neighbors = 0
        self.servers = {}  # server_id -> (ip, port)
        self.neighbors = {}  # neighbor_id -> cost
        self.my_server_id = None
        self.my_ip = None
        self.my_port = None
    
    def parse(self):
        """
        Parse the topology file
        
        Returns:
            dict: Parsed topology information
        
        Raises:
            ValueError: If file format is invalid
        """
        try:
            with open(self.filename, 'r') as f:
                lines = [line.strip() for line in f if line.strip()]
            
            if len(lines) < 2:
                raise ValueError("Topology file too short")
            
            # Line 1: number of servers
            self.num_servers = int(lines[0])
            
            # Line 2: number of neighbors
            self.num_neighbors = int(lines[1])
            
            # Next num_servers lines: server info
            server_line_start = 2
            server_line_end = server_line_start + self.num_servers
            
            if len(lines) < server_line_end:
                raise ValueError("Not enough server entries")
            
            for i in range(server_line_start, server_line_end):
                parts = lines[i].split()
                if len(parts) != 3:
                    raise ValueError(f"Invalid server entry at line {i+1}: {lines[i]}")
                
                server_id = int(parts[0])
                server_ip = parts[1]
                server_port = int(parts[2])
                
                if not validate_ip(server_ip):
                    raise ValueError(f"Invalid IP address: {server_ip}")
                if not validate_port(server_port):
                    raise ValueError(f"Invalid port: {server_port}")
                
                self.servers[server_id] = (server_ip, server_port)
            
            # Next num_neighbors lines: neighbor entries in concatenated format
            # Format: <server-ID1><server-ID2><cost> as a single number
            # Example: 127 means server 1 to server 2 with cost 7
            neighbor_line_start = server_line_end
            neighbor_line_end = neighbor_line_start + self.num_neighbors
            
            if len(lines) < neighbor_line_end:
                raise ValueError("Not enough neighbor entries")
            
            for i in range(neighbor_line_start, neighbor_line_end):
                entry_str = lines[i].strip()
                
                if not entry_str:
                    raise ValueError(f"Empty neighbor entry at line {i+1}")
                
                try:
                    entry_num = int(entry_str)
                except ValueError:
                    raise ValueError(f"Invalid neighbor entry at line {i+1}: {lines[i]}. Expected a number in format <server-ID1><server-ID2><cost>")
                
                # Parse the concatenated number: first digit = server-ID1, second digit = server-ID2, rest = cost
                entry_digits = list(entry_str)
                
                if len(entry_digits) < 3:
                    raise ValueError(f"Invalid neighbor entry at line {i+1}: {lines[i]}. Number too short (need at least 3 digits)")
                
                server_id1 = int(entry_digits[0])
                server_id2 = int(entry_digits[1])
                cost_str = ''.join(entry_digits[2:])
                cost = parse_cost(cost_str)
                
                # First neighbor entry tells us which server we are (server-ID1)
                if i == neighbor_line_start:
                    self.my_server_id = server_id1
                    if self.my_server_id not in self.servers:
                        raise ValueError(f"My server ID {self.my_server_id} not in server list")
                    self.my_ip, self.my_port = self.servers[self.my_server_id]
                
                # All neighbor entries should have our server ID as first element
                if server_id1 != self.my_server_id:
                    raise ValueError(f"Neighbor entry at line {i+1} doesn't match my server ID. Expected {self.my_server_id}, got {server_id1}: {lines[i]}")
                
                if server_id2 not in self.servers:
                    raise ValueError(f"Neighbor {server_id2} not in server list")
                
                if server_id2 == self.my_server_id:
                    raise ValueError(f"Neighbor entry cannot have same server ID for both server-ID1 and server-ID2: {lines[i]}")
                
                self.neighbors[server_id2] = cost
            
            return {
                'num_servers': self.num_servers,
                'num_neighbors': self.num_neighbors,
                'servers': self.servers,
                'neighbors': self.neighbors,
                'my_server_id': self.my_server_id,
                'my_ip': self.my_ip,
                'my_port': self.my_port
            }
        
        except FileNotFoundError:
            raise ValueError(f"Topology file not found: {self.filename}")
        except Exception as e:
            raise ValueError(f"Error parsing topology file: {str(e)}")