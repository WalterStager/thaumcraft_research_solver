import json
from ortools.sat.python import cp_model

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

def solver_attempt():
    grid = CombinedGrid(4)
    edge_list = list(grid.edge_list)
    num_cells = len(grid.all_nodes())
    print("solver_attempt", num_cells, len(edge_list))

    model = cp_model.CpModel()
    terminals = [grid.coord_to_id[(-3,2,0)], grid.coord_to_id[(3,0,1)]]
    root = grid.coord_to_id[(-3,2,0)]

    cell_vars = {c: model.NewBoolVar(f"cell_vars_{c}") for c in grid.all_nodes()}
    edge_vars = {e: model.NewBoolVar(f"edge_vars_{e}") for e in edge_list}
    flow = {f: model.NewIntVar(0, num_cells, f"flow_{f}") for f in edge_list + [(b,a) for (a,b) in edge_list]}

    for t in terminals:
        model.Add(cell_vars[t] == 1)
    for (a,b) in edge_list:
        model.Add(edge_vars[(a,b)] <= cell_vars[a])
        model.Add(edge_vars[(a,b)] <= cell_vars[b])

    for (a,b) in edge_list + [(b,a) for (a,b) in edge_list]:
        base = edge_vars.get((min(a, b), max(a, b)))
        model.Add(flow[(a, b)] <= num_cells * base)
        
    for c in grid.all_nodes():
        inflow = sum(flow[(a, b)] for (a, b) in flow if b == c)
        outflow = sum(flow[(a, b)] for (a, b) in flow if a == c)
        if c == root:
            model.Add(inflow - outflow == len(terminals) - 1)
        elif c in terminals:
            model.Add(outflow - inflow == 1)
        else:
            model.Add(inflow == outflow)

    non_terminals = [c for c in grid.all_nodes() if c not in terminals]
    model.Minimize(sum(cell_vars[c] for c in non_terminals))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 500
    solver.parameters.num_search_workers = 16
    status = solver.Solve(model)

    print("Status:", solver.StatusName(status))
    print("Objective:", solver.ObjectiveValue())
    print("Placed cells:")
    for c in grid.all_nodes():
        if solver.Value(cell_vars[c]):
            print(" ", c)

if __name__ == "__main__":
    solver_attempt()