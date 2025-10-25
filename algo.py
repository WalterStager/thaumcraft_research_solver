from pulp import *
from ortools.sat.python import cp_model

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
        self.edge_list : set[(int,int)] = set()
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
        for id, coord in self.id_to_coord.items():
            q, r = coord
            for dq, dr in dirs:
                ncoord = (q + dq, r + dr)
                if ncoord in self.coord_to_id:
                    nid = self.coord_to_id[ncoord]
                    self.adj[id].append(nid)
                    if (not (nid, id) in self.edge_list):
                        self.edge_list.add((id, nid))

    def neighbors(self, node_id: int):
        return list(self.adj.get(node_id, []))

    def node_count(self):
        return len(self.adj)

    def all_nodes(self):
        return list(self.adj.keys())

class CombinedGrid:
    def __init__(self, radius: int):
        self.radius = max(0, radius - 1)
        # graph lookups that use id <=> (q, r, a)
        self.id_to_coord : dict[int, (int,int,int)] = {}
        self.coord_to_id : dict[(int,int,int), int] = {}
        self.edge_list : set[(int,int)] = set()
        self.adj : dict[int, set[int]] = {}

        # aspect specific lookups that use aid/'a'/aspect id <=> str
        self.aspect_to_aid : dict[str, int] = {}
        self.aid_to_aspect : dict[int, str] = {}
        self.aspect_adj : dict[int, set[int]] = {}
        self._build()

    def _build(self):
        with open('aspects.json') as aspects_file:
            data : dict = json.load(aspects_file)

        # let all aspects be assigned ids
        for aid, (aspect, components) in enumerate(data.items()):
            self.aspect_to_aid[aspect] = aid
            self.aid_to_aspect[aid] = aspect
        
        # construct aspect adjacency lists
        for aspect, components in data.items():
            a1 = self.aspect_to_aid[aspect]
            components = list(components or [])
            for component in components:
                a2 = self.aspect_to_aid[component]
                self.aspect_adj.setdefault(a1, set()).add(a2)
                self.aspect_adj.setdefault(a2, set()).add(a1)

        # let all nodes be assigned ids
        rad = self.radius
        nid = 0
        for q in range(-rad, rad + 1):
            s1 = max(-rad, -q - rad)
            s2 = min(rad, -q + rad)
            for r in range(s1, s2 + 1):
                for a in self.aid_to_aspect.keys():
                    coord = (q, r, a)
                    self.id_to_coord[nid] = coord
                    self.coord_to_id[coord] = nid
                    nid += 1

        # axial neighbor directions
        dirs = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]
        # construct node adjacency lists
        for id, (q, r, a) in self.id_to_coord.items():
            for dq, dr in dirs:
                for da in self.aspect_adj[a]:
                    ncoord = (q + dq, r + dr, da)
                    if (ncoord in self.coord_to_id):
                        nid = self.coord_to_id[ncoord]
                        self.adj.setdefault(id, set()).add(nid)
                        self.adj.setdefault(nid, set()).add(id)
                        if (not (nid, id) in self.edge_list):
                            self.edge_list.add((id, nid))

    def neighbors(self, node_id: int):
        return list(self.adj.get(node_id, []))

    def node_count(self):
        return len(self.adj)

    def all_nodes(self):
        return list(self.adj.keys())
    
def pulp_solution1():
    grid = CombinedGrid(4)
    edge_list = list(grid.edge_list)
    print("pulp_solution1", len(grid.all_nodes()), len(edge_list))

    prob = LpProblem("HexSteinerBoard", LpMinimize)
    terminals = [grid.coord_to_id[(-3,2,0)], grid.coord_to_id[(3,0,1)]]
    root = grid.coord_to_id[(-3,2,0)]

    cell_vars = LpVariable.dicts("cell_vars", grid.all_nodes(), 0, 1, cat="Binary")
    edge_vars = LpVariable.dicts("edge_vars", edge_list, 0, 1, cat="Binary")
    flow = LpVariable.dicts("flow", edge_list + [(b,a) for (a,b) in edge_list], 0, cat="Integer")

    for t in terminals:
        prob += cell_vars[t] == 1
    for (a,b) in edge_list:
        prob += edge_vars[(a,b)] <= cell_vars[a]
        prob += edge_vars[(a,b)] <= cell_vars[b]

    num_cells = len(grid.all_nodes())
    for (a,b) in edge_list + [(b,a) for (a,b) in edge_list]:
        prob += flow[(a,b)] <= (num_cells * edge_vars.get((a,b), edge_vars.get((b,a))))
        
    for c in grid.all_nodes():
        inflow = sum(flow[(a,b)] for (a,b) in flow if b == c)
        outflow = sum(flow[(a,b)] for (a,b) in flow if a == c)
        if c == root:
            # Root supplies total flow = number of other placed nodes
            prob += outflow - inflow == (sum(cell_vars[k] for k in grid.all_nodes()) - 1)
        else:
            prob += inflow - outflow == cell_vars[c]
    non_terminals = [c for c in grid.all_nodes() if c not in terminals]
    prob += lpSum(cell_vars[c] for c in non_terminals)
    prob.solve()

