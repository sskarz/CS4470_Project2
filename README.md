# Distance Vector Routing Protocol

CS4470 Computer Networking Protocols - Programming Assignment 2

## Overview

This project implements a Distance Vector Routing Protocol using the Bellman-Ford algorithm. Servers exchange routing information via UDP to build and maintain routing tables that determine the shortest paths to all destinations in the network.

## Team Members

- Andy Su
- Joshua Soteras
- Sanskar Thapa

## Project Structure

```
├── dv.py                      # Main DV routing protocol implementation
├── router.py                  # RoutingEntry data structure
├── parse_topology.py          # Topology file parser
├── generate_topologies.py     # Topology file generator
├── test_parser.py            # Parser unit tests
```

## Requirements

- Python 3.x
- Standard library only (no external dependencies)

## Quick Start

### Local Testing (Single Machine)

1. **Generate topology files**:

   ```bash
   python3 generate_topologies.py --local
   ```

2. **Open 3 separate terminal windows** and run:

   ```bash
   # Terminal 1
   python3 dv.py -t topology1.txt -i 5

   # Terminal 2
   python3 dv.py -t topology2.txt -i 5

   # Terminal 3
   python3 dv.py -t topology3.txt -i 5
   ```

3. **Wait 5-10 seconds** for routing tables to converge

4. **Test commands** (in any terminal):
   ```
   display           # View routing table
   packets           # Show packet count
   step              # Send immediate update
   ```

### Remote Testing (Multiple Machines)

1. **Find each teammate's IP address**:

   - Mac/Linux: `ifconfig | grep "inet "`
   - Windows: `ipconfig`
   - Look for addresses like `192.168.x.x` or `10.x.x.x`

2. **Generate topology files** (one person runs this):

   ```bash
   python3 generate_topologies.py --remote
   ```

   Enter when prompted:

   ```
   Server 1 IP address: 192.168.1.100
   Server 2 IP address: 192.168.1.101
   Server 3 IP address: 192.168.1.102
   Port number (e.g., 4091): 4091
   ```

3. **Distribute files**:

   - Send `topology2.txt` to teammate running Server 2
   - Send `topology3.txt` to teammate running Server 3

4. **Each teammate runs** on their machine:

   ```bash
   # Server 1's machine
   python3 dv.py -t topology1.txt -i 5

   # Server 2's machine
   python3 dv.py -t topology2.txt -i 5

   # Server 3's machine
   python3 dv.py -t topology3.txt -i 5
   ```

5. **Important**:
   - All computers must be on the same network
   - Firewalls must allow UDP traffic on the chosen port
   - Do NOT use `127.0.0.1` for remote testing (use actual IP addresses)

## Topology Generator (`generate_topologies.py`)

### How It Works

The topology generator creates configuration files for each server in the network. Each file contains:

- Number of servers in the network
- Number of direct neighbors for this server
- IP addresses and ports for all servers
- Link costs to direct neighbors (in concatenated format)

### Usage Modes

#### 1. Local Mode (`--local`)

**Use case**: Testing on a single machine with multiple terminal windows

```bash
python3 generate_topologies.py --local
```

**What it does**:

- Creates 3 topology files (topology1.txt, topology2.txt, topology3.txt)
- Uses `127.0.0.1` for all servers
- Assigns different ports: 5001, 5002, 5003
- No port conflicts when running multiple instances locally

**Default network**:

```
Server 1 ←→ Server 2 (cost: 5)
Server 1 ←→ Server 3 (cost: 8)
Server 2 ←→ Server 3 (cost: 3)
```

#### 2. Remote Mode (`--remote`)

**Use case**: Testing across multiple physical machines (teammate collaboration)

```bash
python3 generate_topologies.py --remote
```

**What it does**:

- Prompts for each teammate's IP address
- Prompts for a port number (same port for all since different machines)
- Creates topology files with actual network IP addresses
- Each teammate can run their server on their own computer

**Important**:

- Use actual IP addresses (e.g., `192.168.1.100`), NOT `127.0.0.1`
- All machines must be on the same network
- Same port is fine since each server runs on a different machine

**What it does**:

- Interactive setup for any number of servers
- Specify custom link costs between neighbors
- Full control over network topology

## Command Line Arguments

### `dv.py`

```bash
python3 dv.py -t <topology_file> -i <update_interval>
```

**Arguments**:

- `-t, --topology`: Path to topology file (required)
- `-i, --interval`: Update interval in seconds (required)

**Example**:

```bash
python3 dv.py -t topology1.txt -i 5
```

## Interactive Commands

Once a server is running, you can enter these commands:

