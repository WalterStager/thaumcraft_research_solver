import json
from heapq import heappop, heappush
from collections import deque
from collections.abc import Iterable

class AspectRelations:
    """
    Adjacency list graph where each node has some cost
    """
    def __init__(self):
        self.aspect_relations : dict[str, set[str]] = {}
        # useful for displaying in UI
        self.aspect_parents : dict[str, set[str]] = {}
        self.aspect_children : dict[str, set[str]] = {}

        self._build()
        
    def _build(self):
        with open('aspects.json') as aspects_file:
            data = json.load(aspects_file)
        for aspect, components in data.items():
            components = list(components or [])
            for component in components:
                self.aspect_relations.setdefault(component, set()).add(aspect)
                self.aspect_relations.setdefault(aspect, set()).add(component)

                self.aspect_parents.setdefault(component, set()).add(aspect)
                self.aspect_children.setdefault(aspect, set()).add(component)

    def neighbors(self, aspect: str):
        return list(self.aspect_relations.get(aspect, []))

    def all_nodes(self):
        return list(self.aspect_relations.keys())

    def find_path_exact_length(self, start: str, end: str, length: int) -> list[str] | None:
        if length < 0 or start not in self.aspect_relations or end not in self.aspect_relations:
            return None
        if length == 0:
            return [start] if start == end else None

        queue = deque([(start, [start])])
        while queue:
            node, path = queue.popleft()
            path_length = len(path) - 1
            if path_length == length:
                if node == end:
                    return path
                continue
            for neighbor in self.aspect_relations.get(node, []):
                if neighbor in path:
                    continue
                queue.append((neighbor, path + [neighbor]))
        return None

class HexGrid:
    """
    Axial hex coordinates (q, r)
    """
    def __init__(self, radius: int):
        self.radius = max(0, radius - 1)
        self.id_to_coord : dict[int, (int,int)] = {}
        self.coord_to_id : dict[(int,int), int] = {}
        self.adj : dict[int, list[int]] = {}
        self.disabled_nodes : set[int] = set()
        self._build()

    def _build(self):
        rad = self.radius
        # create nodes inside axial radius
        nid = 0
        for q in range(-rad, rad + 1):
            s1 = max(-rad, -q - rad)
            s2 = min(rad, -q + rad)
            for r in range(s1, s2 + 1):
                coord = (q, r)
                self.id_to_coord[nid] = coord
                self.coord_to_id[coord] = nid
                self.adj[nid] = []
                nid += 1

        # axial neighbor directions
        dirs = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]
        for i, coord in self.id_to_coord.items():
            q, r = coord
            for dq, dr in dirs:
                ncoord = (q + dq, r + dr)
                if ncoord in self.coord_to_id:
                    nid = self.coord_to_id[ncoord]
                    self.adj[i].append(nid)

    def disable_id(self, node_id: int):
        if (node_id in self.id_to_coord):
            self.disabled_nodes.add(node_id)

    def enable_id(self, node_id: int):
        if (node_id in self.disabled_nodes):
            self.disabled_nodes.remove(node_id)

    def neighbors(self, node_id: int):
        return list([x for x in self.adj.get(node_id, []) if not x in self.disabled_nodes])

    def node_count(self):
        return len([x for x in self.adj if not x in self.disabled_nodes])

    def all_nodes(self):
        return list([x for x in self.adj.keys() if not x in self.disabled_nodes])
    
    def find_path_minimum_length(self, start: int, ends: list[int], minimum_length: int) -> list[int] | None:
        if start not in self.adj or start in self.disabled_nodes:
            return None
        targets = {end for end in ends if end in self.adj and end not in self.disabled_nodes}
        if not targets:
            return None

        queue = deque([(start, [start])])
        min_len = max(0, minimum_length)

        while queue:
            node, path = queue.popleft()
            distance = len(path) - 1
            if node in targets and distance >= min_len:
                return path
            for neighbor in self.neighbors(node):
                if neighbor in path:
                    continue
                queue.append((neighbor, path + [neighbor]))
        return None
