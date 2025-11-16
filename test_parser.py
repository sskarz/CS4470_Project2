#!/usr/bin/env python3
"""
Test script for topology parser
"""

import sys
from parse_topology import TopologyParser, parse_cost, validate_ip, validate_port, INFINITY

def main():
    print("Testing TopologyParser with topology.txt")
    print("=" * 50)
    
    try:
        parser = TopologyParser("topology.txt")
        result = parser.parse()
        
        print("\n✓ Parsing successful!")
        print("\nParsed Results:")
        print(f"  Number of servers: {result['num_servers']}")
        print(f"  Number of neighbors: {result['num_neighbors']}")
        print(f"  My server ID: {result['my_server_id']}")
        print(f"  My IP: {result['my_ip']}")
        print(f"  My port: {result['my_port']}")
        
        print("\n  Servers:")
        for server_id, (ip, port) in sorted(result['servers'].items()):
            print(f"    Server {server_id}: {ip}:{port}")
        
        print("\n  Neighbors:")
        for neighbor_id, cost in sorted(result['neighbors'].items()):
            print(f"    Neighbor {neighbor_id}: cost = {cost}")
        
        print("\n" + "=" * 50)
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

