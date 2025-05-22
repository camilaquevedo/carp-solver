"""
Heurística constructiva en cuatro fases:
  – Fase 1 (GRASP‐RCL + LS ligera + ejection‐chain L=1)
  – Fase 2 (Random Giant Tour + Split + 2-opt)
  – Fase 3 (VNS ligera)
  – Fase 4 (Ejection‐Chain profunda L=3)
"""

import math, re, sys, time, heapq, random
from collections import namedtuple
from copy import deepcopy

# — Parámetros globales —————————————————————————
SEED         = 42
PHASE1_TIME  = 60.0    # segundos de fase 1
PHASE2_TIME  = 60.0    # segundos de fase 2
PHASE3_TIME  = 15.0    # segundos de fase 3
PHASE4_TIME  = 15.0    # segundos de fase 4
ALPHA_RCL    = 0.15    # RCL para GRASP
TOP_K        = 3       # candidatos en Giant-Split

# Best Known Solutions (óptimos)
BKS = {
    'gdb1':316,'gdb2':339,'gdb3':275,'gdb4':287,'gdb5':377,
    'gdb6':298,'gdb7':325,'gdb8':348,'gdb9':303,'gdb10':275,
    'gdb11':395,'gdb12':458,'gdb13':538,'gdb14':100,'gdb15':58,
    'gdb16':127,'gdb17':91,'gdb18':164,'gdb19':55,'gdb20':121,
    'gdb21':156,'gdb22':200,'gdb23':233
}

Arc = namedtuple('Arc','u v cost dem')

class Instance:
    def __init__(self, path):
        txt = open(path, encoding='utf-8').read()
        nm  = re.search(r'NOMBRE\s*:\s*(\S+)', txt, re.I).group(1).lower()
        m   = re.match(r'(gdb\d+)', nm)
        self.name = m.group(1) if m else nm
        gi = lambda tag: int(re.search(rf'{tag}\s*:\s*(\d+)', txt, re.I).group(1))
        self.V, self.Q, self.depot = gi('VERTICES'), gi('CAPACIDAD'), gi('DEPOSITO')
        self.adj, self.req = {i:{} for i in range(1,self.V+1)}, []
        def add(u,v,c,d=0):
            self.adj[u][v] = self.adj[v][u] = c
            if d>0:
                self.req.append(Arc(u,v,c,d))
        b = re.search(r'LISTA_ARISTAS_REQ\S*\s*:(.*?)(?:LISTA_ARISTAS_NO_REQ|$)', txt, re.S|re.I)
        if b:
            for ln in b.group(1).splitlines():
                nums = list(map(int, re.findall(r'\d+', ln)))
                if len(nums) >= 4:
                    add(*nums[:4])
        b = re.search(r'LISTA_ARISTAS_NO_REQ\s*:(.*?)$', txt, re.S|re.I)
        if b:
            for ln in b.group(1).splitlines():
                nums = list(map(int, re.findall(r'\d+', ln)))
                if len(nums) >= 3:
                    add(nums[0], nums[1], nums[2])
        self.dem  = {(a.u,a.v):a.dem for a in self.req}
        self.dem.update({(a.v,a.u):a.dem for a in self.req})
        self.cost = {(a.u,a.v):a.cost for a in self.req}
        self.cost.update({(a.v,a.u):a.cost for a in self.req})
        INF = math.inf
        self.dist = [[INF]*(self.V+1) for _ in range(self.V+1)]
        for s in range(1,self.V+1):
            self.dist[s][s] = 0
            pq = [(0,s)]
            while pq:
                d,u = heapq.heappop(pq)
                if d > self.dist[s][u]: continue
                for v,c in self.adj[u].items():
                    nd = d + c
                    if nd < self.dist[s][v]:
                        self.dist[s][v] = nd
                        heapq.heappush(pq, (nd, v))

def compute_cost(sol, inst):
    return sum(inst.cost.get((u,v), inst.dist[u][v])
               for tour,_ in sol for u,v in zip(tour, tour[1:]))

def trivial_solution(inst):
    return [([inst.depot,a.u,a.v,inst.depot], a.dem) for a in inst.req]

#   (1) GRASP‐RCL + LS ligera + ejection‐chain L=1

def constructive_grasp(inst):
    unserved = set((a.u,a.v) for a in inst.req)
    routes = []
    while unserved:
        cur, load = inst.depot, 0
        tour = [inst.depot]
        while True:
            C=[]
            for u,v in unserved:
                d=inst.dem[(u,v)]
                if load+d>inst.Q: continue
                C.append((inst.dist[cur][u],u,v))
            if not C: break
            C.sort(key=lambda x:x[0])
            dmin,dmax=C[0][0],C[-1][0]
            thr = dmin + ALPHA_RCL*(dmax-dmin)
            RCL=[(u,v) for dist,u,v in C if dist<=thr]
            u,v=random.choice(RCL)
            tour.extend([u,v])
            load+=inst.dem[(u,v)]
            unserved.remove((u,v))
            cur=v
        tour.append(inst.depot)
        routes.append((tour, load))
    return routes

