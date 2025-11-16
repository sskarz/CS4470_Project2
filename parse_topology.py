# topology_parser.py

def _split_neighbor_entry(raw_entry, server_ids):
    """Return (server_id_1, server_id_2, cost) from a neighbor entry string."""
    parts = raw_entry.split()
    if len(parts) == 3:
        return tuple(map(int, parts))

    if len(parts) == 1:
        digits = parts[0]
        if not digits.isdigit():
            raise ValueError(f"Cannot parse neighbor entry '{raw_entry}'")

        server_id_strings = {str(server_id) for server_id in server_ids}
        n = len(digits)

        # Try every possible split to find two server IDs followed by a cost.
        for i in range(1, n - 1):
            left = digits[:i]
            if left not in server_id_strings:
                continue
            for j in range(i + 1, n):
                middle = digits[i:j]
                if middle not in server_id_strings:
                    continue
                right = digits[j:]
                if right:  # cost must have at least one digit
                    return int(left), int(middle), int(right)

    raise ValueError(f"Cannot parse neighbor entry '{raw_entry}'")


def parse_topology(path):
    with open(path) as f:
        lines = [line.strip() for line in f if line.strip()]

    if len(lines) < 2:
        raise ValueError("Topology file must contain num_servers and num_neighbors")

    num_servers = int(lines[0])
    num_neighbors = int(lines[1])

    server_lines = lines[2:2 + num_servers]
    if len(server_lines) != num_servers:
        raise ValueError("Topology file missing server definitions")

    router_map = {}
    for entry in server_lines:
        parts = entry.split()
        if len(parts) != 3:
            raise ValueError(f"Invalid server entry '{entry}'")
        server_id = int(parts[0])
        router_map[server_id] = {'ip': parts[1], 'port': int(parts[2])}

    own_id = int(server_lines[0].split()[0])
    if own_id not in router_map:
        raise ValueError("Own server information not found in router map")

    own_info = {'id': own_id,
                'ip': router_map[own_id]['ip'],
                'port': router_map[own_id]['port']}

    neighbor_lines = lines[2 + num_servers:2 + num_servers + num_neighbors]
    if len(neighbor_lines) != num_neighbors:
        raise ValueError("Topology file missing neighbor entries")

    neighbors = {}
    for entry in neighbor_lines:
        server1, server2, cost = _split_neighbor_entry(entry, router_map.keys())

        if server1 == own_id and server2 in router_map:
            neighbor_id = server2
        elif server2 == own_id and server1 in router_map:
            neighbor_id = server1
        else:
            # Ignore edges not involving this server.
            continue

        neighbors[neighbor_id] = {
            'ip': router_map[neighbor_id]['ip'],
            'port': router_map[neighbor_id]['port'],
            'cost': cost
        }

    return own_info, neighbors

if __name__ == '__main__':
    print(parse_topology('topology.txt'))