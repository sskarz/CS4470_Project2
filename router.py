import time

class RoutingEntry:
    """Data structure for routing table entry"""
    def __init__(self, destination_id, next_hop_id, cost):
        self.destination_id = destination_id
        self.next_hop_id = next_hop_id
        self.cost = cost
        self.last_update_time = time.time()