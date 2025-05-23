# CARP Solver – Heurística Path-Scanning + 2-opt

## Requisitos
- Python 3.9 o superior  
- Sólo librerías estándar de Python 

---

## 1. Clonar el repositorio y abrir la carpeta
```bash
git clone https://github.com/camilaquevedo/carp-solver.git
cd carp-solver
```

---

## 2. Estructura del proyecto
```
carp-solver/
├─ instancias/         23 archivos *.dat (Instancias de Golden)
├─ soluciones/         aquí se guardan los *.sol con la solución de cada instancia
├─ graficos/           aquí se guardan los *.png con la visualización de cada solución
├─ carp_solver.py      heurística constructiva en 4 fases
├─ graficar_rutas.py   script que grafica la visualización de las soluciones
└─ README.md
```

---

## 3. Uso

### 3.1 Ejecutar una sola instancia
```bash
python carp_solver.py instancias/gdb1.dat soluciones/gdb1.sol
```

### 3.2 Ejecutar **todas** las instancias a la vez

**PowerShell (Windows)**
```powershell
Get-ChildItem .\instancias\*.dat | ForEach-Object {
  python carp_solver.py $_.FullName ".\soluciones\$($_.BaseName).sol"
}
```

**bash / Linux / macOS**
```bash
for f in instancias/*.dat; do
  python carp_solver.py "$f" "soluciones/$(basename "$f" .dat).sol"
done
```
Al finalizar, la carpeta **soluciones/** contendrá 23 archivos `.sol`, uno por instancia.

---

## 4. Cómo funciona la heurística

| Fase | Tiempo por defecto | Descripción |
|------|--------------------|-------------|
| **1** | 60 s | GRASP (α = 0.15) + 2-opt intra-ruta + relocate inter-ruta + ejection-chain ligera |
| **2** | 60 s | Giant-tour aleatorio → Split → 2-opt |
| **3** | 15 s | VNS ligera sobre la mejor solución |
| **4** | 15 s | Ejection-Chain profundidad 3 |

La búsqueda se detiene antes si alcanza **GAP ≤ 3 %** respecto al BKS.

---

## 5. Interpretar los resultados

Ejemplo de archivo `gdb1.sol`:
```
Instancia: gdb1
Ruta  1 (carga= 5): 1-2-3-1
Ruta  2 (carga= 4): 1-4-7-1
…
Coste total: 317
BKS: 316
GAP: 0.32%
Iters: 124
Tiempo: 58.42s
```
- **Ruta X** → secuencia de vértices (empieza y termina en el depósito) y carga.  
- **Coste total** → distancia recorrida (arcos servidos + desplazamientos vacíos).  
- **BKS** → mejor solución conocida para la instancia.  
- **GAP** → `(Coste − BKS) / BKS × 100 %`.  
- **Iters / Tiempo** → iteraciones totales y segundos de ejecución.

---

## 6. Parámetros editables
En la cabecera de `carp_solver.py`:
```python
PHASE1_TIME = 60.0   # seg. GRASP + LS
PHASE2_TIME = 60.0   # seg. Giant-Split
ALPHA_RCL   = 0.15   # tamaño de la RCL en GRASP
GAP_TARGET  = 3.0    # umbral GAP (%) para parar
```

## 7. Visualización

```bash
python graficar_rutas.py
```
Al finalizar, la carpeta **graficos/** contendrá 23 archivos `.png`, uno por solución de instancia.