def pulp_solution2():
    # aspect specific lookups that use aid/'a'/aspect id <=> str
    aspect_to_aid : dict[str, int] = {}
    aid_to_aspect : dict[int, str] = {}
    aspect_adj : dict[int, set[int]] = {}

    with open('aspects.json') as aspects_file:
        data : dict = json.load(aspects_file)

    # let all aspects be assigned ids
    for aid, (aspect, components) in enumerate(data.items()):
        aspect_to_aid[aspect] = aid
        aid_to_aspect[aid] = aspect
    
    # construct aspect adjacency lists
    for aspect, components in data.items():
        a1 = aspect_to_aid[aspect]
        components = list(components or [])
        for component in components:
            a2 = aspect_to_aid[component]
            aspect_adj.setdefault(a1, set()).add(a2)
            aspect_adj.setdefault(a2, set()).add(a1)
    
    hex_grid = HexGrid(4)

    cell_list = set()
    for node in hex_grid.all_nodes():
        for aid in aid_to_aspect.keys():
            cell_list.add((node, aid))
    cell_list = list(cell_list)

    edge_list = set()
    for (n1, n2) in hex_grid.edge_list:
        for aid in aid_to_aspect.keys():
            for caid in aspect_adj[aid]:
                edge_list.add(((n1, aid), (n2, caid)))
                # edge_list.add(((n1, caid), (n2, aid)))
    edge_list = list(edge_list)
    
    print("pulp_solution2", len(cell_list), len(edge_list))

    prob = LpProblem("HexSteinerBoard", LpMinimize)
    terminals = [(hex_grid.coord_to_id[(-3,2,)],0), (hex_grid.coord_to_id[(3,0)],1)]
    root = terminals[0]
    cell_vars = LpVariable.dicts("cell_vars", cell_list, 0, 1, cat="Binary")
    edge_vars = LpVariable.dicts("edge_vars", edge_list, 0, 1, cat="Binary")
    flow = LpVariable.dicts("flow", edge_list + [(b,a) for (a,b) in edge_list], 0, cat="Integer")
    for t in terminals:
        prob += cell_vars[t] == 1
    for (a,b) in edge_list:
        prob += edge_vars[(a,b)] <= cell_vars[a]
        prob += edge_vars[(a,b)] <= cell_vars[b]
    num_cells = len(cell_list)
    for (a,b) in edge_list + [(b,a) for (a,b) in edge_list]:
        prob += flow[(a,b)] <= (num_cells * edge_vars.get((a,b), edge_vars.get((b,a))))
    for c in cell_list:
        inflow = sum(flow[(a,b)] for (a,b) in flow if b == c)
        outflow = sum(flow[(a,b)] for (a,b) in flow if a == c)
        if c == root:
            # Root supplies total flow = number of other placed nodes
            prob += outflow - inflow == (sum(cell_vars[k] for k in cell_list) - 1)
        else:
            prob += inflow - outflow == cell_vars[c]
    non_terminals = [c for c in cell_list if c not in terminals]
    prob += lpSum(cell_vars[c] for c in non_terminals)
    prob.solve()

    print("Status:", LpStatus[prob.status])
    print("Objective (extra pieces):", value(prob.objective))
    print("Placed cells:")
    for c in cell_list:
        if value(cell_vars[c]) == 1:
            print(" ", hex_grid.id_to_coord[c])

def pulp_solution3():
    grid = CombinedGrid(4)
    edge_list = list(grid.edge_list)
    print("pulp_solution3", len(grid.all_nodes()), len(edge_list))

    model = cp_model.CpModel()
    terminals = [grid.coord_to_id[(-3,2,0)], grid.coord_to_id[(3,0,1)]]
    root = grid.coord_to_id[(-3,2,0)]

    cell_vars = {c: model.NewBoolVar(f"cell_vars_{c}") for c in grid.all_nodes()}
    edge_vars = {e: model.NewBoolVar(f"edge_vars_{e}") for e in edge_list}
    flow = {f: model.NewBoolVar(f"flow_{f}") for f in edge_list + [(b,a) for (a,b) in edge_list]}

    for t in terminals:
        model.Add(cell_vars[t] == 1)
    for (a,b) in edge_list:
        model.Add(edge_vars[(a,b)] <= cell_vars[a])
        model.Add(edge_vars[(a,b)] <= cell_vars[b])

    num_cells = len(grid.all_nodes())
    for (a,b) in edge_list + [(b,a) for (a,b) in edge_list]:
        model.Add(flow[(a,b)] <= (num_cells * edge_vars.get((a,b), edge_vars.get((b,a)))))
        
    for c in grid.all_nodes():
        inflow = sum(flow[(a,b)] for (a,b) in flow if b == c)
        outflow = sum(flow[(a,b)] for (a,b) in flow if a == c)
        if c == root:
            # Root supplies total flow = number of other placed nodes
            model.Add(outflow - inflow == (sum(cell_vars[k] for k in grid.all_nodes()) - 1))
        else:
            model.Add(inflow - outflow == cell_vars[c])
    non_terminals = [c for c in grid.all_nodes() if c not in terminals]
    model.Minimize(sum(cell_vars[c] for c in non_terminals))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 500  # limit for safety
    solver.parameters.num_search_workers = 8     # multi-core
    status = solver.Solve(model)
    # --- Output ---
    print("Status:", solver.StatusName(status))
    print("Objective:", solver.ObjectiveValue())
    print("Placed cells:")
    for c in grid.all_nodes():
        if solver.Value(cell_vars[c]):
            print(" ", c)

