#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
carp_solver.py

Heurística Path-Scanning + 2-opt para el Capacitated Arc Routing Problem (CARP).
Soporta archivos .dat en formato Bruce Golden et al. (instancias gdb1 … gdb23).
Al final guarda:
  - Rutas encontradas
  - Coste total
  - LB (cota inferior Benavent)
  - BKS (UB, mejor solución conocida)
  - GAP vs. LB y vs. UB (%)
  - Tiempo de ejecución (s)
"""

import re
import math
import time
from collections import namedtuple

# ----------------------------------------
# DATOS DE LB / BKS según Table 2 (Golden et al. 1983, ref. [20])
# ----------------------------------------
GDB_STATS = {
    'gdb1':  {'LB': 310, 'UB': 316},
    'gdb2':  {'LB': 339, 'UB': 339},
    'gdb3':  {'LB': 275, 'UB': 275},
    'gdb4':  {'LB': 274, 'UB': 287},
    'gdb5':  {'LB': 376, 'UB': 377},
    'gdb6':  {'LB': 295, 'UB': 298},
    'gdb7':  {'LB': 312, 'UB': 325},
    'gdb8':  {'LB': 326, 'UB': 348},
    'gdb9':  {'LB': 277, 'UB': 303},
    'gdb10': {'LB': 275, 'UB': 275},
    'gdb11': {'LB': 395, 'UB': 395},
    'gdb12': {'LB': 428, 'UB': 458},
    'gdb13': {'LB': 536, 'UB': 538},
    'gdb14': {'LB': 100, 'UB': 100},
    'gdb15': {'LB': 58,  'UB': 58},
    'gdb16': {'LB': 127, 'UB': 127},
    'gdb17': {'LB': 91,  'UB': 91},
    'gdb18': {'LB': 164, 'UB': 164},
    'gdb19': {'LB': 55,  'UB': 55},
    'gdb20': {'LB': 121, 'UB': 121},
    'gdb21': {'LB': 156, 'UB': 156},
    'gdb22': {'LB': 200, 'UB': 200},
    'gdb23': {'LB': 233, 'UB': 233},
}

# ----------------------------------------
# ESTRUCTURAS DE DATOS
# ----------------------------------------
Arc = namedtuple('Arc', ['u', 'v', 'cost', 'demand'])

class CARPInstance:
    def __init__(self, path):
        self.name = None
        self.num_vertices = 0
        self.vehicles = 0
        self.capacity = 0
        self.depot = None
        self.req_arcs = []
        self.adj = {}
        self._parse_dat(path)
        self.dist = self._floyd_warshall()

    def _parse_dat(self, path):
        with open(path, 'r') as f:
            text = f.read()
        # Nombre
        m = re.search(r'NOMBRE\s*:\s*(\S+)', text)
        self.name = m.group(1).lower()
        # Parámetros
        def gi(tag):
            m = re.search(rf'{tag}\s*:\s*(\d+)', text)
            return int(m.group(1))
        self.num_vertices = gi('VERTICES')
        self.vehicles    = gi('VEHICULOS')
        self.capacity    = gi('CAPACIDAD')
        # Depósito
        m = re.search(r'DEPOSITO\s*:\s*(\d+)', text)
        self.depot = int(m.group(1))
        # Inicializa grafo vacío
        for i in range(1, self.num_vertices+1):
            self.adj[i] = {}
        # Leer aristas requeridas
        block = re.search(r'LISTA_ARISTAS_REQ\s*:(.*?)DEPOSITO', text, re.S).group(1)
        for line in block.strip().splitlines():
            nums = list(map(int, re.findall(r'\d+', line)))
            if len(nums) >= 4:
                u, v, cost, demand = nums[:4]
                self.req_arcs.append(Arc(u, v, cost, demand))
                # grafo no dirigido
                self.adj[u][v] = cost
                self.adj[v][u] = cost

    def _floyd_warshall(self):
        V = self.num_vertices
        INF = math.inf
        dist = [[INF]*(V+1) for _ in range(V+1)]
        for i in range(1, V+1):
            dist[i][i] = 0
            for j, c in self.adj[i].items():
                dist[i][j] = c
        for k in range(1, V+1):
            for i in range(1, V+1):
                for j in range(1, V+1):
                    if dist[i][j] > dist[i][k] + dist[k][j]:
                        dist[i][j] = dist[i][k] + dist[k][j]
        return dist

# ----------------------------------------
# HEURÍSTICO CONSTRUCTIVO: Path-Scanning
# ----------------------------------------
def path_scanning(inst: CARPInstance):
    unserved = set(range(len(inst.req_arcs)))
    routes = []
    while unserved:
        load = 0
        tour = [inst.depot]
        while True:
            cands = []
            last = tour[-1]
            for idx in unserved:
                arc = inst.req_arcs[idx]
                if load + arc.demand <= inst.capacity:
                    cost_to_u = inst.dist[last][arc.u] + arc.cost
                    cands.append((cost_to_u, idx))
            if not cands:
                break
            _, chosen = min(cands)
            arc = inst.req_arcs[chosen]
            tour.extend([arc.u, arc.v])
            load += arc.demand
            unserved.remove(chosen)
        tour.append(inst.depot)
        routes.append((tour, load))
    return routes

# ----------------------------------------
# MEJORA LOCAL: 2-opt sobre cada ruta
# ----------------------------------------
def two_opt_route(route, dist):
    best = route
    improved = True
    while improved:
        improved = False
        for i in range(1, len(best)-2):
            for j in range(i+1, len(best)-1):
                if dist[best[i-1]][best[j]] + dist[best[i]][best[j+1]] \
                   < dist[best[i-1]][best[i]] + dist[best[j]][best[j+1]]:
                    best = best[:i] + best[i:j+1][::-1] + best[j+1:]
                    improved = True
        route = best
    return best

def improve(routes, inst):
    return [(two_opt_route(tour, inst.dist), load) for tour, load in routes]

# ----------------------------------------
# ESCRITURA DE LA SOLUCIÓN (solo GAP vs. UB)
# ----------------------------------------
def write_solution(inst, routes, sol_path, t_elapsed):
    cost_total = 0
    with open(sol_path, 'w') as f:
        f.write(f"Instancia: {inst.name}\n\n")
        f.write("Rutas encontradas:\n")
        for i, (tour, _) in enumerate(routes, 1):
            f.write(f"  Ruta {i}: {'-'.join(map(str, tour))}\n")
            for k in range(len(tour)-1):
                cost_total += inst.dist[tour[k]][tour[k+1]]
        f.write(f"\nCoste total: {cost_total}\n")

        stats = GDB_STATS.get(inst.name)
        if stats:
            ub = stats['UB']
            gap_ub = (cost_total - ub) / ub * 100
            f.write(f"BKS (UB):       {ub}\n")
            f.write(f"GAP vs. UB:     {gap_ub:.2f}%\n")
        else:
            f.write("BKS (UB):       N/D\n")
            f.write("GAP vs. UB:     N/A\n")

        f.write(f"Tiempo de ejecución: {t_elapsed:.3f} s\n")

    # Impresión por pantalla
    if stats:
        print(f"Resuelto {inst.name}: coste={cost_total}, GAP_vs_UB={gap_ub:.2f}%, tiempo={t_elapsed:.3f}s")
    else:
        print(f"Resuelto {inst.name}: coste={cost_total}, GAP_vs_UB=N/A, tiempo={t_elapsed:.3f}s")


# ----------------------------------------
# PUNTO DE ENTRADA
# ----------------------------------------
if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print("Uso: python carp_solver.py instancia.dat solucion.txt")
        sys.exit(1)

    inst_path, sol_path = sys.argv[1], sys.argv[2]
    instance = CARPInstance(inst_path)

    t0 = time.time()
    routes = path_scanning(instance)
    routes = improve(routes, instance)
    t1 = time.time()

    write_solution(instance, routes, sol_path, t1 - t0)