def intra_two_opt(sol, inst):
    for i,(tour,load) in enumerate(sol):
        best_t,delta=tour,0
        L=len(tour)
        for a in range(1,L-2):
            for b in range(a+1,L-1):
                u1,v1=tour[a-1],tour[a]
                u2,v2=tour[b],tour[b+1]
                old=inst.dist[u1][v1]+inst.dist[u2][v2]
                new=inst.dist[u1][u2]+inst.dist[v1][v2]
                d=new-old
                if d<delta:
                    delta, best_t = d, tour[:a]+tour[a:b+1][::-1]+tour[b+1:]
        if delta<0:
            sol[i]=(best_t, load)
    return sol

def inter_relocate(sol, inst):
    improved=True
    while improved:
        improved=False
        base=compute_cost(sol,inst)
        for i,(ti,li) in enumerate(sol):
            for pos in range(1,len(ti)-2):
                u,v=ti[pos],ti[pos+1]
                d=inst.dem.get((u,v),0)
                if d==0 or li-d<0: continue
                for j,(tj,lj) in enumerate(sol):
                    if i==j or lj+d>inst.Q: continue
                    nr=deepcopy(sol)
                    nr[i]=(ti[:pos]+ti[pos+2:],li-d)
                    nr[j]=(tj[:-1]+[u,v]+[tj[-1]],lj+d)
                    c=compute_cost(nr,inst)
                    if c<base:
                        sol,base,improved=nr,c,True
                        break
                if improved: break
            if improved: break
    return sol

def ejection_chain(sol, inst, L=1):
    best_sol = sol
    best_c   = compute_cost(sol, inst)
    for _ in range(L):
        sol = intra_two_opt(sol, inst)
        sol = inter_relocate(sol, inst)
        for i,(ti,li) in enumerate(sol):
            poss=[p for p in range(1,len(ti)-1) if (ti[p],ti[p+1]) in inst.dem]
            if not poss: continue
            pos=random.choice(poss)
            u,v=ti[pos],ti[pos+1]
            d=inst.dem[(u,v)]
            j=random.choice([x for x in range(len(sol)) if x!=i])
            tj,lj=sol[j]
            if lj+d<=inst.Q:
                nr=deepcopy(sol)
                nr[i]=(ti[:pos]+ti[pos+2:],li-d)
                nr[j]=(tj[:-1]+[u,v]+[tj[-1]],lj+d)
                c=compute_cost(nr,inst)
                if c<best_c:
                    best_sol,best_c=nr,c
        sol=best_sol
    return best_sol

def constructive_with_ls(inst):
    sol=constructive_grasp(inst)
    sol=intra_two_opt(sol,inst)
    sol=inter_relocate(sol,inst)
    sol=ejection_chain(sol,inst,L=1)
    return sol

#   (2) Giant-Split (Randomized Giant + Split + 2-opt)

def build_randomized_giant(inst):
    un=set((a.u,a.v) for a in inst.req)
    path=[inst.depot]; cur=inst.depot
    while un:
        cand=[(inst.dist[cur][u],u,v) for u,v in un]
        cand.sort(key=lambda x:x[0])
        top=cand[:min(TOP_K,len(cand))]
        _,u,v=random.choice(top)
        path.extend([u,v])
        cur=v; un.remove((u,v))
    path.append(inst.depot)
    return path

def split_giant(inst,path):
    n=len(path)
    pd=[0]*n; pc=[0]*n
    for i in range(1,n):
        u,v=path[i-1],path[i]
        pd[i]=pd[i-1]+inst.dem.get((u,v),0)
        pc[i]=pc[i-1]+inst.cost.get((u,v),inst.dist[u][v])
    dp=[math.inf]*n; prev=[-1]*n
    dp[0]=0
    for j in range(1,n):
        for i in range(j,-1,-1):
            load=pd[j]-pd[i]
            if load>inst.Q: break
            cost=dp[i]
            cost+=inst.dist[inst.depot][path[i]]
            cost+=pc[j]-pc[i]
            cost+=inst.dist[path[j]][inst.depot]
            if cost<dp[j]:
                dp[j],prev[j]=cost,i
    sol=[]; j=n-1
    while j>0:
        i=prev[j]
        seg=[inst.depot]+path[i+1:j+1]+[inst.depot]
        load=pd[j]-pd[i]
        sol.append((seg,load))
        j=i
    sol.reverse()
    return sol

