# topology_parser.py
import re

def parse_topology(path):
    
    with open(path) as f:
        lines = [l.strip() for l in f if l.strip()]

    num_servers   = int(lines[0])
    num_neighbors = int(lines[1])

    # line 2 – own info
    own_line = lines[2].split()
    own_id, own_ip, own_port = map(int, own_line[:3]) if len(own_line)==3 else (int(own_line[0]), own_line[1], int(own_line[2]))

    # next `num_servers` lines – all routers
    router_map = {}
    for i in range(num_servers):
        parts = lines[3+i].split()
        rid, ip, port = int(parts[0]), parts[1], int(parts[2])
        router_map[rid] = {'ip': ip, 'port': port}

    # last `num_neighbors` lines – links
    neighbors = {}
    for i in range(num_neighbors):
        a,b,cost = map(int, lines[3+num_servers+i].split())
        if a == own_id:
            neighbors[b] = {'ip': router_map[b]['ip'],
                            'port': router_map[b]['port'],
                            'cost': cost}
        elif b == own_id:          # ensure symmetry
            neighbors[a] = {'ip': router_map[a]['ip'],
                            'port': router_map[a]['port'],
                            'cost': cost}

    return {'id': own_id, 'ip': own_ip, 'port': own_port}, neighbors