| Command                   | Description                                | Example         |
| ------------------------- | ------------------------------------------ | --------------- |
| `display`                 | Show current routing table                 | `display`       |
| `packets`                 | Display number of packets received         | `packets`       |
| `step`                    | Send immediate routing update to neighbors | `step`          |
| `update <s1> <s2> <cost>` | Update link cost between servers           | `update 1 2 10` |
| `disable <server>`        | Disable link to a neighbor                 | `disable 2`     |
| `crash`                   | Shutdown this server                       | `crash`         |

### Command Examples

**View routing table**:

```
> display
SUCCESS
1 1 0
2 2 5
3 2 8
```

Output format: `<destination> <next_hop> <cost>`

**Change link cost**:

```
> update 1 2 10
SUCCESS
```

Updates the cost of the link between Server 1 and Server 2 to 10

**Disable a neighbor**:

```
> disable 2
SUCCESS
```

Sets the cost to Server 2 to infinity (simulates link failure)

**Check packet statistics**:

```
> packets
SUCCESS
Packets received: 42
```

## Topology File Format

Each topology file follows this format:

```
<num_servers>
<num_neighbors>
<server_id> <ip> <port>
<server_id> <ip> <port>
...
<concatenated_neighbor_entry>
<concatenated_neighbor_entry>
...
```

**Example** (`topology1.txt`):

```
3
2
1 127.0.0.1 5001
2 127.0.0.1 5002
3 127.0.0.1 5003
125
138
```

**Explanation**:

- Line 1: `3` = 3 servers in the network
- Line 2: `2` = Server 1 has 2 neighbors
- Lines 3-5: Server information (ID, IP, port)
- Line 6: `125` = Server **1** → Server **2**, cost **5**
- Line 7: `138` = Server **1** → Server **3**, cost **8**

The concatenated format combines: `<from_server><to_server><cost>`

## How It Works

### Bellman-Ford Algorithm

The Distance Vector protocol uses the Bellman-Ford equation:

```
D_x(y) = min_v { c(x,v) + D_v(y) }
```

Where:

- `D_x(y)` = cost of least-cost path from x to y
- `c(x,v)` = cost from x to neighbor v
- `D_v(y)` = neighbor v's cost to destination y

### Protocol Operation

1. **Initialization**:

   - Parse topology file
   - Initialize routing table (cost 0 to self, direct costs to neighbors, infinity to others)
   - Create UDP socket

2. **Three concurrent threads**:

   - **Update Thread**: Every `interval` seconds, sends routing table to all neighbors
   - **Receive Thread**: Listens for incoming routing updates, applies Bellman-Ford
   - **Command Thread**: Processes user commands (display, update, disable, etc.)

3. **Routing Updates**:

   - Servers exchange their routing tables via UDP
   - Each server computes new shortest paths using Bellman-Ford
   - Tables converge to optimal routes

4. **Failure Detection**:
   - If no update received from a neighbor for 3 × interval seconds, mark as failed (cost = infinity)
   - Routing tables automatically reconverge around the failure

### Message Format

Binary UDP packets use this structure:

```
[num_fields(4B)][port(4B)][IP(4B)]
[dest_IP(4B)][dest_port(4B)][padding(4B)][dest_ID(4B)][cost(4B)] (repeated)
```

All integers use network byte order (big-endian).

## Testing Scenarios

### Scenario 1: Basic Convergence

1. Start all 3 servers
2. Wait 10 seconds
3. Run `display` on each server
4. Verify routing tables show correct shortest paths

### Scenario 2: Link Cost Change

1. On Server 1: `update 1 2 100`
2. Wait for convergence
3. Check if routes through Server 3 are now preferred

### Scenario 3: Link Failure

1. On Server 1: `disable 2`
2. Routes should reconverge using alternative paths

### Scenario 4: Server Crash

1. On Server 2: `crash`
2. Servers 1 and 3 should detect timeout and update routes

## Troubleshooting

**"Address already in use" error**:

- You're trying to run multiple servers with the same port on the same machine
- Solution: Use `--local` mode which assigns different ports (5001, 5002, 5003)

**Servers not communicating**:

- Check that all servers are running
- Verify IP addresses are correct (use `ifconfig` or `ipconfig`)
- Ensure firewall allows UDP traffic on the chosen port
- For remote testing, don't use `127.0.0.1` - use actual IP addresses

**Routing table shows infinity**:

- Servers haven't exchanged updates yet (wait 5-10 seconds)
- Check that other servers are running
- Verify network connectivity

## Implementation Details

**Language**: Python 3

**Key Components**:

- `DVServer` class: Main routing protocol implementation
- `RoutingEntry` class: Stores destination, next hop, cost, and timestamp
- UDP sockets for network communication
- Threading for concurrent update/receive/command operations
- Thread-safe routing table updates using locks

**Files**:

- `dv.py`: Core DV protocol (636 lines)
- `router.py`: Data structures
- `parse_topology.py`: Topology file parsing
- `generate_topologies.py`: Test topology generation

## References

- Bellman-Ford algorithm: Distance Vector routing
- Protocol: UDP-based routing updates