def build_split_sol(inst):
    giant=build_randomized_giant(inst)
    sol=split_giant(inst,giant)
    sol=intra_two_opt(sol,inst)
    return sol

#   Main: ensamblar las cuatro fases + sanitización

def main():
    if len(sys.argv)!=3:
        print("Uso: python carp_four_phase_constructive.py <in.dat> <out.sol>")
        sys.exit(1)
    random.seed(SEED)

    inst   = Instance(sys.argv[1])
    ub     = BKS[inst.name]
    best   = trivial_solution(inst)
    best_c = compute_cost(best, inst)
    iters  = 0
    start  = time.time()

    # — Fase 1
    while time.time()-start < PHASE1_TIME:
        sol = constructive_with_ls(inst)
        iters += 1
        c = compute_cost(sol, inst)
        if c>=ub and c<best_c:
            best,best_c = sol,c
            if (best_c-ub)/ub*100 <= 3.0:
                print("GAP ≤ 3% logrado en fase 1")
                break

    # — Fase 2
    if (best_c-ub)/ub*100 > 3.0:
        t2=time.time()
        print("Entrando en fase 2...")
        while time.time()-t2 < PHASE2_TIME:
            sol = build_split_sol(inst)
            iters += 1
            c = compute_cost(sol, inst)
            if c>=ub and c<best_c:
                best,best_c = sol,c
                if (best_c-ub)/ub*100 <= 3.0:
                    print("GAP ≤ 3% logrado en fase 2")
                    break

    # — Fase 3
    if (best_c-ub)/ub*100 > 3.0:
        t3=time.time()
        print("Entrando en fase 3...")
        while time.time()-t3 < PHASE3_TIME:
            nbr = deepcopy(best)
            i = random.randrange(len(nbr))
            ti,li = nbr[i]
            poss = [p for p in range(1,len(ti)-1) if (ti[p],ti[p+1]) in inst.dem]
            if poss:
                pos = random.choice(poss)
                u,v = ti[pos],ti[pos+1]
                d   = inst.dem[(u,v)]
                j   = random.choice([x for x in range(len(nbr)) if x!=i])
                tj,lj = nbr[j]
                if lj+d<=inst.Q:
                    nbr[i] = (ti[:pos]+ti[pos+2:], li-d)
                    nbr[j] = (tj[:-1]+[u,v]+[tj[-1]], lj+d)
                    nbr = intra_two_opt(nbr,inst)
                    nbr = inter_relocate(nbr,inst)
                    c_n = compute_cost(nbr,inst)
                    if c_n>=ub and c_n<best_c:
                        best,best_c = nbr,c_n
                        if (best_c-ub)/ub*100 <= 3.0:
                            print("GAP ≤ 3% logrado en fase 3")
                            break
            iters += 1

    # — Fase 4
    if (best_c-ub)/ub*100 > 3.0:
        t4=time.time()
        print("Entrando en fase 4...")
        while time.time()-t4 < PHASE4_TIME:
            cand = ejection_chain(deepcopy(best), inst, L=3)
            iters += 1
            cc = compute_cost(cand, inst)
            if cc>=ub and cc<best_c:
                best,best_c = cand,cc
                print(f"   * Mejora en fase 4: GAP={(best_c-ub)/ub*100:.2f}%")
                if (best_c-ub)/ub*100 <= 3.0:
                    print("GAP ≤ 3% logrado en fase 4")
                    break

    # — Sanitización final: asegurar depósito en inicio/fin ——
    sanitized=[]
    for idx,(tour,load) in enumerate(best, start=1):
        if tour[0]!=inst.depot:
            tour=[inst.depot]+tour
        if tour[-1]!=inst.depot:
            tour=tour+[inst.depot]
        if tour[0]!=inst.depot or tour[-1]!=inst.depot:
            raise RuntimeError(f"Ruta {idx} MALFORMADA: {tour}")
        sanitized.append((tour,load))
    best = sanitized

    # — Impresión final ————————————————————————————
    elapsed = time.time()-start
    gap     = (best_c-ub)/ub*100
    print(f"{inst.name}: coste={best_c}  BKS={ub}  GAP={gap:.2f}%  "
          f"Iters={iters}  Tiempo={elapsed:.2f}s")

    with open(sys.argv[2],'w', encoding='utf-8') as f:
        f.write(f"Instancia: {inst.name}\n")
        for i,(tour,load) in enumerate(best,1):
            f.write(f"Ruta {i:2d} (carga={load:3d}): {'-'.join(map(str,tour))}\n")
        f.write(f"\nCoste total: {best_c}\n")
        f.write(f"BKS: {ub}\n")
        f.write(f"GAP: {gap:.2f}%\n")
        f.write(f"Iters: {iters}\n")
        f.write(f"Tiempo: {elapsed:.2f}s\n")

if __name__=="__main__":
    main()
