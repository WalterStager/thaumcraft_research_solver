import json
from heapq import heappop, heappush
from collections import deque
from collections.abc import Iterable

class AspectRelations:
    """
    Adjacency list graph where each node has some cost
    """
    def __init__(self):
        self.aspect_costs : dict[str, int] = {}
        self.aspect_relations : dict[str, set[str]] = {}
        self.aspect_parents : dict[str, set[str]] = {}
        self.aspect_children : dict[str, set[str]] = {}
        self._recipes: dict[str, list[str]] = {}
        self._min_costs: dict[str, dict[str, int]] = {}
        self._build()
        
    def _build(self):
        with open('aspects.json') as aspects_file:
            data = json.load(aspects_file)
        for aspect, components in data.items():
            normalized = list(components or [])
            self.aspect_relations.setdefault(aspect, set())
            self.aspect_children.setdefault(aspect, set())
            self._recipes[aspect] = normalized
            for component in normalized:
                self.aspect_relations.setdefault(component, set()).add(aspect)
                self.aspect_parents.setdefault(component, set()).add(aspect)
                self.aspect_relations[aspect].add(component)
                self.aspect_children[aspect].add(component)
                self._recipes.setdefault(component, [])
        memo: dict[str, int] = {}
        for aspect in self.aspect_relations:
            self.aspect_costs[aspect] = self._resolve_cost(aspect, memo, set())
        self._precompute_min_costs()

    def _resolve_cost(self, aspect: str, memo: dict[str, int], visiting: set[str]) -> int:
        if aspect in memo:
            return memo[aspect]
        if aspect in visiting:
            raise ValueError(f'Cycle detected while computing cost for {aspect}')
        visiting.add(aspect)
        components = self._recipes.get(aspect, [])
        if not components:
            memo[aspect] = 1
        else:
            memo[aspect] = 1 + sum(self._resolve_cost(comp, memo, visiting) for comp in components)
        visiting.remove(aspect)
        return memo[aspect]

    def _precompute_min_costs(self):
        self._min_costs = {}
        for aspect in self.aspect_relations:
            self._min_costs[aspect] = self._dijkstra(aspect)

    def _dijkstra(self, start: str) -> dict[str, int]:
        distances: dict[str, int] = {start: 0}
        frontier: list[tuple[int, str]] = [(0, start)]
        while frontier:
            cost, node = heappop(frontier)
            if cost > distances[node]:
                continue
            for neighbor in self.aspect_relations.get(node, ()):
                step_cost = self.transition_cost(node, neighbor)
                new_cost = cost + step_cost
                if new_cost < distances.get(neighbor, float('inf')):
                    distances[neighbor] = new_cost
                    heappush(frontier, (new_cost, neighbor))
        return distances

    def transition_cost(self, source: str, target: str) -> int:
        return self.aspect_costs.get(target, 1)

    def min_cost(self, source: str, target: str) -> int:
        return self._min_costs.get(source, {}).get(target, float('inf'))

    def candidate_moves(self, aspect: str):
        return self.neighbors(aspect)

    def neighbors(self, aspect: str):
        return list(self.aspect_relations.get(aspect, []))

    def node_count(self):
        return len(self.aspect_relations)

    def all_nodes(self):
        return list(self.aspect_relations.keys())

