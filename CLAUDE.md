# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Distance Vector Routing Protocol implementation using the Bellman-Ford algorithm. Servers communicate via UDP to build and maintain routing tables for determining shortest paths in a network.

## Running and Testing

### Run the main DV routing server
```bash
python3 dv.py -t <topology_file> -i <update_interval>
```

Example for local testing:
```bash
# Terminal 1
python3 dv.py -t topology1.txt -i 5

# Terminal 2
python3 dv.py -t topology2.txt -i 5

# Terminal 3
python3 dv.py -t topology3.txt -i 5
```

### Generate topology files
```bash
# Local testing (same machine, different ports)
python3 generate_topologies.py --local

# Remote testing (different machines)
python3 generate_topologies.py --remote
```

### Run parser tests
```bash
python3 test_parser.py
```

## Architecture

### Core Components

**DVServer** (`dv.py:18-618`)
- Main routing protocol implementation using three concurrent threads:
  - **Update Thread**: Sends routing updates at regular intervals and checks for neighbor timeouts
  - **Receive Thread**: Listens for incoming UDP packets and processes distance vector updates
  - **Command Thread**: Processes user commands (display, update, disable, crash, etc.)
- Thread-safe routing table updates using locks (`self.lock`)

**RoutingEntry** (`router.py:3-9`)
- Data structure for routing table entries
- Contains: `destination_id`, `next_hop_id`, `cost`, `last_update_time`

**TopologyParser** (`parse_topology.py:76-206`)
- Parses topology configuration files
- Validates IP addresses and port numbers
- Uses concatenated format for neighbor entries: `<server-ID1><server-ID2><cost>` (e.g., "125" = server 1 to server 2 with cost 5)

### Key Data Structures

**Routing Table** (`dv.py:27`)
```python
self.routing_table = {}  # destination_id -> RoutingEntry
```

**Neighbor Information** (`dv.py:30-31`)
```python
self.neighbors = {}  # neighbor_id -> {'ip': ip, 'port': port, 'cost': cost}
self.neighbor_last_update = {}  # neighbor_id -> timestamp
```

**Distance Vector Message Format** (Binary UDP packets)
```
[num_fields(4B)][port(4B)][IP(4B)]
[dest_IP(4B)][dest_port(4B)][padding(4B)][dest_ID(4B)][cost(4B)] (repeated)
```
All integers use network byte order (big-endian).

### Algorithm Implementation

**Bellman-Ford Equation** (`dv.py:264-325`)
```
D_x(y) = min_v { c(x,v) + D_v(y) }
```
- `D_x(y)` = cost of least-cost path from x to y
- `c(x,v)` = cost from x to neighbor v
- `D_v(y)` = neighbor v's cost to destination y

**Failure Detection** (`dv.py:329-353`)
- If no update received from neighbor for `3 × interval` seconds, mark as failed (cost = infinity)
- Routing tables automatically reconverge around failures

### Constants

- `INFINITY = 999999` (for binary packet encoding in `dv.py:14`)
- `INFINITY = float('inf')` (for internal calculations in `parse_topology.py:8`)
- `TIMEOUT_MULTIPLIER = 3` (intervals before neighbor timeout in `dv.py:15`)

## Topology File Format

```
<num_servers>
<num_neighbors>
<server_id> <ip> <port>
...
<concatenated_neighbor_entry>
...
```

Example:
```
3
2
1 127.0.0.1 5001
2 127.0.0.1 5002
3 127.0.0.1 5003
125
138
```

The concatenated format combines: `<from_server><to_server><cost>`
- Line "125" = Server 1 → Server 2, cost 5
- Line "138" = Server 1 → Server 3, cost 8

## Interactive Commands

When a server is running, these commands are available:

- `display` - Show current routing table
- `packets` - Display number of packets received (and reset counter)
- `step` - Send immediate routing update to neighbors
- `update <s1> <s2> <cost>` - Update link cost between servers
- `disable <server>` - Disable link to a neighbor (set cost to infinity)
- `crash` - Shutdown the server

## Important Implementation Details

### Thread Safety
All routing table modifications are protected by `self.lock` to prevent race conditions between the update, receive, and command threads.

### Message Parsing and Creation
- `parse_update_message()` (`dv.py:143-201`) - Converts binary UDP packets to routing entries
- `create_update_message()` (`dv.py:205-244`) - Converts routing table to binary UDP packets
- `INFINITY` constant is used for binary encoding; `float('inf')` is used internally

### Routing Table Updates
- Updates happen when receiving distance vectors from neighbors
- Current route is updated if: (1) new cost is better, or (2) current path goes through sender and sender's view changed
- All routes through a failed neighbor are marked with infinity cost

### Local vs Remote Testing
- **Local**: Use `127.0.0.1` with different ports (5001, 5002, 5003) to avoid port conflicts
- **Remote**: Use actual IP addresses (e.g., `192.168.1.100`) with same port since each server runs on different machine
