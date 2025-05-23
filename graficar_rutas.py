#!/usr/bin/env python3
import os
import re
import math
import matplotlib.pyplot as plt

def main():
    # Directorios relativos
    dir_inst = 'instancias'
    dir_sol = 'soluciones'
    dir_graf = 'graficos'
    os.makedirs(dir_graf, exist_ok=True)

    # Generar coordenadas: depósito en el centro, otros en círculo
    def generar_coordenadas(n):
        coords = {1: (0.0, 0.0)}
        others = list(range(2, n+1))
        m = len(others)
        for idx, node in enumerate(others):
            angle = 2 * math.pi * idx / m
            coords[node] = (math.cos(angle), math.sin(angle))
        return coords

    # Contar vértices
    def contar_vertices(dat_path):
        with open(dat_path, encoding='utf-8') as f:
            txt = f.read()
        m = re.search(r'VERTICES\s*:\s*(\d+)', txt)
        return int(m.group(1)) if m else 0

    # Leer aristas
    def leer_aristas(dat_path):
        aristas = set()
        in_req = in_nonreq = False
        with open(dat_path, encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('LISTA_ARISTAS_REQ'):
                    in_req, in_nonreq = True, False
                    continue
                if line.strip().startswith('LISTA_ARISTAS_NO_REQ'):
                    in_req, in_nonreq = False, True
                    continue
                if in_req or in_nonreq:
                    nums = re.findall(r'\d+', line)
                    if in_req and len(nums) >= 4:
                        u, v = int(nums[0]), int(nums[1])
                        aristas.add((u, v))
                    elif in_nonreq and len(nums) >= 3:
                        u, v = int(nums[0]), int(nums[1])
                        aristas.add((u, v))
        return aristas

    # Leer solución
    def leer_solucion(sol_path):
        rutas = []
        with open(sol_path, encoding='utf-8') as f:
            for line in f:
                if line.startswith('Ruta'):
                    nodos = list(map(int, re.findall(r'\d+', line.split(':')[-1])))
                    rutas.append(nodos)
        return rutas

    # Procesar cada solución
    for fname in os.listdir(dir_sol):
        if not fname.endswith('.sol'):
            continue
        inst_name = os.path.splitext(fname)[0]
        dat_path = os.path.join(dir_inst, inst_name + '.dat')
        sol_path = os.path.join(dir_sol, fname)
        out_path = os.path.join(dir_graf, inst_name + '.png')

        if not os.path.exists(dat_path):
            print(f'[Aviso] No encontrado: {dat_path}')
            continue

        n = contar_vertices(dat_path)
        coords = generar_coordenadas(n)
        edges = leer_aristas(dat_path)
        rutas = leer_solucion(sol_path)

        plt.figure(figsize=(8, 8))

        # Dibujar grafo base
        for u, v in edges:
            if u in coords and v in coords:
                x1, y1 = coords[u]; x2, y2 = coords[v]
                plt.plot([x1, x2], [y1, y2], color='lightgray', linewidth=1, zorder=1)

        cmap = plt.get_cmap('tab20')

        # Dibujar rutas con flechas y numeración grande
        for idx, ruta in enumerate(rutas):
            color = cmap(idx % 20)
            # flechas
            for i in range(len(ruta)-1):
                u, v = ruta[i], ruta[i+1]
                if u in coords and v in coords:
                    x1, y1 = coords[u]; x2, y2 = coords[v]
                    plt.annotate('', xy=(x2, y2), xytext=(x1, y1),
                                 arrowprops=dict(arrowstyle='->', color=color, lw=2),
                                 zorder=2)
            # numeración de pasos en nodos
            for step, node in enumerate(ruta, start=1):
                if node in coords:
                    x, y = coords[node]
                    plt.text(x+0.05, y+0.05, str(step), color=color,
                             fontsize=12, fontweight='bold', zorder=3)

        # Dibujar nodos y etiquetas
        for node, (x, y) in coords.items():
            if node == 1:
                plt.scatter(x, y, color='red', s=200, zorder=4)
                plt.text(x, y, '1', fontsize=14, ha='center', va='center',
                         color='white', fontweight='bold', zorder=5)
            else:
                plt.scatter(x, y, color='black', s=50, zorder=4)
                plt.text(x, y, str(node), fontsize=12, ha='center', va='center',
                         color='white', fontweight='bold', zorder=5)

        plt.title(f'Solución: {inst_name}', fontsize=16)
        plt.axis('equal')
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(out_path, dpi=150)
        plt.close()
        print(f'[OK] Gráfico guardado: {out_path}')

if __name__ == '__main__':
    main()