def pulp_hex_test():
    hex_grid = HexGrid(4)
    edge_list = list(hex_grid.edge_list)

    prob = LpProblem("HexSteinerBoard", LpMinimize)
    terminals = [hex_grid.coord_to_id[(-3,2)], hex_grid.coord_to_id[(3,0)]]
    root = hex_grid.coord_to_id[(-3,2)]
    cell_vars = LpVariable.dicts("cell_vars", hex_grid.all_nodes(), 0, 1, cat="Binary")
    edge_vars = LpVariable.dicts("edge_vars", edge_list, 0, 1, cat="Binary")
    flow = LpVariable.dicts("flow", edge_list + [(b,a) for (a,b) in edge_list], 0, cat="Integer")
    for t in terminals:
        prob += cell_vars[t] == 1
    for (a,b) in edge_list:
        prob += edge_vars[(a,b)] <= cell_vars[a]
        prob += edge_vars[(a,b)] <= cell_vars[b]
    num_cells = len(hex_grid.all_nodes())
    for (a,b) in edge_list + [(b,a) for (a,b) in edge_list]:
        prob += flow[(a,b)] <= (num_cells * edge_vars.get((a,b), edge_vars.get((b,a))))
    for c in hex_grid.all_nodes():
        inflow = sum(flow[(a,b)] for (a,b) in flow if b == c)
        outflow = sum(flow[(a,b)] for (a,b) in flow if a == c)
        if c == root:
            # Root supplies total flow = number of other placed nodes
            prob += outflow - inflow == (sum(cell_vars[k] for k in hex_grid.all_nodes()) - 1)
        else:
            prob += inflow - outflow == cell_vars[c]
    non_terminals = [c for c in hex_grid.all_nodes() if c not in terminals]
    prob += lpSum(cell_vars[c] for c in non_terminals)
    prob.solve()

    print("Status:", LpStatus[prob.status])
    print("Objective (extra pieces):", value(prob.objective))
    print("Placed cells:")
    for c in hex_grid.all_nodes():
        if value(cell_vars[c]) == 1:
            print(" ", hex_grid.id_to_coord[c])

def pulp_test():
    cells = [(0,0), (0,1), (1,0), (1,1)]
    adj = [
        ((0,0),(0,1)), ((0,0),(1,0)),
        ((0,1),(1,1)), ((1,0),(1,1))
    ]

    terminals = [(0,0), (1,1)]
    root = (0,0)

    prob = LpProblem("SteinerBoard", LpMinimize)

    # 1 = cell placed
    cell_vars = LpVariable.dicts("cell_vars", cells, 0, 1, cat="Binary")
    # 1 = edge placed
    edge_vars = LpVariable.dicts("edge_vars", adj, 0, 1, cat="Binary")

    flow = LpVariable.dicts("flow", adj + [(b,a) for (a,b) in adj], 0, cat="Integer")

    # Force terminals placed
    for t in terminals:
        prob += cell_vars[t] == 1

    # edge (a,b) placed iff a & b placed
    for (a,b) in adj:
        prob += edge_vars[(a,b)] <= cell_vars[a]
        prob += edge_vars[(a,b)] <= cell_vars[b]

    # --- Connectivity via flow from root ---
    # Capacity: flow can only go through placed edges
    num_cells = len(cells)
    # flow (a,b) == 0 if (a,b) not placed
    for (a,b) in adj + [(b,a) for (a,b) in adj]:
        prob += flow[(a,b)] <= (num_cells * edge_vars.get((a,b), edge_vars.get((b,a))))

    # Flow conservation: root sends out (num_selected - 1) units; others receive 1 if selected
    for c in cells:
        inflow = sum(flow[(a,b)] for (a,b) in flow if b == c)
        outflow = sum(flow[(a,b)] for (a,b) in flow if a == c)
        if c == root:
            # Root supplies total flow = number of other placed nodes
            prob += outflow - inflow == (sum(cell_vars[k] for k in cells) - 1)
        else:
            prob += inflow - outflow == cell_vars[c]

    # --- Objective: minimize number of placed (non-terminal) pieces ---
    non_terminals = [c for c in cells if c not in terminals]
    prob += lpSum(cell_vars[c] for c in non_terminals)

    prob.solve()

    print("Status:", LpStatus[prob.status])
    print("Objective (extra pieces):", value(prob.objective))
    print("Placed cells:")
    for c in cells:
        if value(cell_vars[c]) > 0.5:
            print(" ", c)

if __name__ == "__main__":
    pulp_solution3()