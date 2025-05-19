#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
carp_solver.py

Heurística Path-Scanning + 2-opt para el Capacitated Arc Routing Problem.
Soporta archivos .dat en formato Bruce Golden.
"""

import re
import math
import heapq
import itertools
from collections import deque, namedtuple

# ------------------------
# ESTRUCTURAS DE DATOS
# ------------------------
Arc = namedtuple('Arc', ['u', 'v', 'cost', 'demand'])

class CARPInstance:
    def __init__(self, path):
        self.name = None
        self.num_vertices = 0
        self.num_req_arcs = 0
        self.num_nonreq_arcs = 0
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
        self.name = m.group(1)
        # Parámetros
        def get_int(tag):
            m = re.search(rf'{tag}\s*:\s*(\d+)', text)
            return int(m.group(1))
        self.num_vertices = get_int('VERTICES')
        self.num_req_arcs = get_int('ARISTAS_REQ')
        self.num_nonreq_arcs = get_int('ARISTAS_NOREQ')
        self.vehicles = get_int('VEHICULOS')
        self.capacity = get_int('CAPACIDAD')
        # Depot
        m = re.search(r'DEPOSITO\s*:\s*(\d+)', text)
        self.depot = int(m.group(1))
        # Lista de aristas requeridas
        arcs_block = re.search(r'LISTA_ARISTAS_REQ\s*:(.*?)DEPOSITO', text, re.S).group(1)
        for line in arcs_block.strip().splitlines():
            nums = list(map(int, re.findall(r'\d+', line)))
            u, v, cost, demand = nums
            self.req_arcs.append(Arc(u, v, cost, demand))
        # Construir grafo
        for i in range(1, self.num_vertices+1):
            self.adj[i] = {}
        # Agregar arcos requeridos y su inverso
        for arc in self.req_arcs:
            self.adj[arc.u][arc.v] = arc.cost
            self.adj[arc.v][arc.u] = arc.cost

    def _floyd_warshall(self):
        # Matriz de distancias inicial
        V = self.num_vertices
        dist = [[math.inf]*(V+1) for _ in range(V+1)]
        for i in range(1, V+1):
            dist[i][i] = 0
            for j, c in self.adj[i].items():
                dist[i][j] = c
        # FW
        for k in range(1, V+1):
            for i in range(1, V+1):
                for j in range(1, V+1):
                    if dist[i][j] > dist[i][k] + dist[k][j]:
                        dist[i][j] = dist[i][k] + dist[k][j]
        return dist

# ------------------------
# HEURÍSTICO CONSTRUCTIVO
# ------------------------
def path_scanning(instance: CARPInstance):
    """Genera un conjunto de rutas usando Path-Scanning."""
    unserved = set(range(len(instance.req_arcs)))
    routes = []
    while unserved:
        load = 0
        tour = [instance.depot]
        # Mientras caben arcos
        while True:
            candidates = []
            for idx in unserved:
                arc = instance.req_arcs[idx]
                if load + arc.demand <= instance.capacity:
                    # Coste desde último vértice del tour a arc.u
                    last = tour[-1]
                    cst = instance.dist[last][arc.u] + arc.cost
                    candidates.append((cst, idx))
            if not candidates:
                break
            _, chosen = min(candidates)
            arc = instance.req_arcs[chosen]
            tour += [arc.u, arc.v]
            load += arc.demand
            unserved.remove(chosen)
        tour.append(instance.depot)
        routes.append((tour, load))
    return routes

# ------------------------
# MEJORA LOCAL 2-OPT
# ------------------------
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

def improve(routes, instance):
    new_routes = []
    for tour, load in routes:
        opt = two_opt_route(tour, instance.dist)
        new_routes.append((opt, load))
    return new_routes

# ------------------------
# ESCRITURA DE SOLUCIÓN
# ------------------------
def write_solution(routes, out_path):
    with open(out_path, 'w') as f:
        total_cost = 0
        for i, (tour, _) in enumerate(routes, 1):
            cost = sum(instance.dist[tour[k]][tour[k+1]] for k in range(len(tour)-1))
            total_cost += cost
            f.write(f'RUTA {i}: {"-".join(map(str, tour))} | Costo: {cost}\n')
        f.write(f'Total rutas: {len(routes)}\n')
        f.write(f'Coste total: {total_cost}\n')

# ------------------------
# MAIN
# ------------------------
if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print("Uso: python carp_solver.py instancia.dat solucion.txt")
        sys.exit(1)
    inst_path, sol_path = sys.argv[1], sys.argv[2]
    instance = CARPInstance(inst_path)
    routes = path_scanning(instance)
    routes = improve(routes, instance)
    write_solution(routes, sol_path)
    print(f"Resuelto {instance.name}: coste total =", 
          sum(instance.dist[r[0][k]][r[0][k+1]] for r in routes for k in range(len(r[0])-1)))
