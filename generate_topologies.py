#!/usr/bin/env python3
"""
Generate topology files for DV routing protocol testing

Usage:
    Local testing:  python3 generate_topologies.py --local
    Remote testing: python3 generate_topologies.py --remote
    Custom setup:   python3 generate_topologies.py --custom
"""

import argparse

def get_local_config():
    """Configuration for local testing (same machine, different ports)"""
    servers = {
        1: ('127.0.0.1', 5001),
        2: ('127.0.0.1', 5002),
        3: ('127.0.0.1', 5003),
    }

    topology = {
        1: {2: 5, 3: 8},   # Server 1 neighbors: 2 (cost 5), 3 (cost 8)
        2: {1: 5, 3: 3},   # Server 2 neighbors: 1 (cost 5), 3 (cost 3)
        3: {1: 8, 2: 3},   # Server 3 neighbors: 1 (cost 8), 2 (cost 3)
    }

    return servers, topology


def get_remote_config():
    """Configuration for remote testing (different machines)"""
    print("\n=== Remote Testing Configuration ===")
    print("Enter IP addresses for each teammate's computer")
    print("(Find your IP with 'ifconfig' on Mac/Linux or 'ipconfig' on Windows)\n")

    server1_ip = input("Server 1 IP address: ").strip()
    server2_ip = input("Server 2 IP address: ").strip()
    server3_ip = input("Server 3 IP address: ").strip()

    # Use same port for all (since different machines)
    port = int(input("Port number (e.g., 4091): ").strip())

    servers = {
        1: (server1_ip, port),
        2: (server2_ip, port),
        3: (server3_ip, port),
    }

    # Same topology as local
    topology = {
        1: {2: 5, 3: 8},
        2: {1: 5, 3: 3},
        3: {1: 8, 2: 3},
    }

    return servers, topology


def get_custom_config():
    """Interactive configuration for custom network"""
    print("\n=== Custom Network Configuration ===")

    num_servers = int(input("Number of servers: ").strip())

    # Get server info
    servers = {}
    print(f"\nEnter information for {num_servers} servers:")
    for i in range(1, num_servers + 1):
        print(f"\nServer {i}:")
        ip = input(f"  IP address: ").strip()
        port = int(input(f"  Port: ").strip())
        servers[i] = (ip, port)

    # Get topology (neighbor relationships)
    print("\n=== Network Topology ===")
    print("For each server, list its neighbors and link costs")

    topology = {}
    for server_id in range(1, num_servers + 1):
        print(f"\nServer {server_id} neighbors:")
        num_neighbors = int(input(f"  How many neighbors? ").strip())

        neighbors = {}
        for _ in range(num_neighbors):
            neighbor_id = int(input(f"    Neighbor server ID: ").strip())
            cost = int(input(f"    Link cost to server {neighbor_id}: ").strip())
            neighbors[neighbor_id] = cost

        topology[server_id] = neighbors

    return servers, topology


def generate_topology_files(servers, topology, prefix="topology"):
    """Generate topology files for all servers"""

    for server_id in servers:
        filename = f"{prefix}{server_id}.txt"

        with open(filename, 'w') as f:
            # Line 1: Number of servers
            f.write(f"{len(servers)}\n")

            # Line 2: Number of neighbors for this server
            f.write(f"{len(topology[server_id])}\n")

            # Lines 3+: Server info (all servers)
            for sid in sorted(servers.keys()):
                ip, port = servers[sid]
                f.write(f"{sid} {ip} {port}\n")

            # Neighbor entries (concatenated format)
            for neighbor_id, cost in sorted(topology[server_id].items()):
                entry = f"{server_id}{neighbor_id}{cost}"
                f.write(f"{entry}\n")

        print(f"✓ Created {filename}")


def print_instructions(servers, topology, prefix="topology", mode="local"):
    """Print usage instructions"""
    print("\n" + "="*60)
    print("TOPOLOGY FILES GENERATED")
    print("="*60)

    if mode == "local":
        print("\nLocal Testing Instructions:")
        print("Open separate terminal windows and run:\n")
        for server_id in sorted(servers.keys()):
            print(f"  Terminal {server_id}: python3 dv.py -t {prefix}{server_id}.txt -i 5")

    elif mode == "remote":
        print("\nRemote Testing Instructions:")
        print("Each teammate should:\n")
        for server_id in sorted(servers.keys()):
            ip, _ = servers[server_id]
            print(f"  Server {server_id} (at {ip}):")
            print(f"    1. Copy {prefix}{server_id}.txt to their computer")
            print(f"    2. Run: python3 dv.py -t {prefix}{server_id}.txt -i 5")
            print()

        print("IMPORTANT:")
        print("  - Make sure all computers are on the same network")
        print("  - Firewalls must allow UDP traffic on the chosen port")
        print("  - Verify IP addresses with 'ifconfig' (Mac/Linux) or 'ipconfig' (Windows)")

    print("\nNetwork Topology:")
    for server_id in sorted(servers.keys()):
        neighbors = topology[server_id]
        neighbor_list = [f"{nid} (cost {cost})" for nid, cost in sorted(neighbors.items())]
        print(f"  Server {server_id}: Connected to {', '.join(neighbor_list)}")

    print("\nAvailable Commands:")
    print("  display           - Show routing table")
    print("  step              - Send immediate update")
    print("  packets           - Show packet count")
    print("  update <s1> <s2> <cost> - Change link cost")
    print("  disable <server>  - Disable link")
    print("  crash             - Shutdown server")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description='Generate topology files for DV routing protocol testing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Local testing:   python3 generate_topologies.py --local
  Remote testing:  python3 generate_topologies.py --remote
  Custom network:  python3 generate_topologies.py --custom
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--local', action='store_true',
                       help='Generate for local testing (127.0.0.1, different ports)')
    group.add_argument('--remote', action='store_true',
                       help='Generate for remote testing (different IPs)')
    group.add_argument('--custom', action='store_true',
                       help='Custom configuration (interactive)')

    parser.add_argument('--prefix', default='topology',
                       help='Filename prefix (default: topology)')

    args = parser.parse_args()

    # Get configuration
    if args.local:
        print("Generating topology files for LOCAL testing...")
        servers, topology = get_local_config()
        mode = "local"
    elif args.remote:
        servers, topology = get_remote_config()
        mode = "remote"
    else:  # custom
        servers, topology = get_custom_config()
        mode = "custom"

    # Generate files
    print()
    generate_topology_files(servers, topology, args.prefix)

    # Print instructions
    print_instructions(servers, topology, args.prefix, mode)


if __name__ == '__main__':
    main()