class HexGrid:
    """
    Axial coordinates (q, r). Constructor parameter `radius` follows:
     - radius=0 -> 1 node
     - radius=1 -> 7 nodes
     - radius=2 -> 19 nodes
    Produces:
      - id_to_coord: dict id -> (q, r)
      - coord_to_id: dict (q, r) -> id
      - adj: dict id -> [neighbor_id, ...]
    """
    def __init__(self, radius: int):
        self.radius = max(0, radius - 1)
        self.id_to_coord : dict[int, (int,int)] = {}
        self.coord_to_id : dict[(int,int), int] = {}
        self.adj : dict[int, list[int]] = {}
        self._build()

    def _build(self):
        r = self.radius
        # create nodes inside axial radius
        nid = 0
        for q in range(-r, r + 1):
            r1 = max(-r, -q - r)
            r2 = min(r, -q + r)
            for s in range(r1, r2 + 1):
                coord = (q, s)  # axial (q, r)
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
                    self.adj[i].append(self.coord_to_id[ncoord])

    def _reconstruct_path(self, parents: dict[int, int | None], node: int) -> list[int]:
        path = [node]
        while parents[path[-1]] is not None:
            path.append(parents[path[-1]])
        return list(reversed(path))

    def neighbors(self, node_id: int):
        return list(self.adj.get(node_id, []))

    def node_count(self):
        return len(self.adj)

    def all_nodes(self):
        return list(self.adj.keys())

    def coord_of(self, node_id: int):
        return self.id_to_coord.get(node_id)

    def id_of(self, coord):
        return self.coord_to_id.get(coord)
    
    def remove_id(self, node_id: int):
        coord = self.id_to_coord.pop(node_id, None)
        if coord is not None:
            self.coord_to_id.pop(coord, None)
        self.adj.pop(node_id, None)
        for neighbors in self.adj.values():
            if node_id in neighbors:
                neighbors.remove(node_id)
        
    def shortest_path(self, start_id: int, goal_ids: Iterable[int]) -> list[int]:
        goals = set(goal_ids)
        if not goals:
            return []
        if start_id not in self.adj or any(goal not in self.adj for goal in goals):
            raise KeyError('Unknown node provided to HexGrid.shortest_path.')
        if start_id in goals:
            return [start_id]
        frontier = deque([start_id])
        parents: dict[int, int | None] = {start_id: None}
        while frontier:
            current = frontier.popleft()
            for neighbor in self.adj.get(current, ()):
                if neighbor in parents:
                    continue
                parents[neighbor] = current
                if neighbor in goals:
                    return self._reconstruct_path(parents, neighbor)
                frontier.append(neighbor)
        return []

    def path_with_exact_length(
        self,
        start_id: int,
        goal_id: int,
        length: int,
        blocked: Iterable[int] | None = None,
    ) -> list[int]:
        if length < 0:
            return []
        if start_id not in self.adj or goal_id not in self.adj:
            raise KeyError('Unknown node provided to HexGrid.path_with_exact_length.')
        blocked_set = set(blocked or ())
        blocked_set.discard(start_id)
        blocked_set.discard(goal_id)
        path = [start_id]
        visited = {start_id}
        result: list[int] = []

        def dfs(node: int, remaining: int) -> bool:
            if remaining == 0:
                if node == goal_id:
                    result.extend(path)
                    return True
                return False
            for neighbor in self.adj.get(node, ()):
                if neighbor in blocked_set or neighbor in visited:
                    continue
                visited.add(neighbor)
                path.append(neighbor)
                if dfs(neighbor, remaining - 1):
                    return True
                path.pop()
                visited.remove(neighbor)
            return False

        return result if dfs(start_id, length) else []


def find_aspect_path(relations: AspectRelations, start: str, goal: str) -> list[str]:
    if start not in relations.aspect_relations or goal not in relations.aspect_relations:
        raise KeyError('Unknown aspect provided to path finder.')
    if start == goal:
        return [start]
    best_costs: dict[str, int] = {start: 0}
    frontier: list[tuple[int, int, str, list[str]]] = []
    initial_h = relations.min_cost(start, goal)
    if initial_h == float('inf'):
        return []
    heappush(frontier, (initial_h, 0, start, [start]))
    while frontier:
        f_cost, g_cost, current, path = heappop(frontier)
        if current == goal:
            return path
        if g_cost > best_costs.get(current, float('inf')):
            continue
        for neighbor in relations.candidate_moves(current):
            step_cost = relations.transition_cost(current, neighbor)
            tentative = g_cost + step_cost
            if tentative >= best_costs.get(neighbor, float('inf')):
                continue
            heuristic = relations.min_cost(neighbor, goal)
            if heuristic == float('inf'):
                continue
            best_costs[neighbor] = tentative
            heappush(frontier, (tentative + heuristic, tentative, neighbor, path + [neighbor]))
    return []


def find_aspect_path_with_steps(relations: AspectRelations, start: str, goal: str, steps: int) -> list[str]:
    if start not in relations.aspect_relations or goal not in relations.aspect_relations:
        raise KeyError('Unknown aspect provided to fixed-step path finder.')
    if steps == 0:
        return [start] if start == goal else []
    best_costs: dict[tuple[str, int], int] = {(start, 0): 0}
    parents: dict[tuple[str, int], tuple[str, int]] = {}
    frontier: list[tuple[int, int, str]] = [(0, 0, start)]

    def reconstruct(state: tuple[str, int]) -> list[str]:
        aspect, _ = state
        route = [aspect]
        while state in parents:
            state = parents[state]
            route.append(state[0])
        return list(reversed(route))

    while frontier:
        cost, step, current = heappop(frontier)
        if cost > best_costs.get((current, step), float('inf')):
            continue
        if step == steps and current == goal:
            return reconstruct((current, step))
        if step == steps:
            continue
        for neighbor in relations.candidate_moves(current):
            next_step = step + 1
            new_cost = cost + relations.transition_cost(current, neighbor)
            state = (neighbor, next_step)
            if new_cost >= best_costs.get(state, float('inf')):
                continue
            best_costs[state] = new_cost
            parents[state] = (current, step)
            heappush(frontier, (new_cost, next_step, neighbor))
    return []


def aspect_path_cost(relations: AspectRelations, path: list[str]) -> int:
    return sum(relations.transition_cost(path[i - 1], path[i]) for i in range(1, len(path)))
