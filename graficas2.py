#!/usr/bin/env python3
# =============================================================================
#  graficas.py - Genera las graficas y tablas del informe del Taller MPI.
#
#  Va en la carpeta principal del proyecto (MPI-taller/) y lee:
#     Experimento-1/Soluciones/mxmMPI_<alg>-N-<N>-W-<W>.txt      (clúster)
#     Experimento-2/resultados_local.csv                          (local)
#     Experimento-3/resultados_overhead/overhead_resumen.csv      (overhead)
#     velocidad_nodos.txt                     (opcional, análisis 2.5)
#
#  USO:   python3 graficas.py
#  Crea:  graficas/<análisis>/   con las gráficas (.png) y las tablas (.png y .csv)
#  Requiere: matplotlib y numpy
# =============================================================================
import csv, glob, os, re, statistics as st, sys
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator

RAIZ = os.path.dirname(os.path.abspath(__file__))
SAL = os.path.join(RAIZ, "graficas2")

# ----------------------------------------------------------------- estilo
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
    "font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10,
    "axes.edgecolor": "#c3c2b7", "axes.linewidth": 0.8,
    "axes.grid": True, "grid.color": "#e1e0d9", "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False,
    "xtick.color": "#52514e", "ytick.color": "#52514e",
    "axes.labelcolor": "#0b0b0b", "text.color": "#0b0b0b",
    "legend.frameon": False, "savefig.dpi": 300,
})
C_ALG = {"FxC": "#eb6834", "FxT": "#2a78d6"}                          # naranja / azul
C_W = {1: "#86b6ef", 2: "#2a78d6", 3: "#104281"}                       # workers: azul claro a oscuro
C_ESC = {"local": "#1baf7a", "cluster": "#6250d6"}                     # aguamarina / violeta
C_ESC_W = {"local": {1: "#8fdcbd", 2: "#1baf7a", 3: "#0b6e4b"},
           "cluster": {1: "#b3abf2", 2: "#6250d6", 3: "#33278c"}}
NOM_ESC = {"local": "Local", "cluster": "Clúster"}
GRIS = "#898781"; TINTA2 = "#52514e"; FONDO = "#f0efec"
NS = [192, 384, 768, 1536, 2304, 3072]; WS = [1, 2, 3]; ALGS = ["FxC", "FxT"]

def coma(x, d=2):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def seg(v):            # formato de segundos legible
    return coma(v, 3) if v < 1 else coma(v, 2) if v < 10 else coma(v, 1)

def carpeta(nombre):
    d = os.path.join(SAL, nombre); os.makedirs(d, exist_ok=True); return d

def guardar(fig, d, nombre):
    fig.savefig(os.path.join(d, nombre + ".png"), bbox_inches="tight", facecolor="white")
    plt.close(fig); print(f"  {os.path.relpath(os.path.join(d, nombre + '.png'), RAIZ)}")

def tabla(d, nombre, titulo, enc, filas, anchos=None):
    """Guarda la tabla como CSV (Excel en español) y como imagen para pegar en Word."""
    with open(os.path.join(d, nombre + ".csv"), "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";"); w.writerow(enc); w.writerows(filas)
    n = len(filas)
    fig, ax = plt.subplots(figsize=(min(1.15 * len(enc) + 0.6, 9.5), 0.36 * (n + 1) + 0.55))
    ax.axis("off")
    t = ax.table(cellText=filas, colLabels=enc, loc="center", cellLoc="center", colWidths=anchos)
    t.auto_set_font_size(False); t.set_fontsize(9); t.scale(1, 1.35)
    for (r, c), cel in t.get_celld().items():
        cel.set_edgecolor("#c3c2b7"); cel.set_linewidth(0.6)
        if r == 0:
            cel.set_facecolor("#1F4E79"); cel.get_text().set_color("white"); cel.get_text().set_weight("bold")
        elif r % 2 == 0:
            cel.set_facecolor("#f4f6fa")
    ax.set_title(titulo, fontsize=10, pad=4)
    guardar(fig, d, nombre)

def eje_tiempo_log(ax):
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: coma(v, 2) if v < 1 else coma(v, 0)))
    ax.minorticks_off()

def eje_N(ax):
    ax.set_xticks(range(len(NS))); ax.set_xticklabels(NS); ax.set_xlabel("Tamaño de la matriz N (N × N)")

X = list(range(len(NS)))

# ----------------------------------------------------------------- lectura
def leer_exp1():
    d = {}
    for f in glob.glob(os.path.join(RAIZ, "Experimento-1", "Soluciones", "mxmMPI_*-N-*-W-*.txt")):
        m = re.search(r"mxmMPI_(FxC|FxT)-N-(\d+)-W-(\d+)\.txt$", f)
        if not m: continue
        v = [int(p[1]) / 1e6 for p in (l.split() for l in open(f, encoding="utf-8").read().splitlines()[1:])
             if len(p) == 3 and p[1].isdigit()]
        if v: d[(m.group(1), int(m.group(2)), int(m.group(3)))] = v
    return d

def leer_local():
    d = defaultdict(list); ruta = os.path.join(RAIZ, "Experimento-2", "resultados_local.csv")
    if not os.path.exists(ruta): return {}
    for r in csv.DictReader(open(ruta, encoding="utf-8"), delimiter=";"):
        try: d[(r["algoritmo"], int(r["N"]), int(r["workers"]))].append(int(r["tiempo_us"]) / 1e6)
        except (ValueError, KeyError): pass
    return dict(d)

def leer_ovh():
    d = {}; ruta = os.path.join(RAIZ, "Experimento-3", "resultados_overhead", "overhead_resumen.csv")
    if not os.path.exists(ruta): return {}
    for r in csv.DictReader(open(ruta, encoding="utf-8")):
        d[(r["algoritmo"], int(r["N"]), int(r["workers"]))] = {
            "T": float(r["T_total_media_s"]), "comp": float(r["T_comp_media_s"]),
            "ovh": float(r["overhead_media_s"]), "pct": float(r["overhead_pct_media"])}
    return d

E1, LOC, OVH = leer_exp1(), leer_local(), leer_ovh()
if not E1: sys.exit("No encontré resultados en Experimento-1/Soluciones (¿el script está en la carpeta principal?)")
T = lambda A, N, W: st.mean(E1[(A, N, W)])                       # tiempo medio clúster (exp. 1)
TL = lambda A, N, W: st.mean(LOC[(A, N, W)])                     # tiempo medio local (exp. 2)
CV = lambda D, k: 100 * st.stdev(D[k]) / st.mean(D[k])
print(f"Datos: Exp.1 {len(E1)} combinaciones | Exp.2 local {len(LOC)} | Exp.3 {len(OVH)}\nGenerando en graficas/:")

# ============================================================ EXPERIMENTO 1
# ---- 1.1 FxC vs FxT
d = carpeta("1.1_FxC_vs_FxT")
for A in ALGS:                                                   # tiempos de cada algoritmo por workers
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    for W in WS:
        ax.plot(X, [T(A, N, W) for N in NS], color=C_W[W], lw=2, marker="o", ms=5,
                label=f"{W} worker" + ("s" if W > 1 else ""))
    eje_tiempo_log(ax); eje_N(ax); ax.set_ylabel("Tiempo medio (s, escala logarítmica)")
    ax.set_title(f"Tiempo de {A} según el tamaño de la matriz"); ax.legend()
    guardar(fig, d, f"tiempos_{A}")
fig, axs = plt.subplots(1, 3, figsize=(9, 3.4), sharey=True)    # FxC frente a FxT, un panel por workers
for ax, W in zip(axs, WS):
    for A in ALGS:
        ax.plot(X, [T(A, N, W) for N in NS], color=C_ALG[A], lw=2, marker="o", ms=4, label=A)
    eje_tiempo_log(ax); ax.set_xticks(X); ax.set_xticklabels(NS, fontsize=8); ax.set_xlabel("N")
    ax.set_title(f"{W} worker" + ("s" if W > 1 else ""))
axs[0].set_ylabel("Tiempo medio (s, escala log)"); axs[0].legend()
fig.suptitle("FxC frente a FxT: tiempo según el tamaño de la matriz", y=1.03)
guardar(fig, d, "FxC_vs_FxT_tiempos")
tabla(d, "tabla_FxC_vs_FxT", "Tiempo medio (s) y cuántas veces más rápido es FxT que FxC",
      ["N", "W", "FxC (s)", "FxT (s)", "FxT es ... veces más rápido"],
      [[N, W, seg(T("FxC", N, W)), seg(T("FxT", N, W)), coma(T("FxC", N, W) / T("FxT", N, W), 1) + "×"]
       for N in NS for W in WS])

# ---- 1.2 Mejora al agregar workers y eficiencia (tiempo real vs esperado)
d = carpeta("1.2_mejora_y_eficiencia")
for A in ALGS:
    filas = []
    for N in NS:
        t1, t2, t3 = T(A, N, 1), T(A, N, 2), T(A, N, 3)
        filas.append([N, seg(t1), seg(t2), seg(t1 / 2), coma(100 * t1 / (2 * t2), 1) + " %",
                      seg(t3), seg(t1 / 3), coma(100 * t1 / (3 * t3), 1) + " %"])
    tabla(d, f"tabla_mejora_{A}", f"{A}: tiempo real frente al esperado (mitad con 2 workers, un tercio con 3)",
          ["N", "1 worker (s)", "2 workers real (s)", "2 workers esperado (s)", "Eficiencia 2W",
           "3 workers real (s)", "3 workers esperado (s)", "Eficiencia 3W"], filas)
    fig, ax = plt.subplots(figsize=(6.5, 3.6))                   # real (línea) vs esperado (punteada)
    for N in (384, 1536, 3072):
        c = {384: "#86b6ef", 1536: "#2a78d6", 3072: "#104281"}[N]
        ax.plot(WS, [T(A, N, W) for W in WS], color=c, lw=2, marker="o", ms=5, label=f"N = {N}, real")
        ax.plot(WS, [T(A, N, 1) / W for W in WS], color=c, lw=1.2, ls="--", label=f"N = {N}, esperado")
    eje_tiempo_log(ax); ax.set_xticks(WS); ax.set_xlabel("Número de workers")
    ax.set_ylabel("Tiempo medio (s, escala log)"); ax.set_title(f"{A}: tiempo real frente al esperado (T₁ ÷ W)")
    ax.legend(fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    guardar(fig, d, f"real_vs_esperado_{A}")

# ---- 1.3 Ganancia marginal: aceleración según N
d = carpeta("1.3_ganancia_marginal")
for A in ALGS:
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    for W in (2, 3):
        ax.axhline(W, color=C_W[W], lw=1, ls="--")
        ax.text(5.15, W, f"ideal {W}×", color=C_W[W], fontsize=8, va="center")
        ax.plot(X, [T(A, N, 1) / T(A, N, W) for N in NS], color=C_W[W], lw=2, marker="o", ms=5,
                label=f"{W} workers")
    eje_N(ax); ax.set_ylim(0.8, 3.3); ax.yaxis.set_major_locator(MultipleLocator(0.5))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: coma(v, 1) + "×"))
    ax.set_ylabel("Veces más rápido que con 1 worker"); ax.set_xlim(-0.3, 5.8)
    ax.set_title(f"{A}: cuánto acelera cada worker adicional"); ax.legend(loc="lower right")
    guardar(fig, d, f"aceleracion_{A}")
tabla(d, "tabla_ganancia_marginal", "Aceleración real y % de lo ideal que aporta cada worker",
      ["Algoritmo", "N", "1 → 2 workers", "% del ideal (2×)", "2 → 3 workers", "% del ideal (1,5×)"],
      [[A, N, coma(T(A, N, 1) / T(A, N, 2), 2) + "×", coma(50 * T(A, N, 1) / T(A, N, 2), 1) + " %",
        coma(T(A, N, 2) / T(A, N, 3), 2) + "×", coma(100 * T(A, N, 2) / (1.5 * T(A, N, 3)), 1) + " %"]
       for A in ALGS for N in NS])

# ---- 1.4 Desde qué tamaño distribuir
d = carpeta("1.4_desde_que_tamano")
for A in ALGS:
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    ax.axhline(85, color=GRIS, ls="--", lw=1); ax.text(-0.25, 87, "85 % (umbral)", color=GRIS, fontsize=8)
    ax.axvspan(1.5, 5.5, color=FONDO, zorder=0)
    ax.text(3.5, 12, "vale la pena distribuir", ha="center", color=TINTA2, fontsize=9)
    for W in (2, 3):
        ax.plot(X, [100 * T(A, N, 1) / (W * T(A, N, W)) for N in NS], color=C_W[W], lw=2, marker="o", ms=5,
                label=f"{W} workers")
    eje_N(ax); ax.set_ylim(0, 112); ax.set_ylabel("Eficiencia (% de la mejora ideal)")
    ax.set_title(f"{A}: eficiencia al distribuir según el tamaño"); ax.legend(loc="lower right")
    guardar(fig, d, f"eficiencia_{A}")

# ============================================================ EXPERIMENTO 2
if LOC:
    # ---- 2.1 Local vs clúster según el algoritmo (tiempos)
    d = carpeta("2.1_local_vs_cluster")
    for A in ALGS:
        fig, axs = plt.subplots(1, 3, figsize=(9, 3.4), sharey=True)
        for ax, W in zip(axs, WS):
            for esc, f in (("local", TL), ("cluster", T)):
                ax.plot(X, [f(A, N, W) for N in NS], color=C_ESC[esc], lw=2, marker="o", ms=4, label=NOM_ESC[esc])
            eje_tiempo_log(ax); ax.set_xticks(X); ax.set_xticklabels(NS, fontsize=8); ax.set_xlabel("N")
            ax.set_title(f"{W} worker" + ("s" if W > 1 else ""))
        axs[0].set_ylabel("Tiempo medio (s, escala log)"); axs[0].legend()
        fig.suptitle(f"{A}: tiempo en local frente a clúster", y=1.03)
        guardar(fig, d, f"tiempos_local_vs_cluster_{A}")
    tabla(d, "tabla_local_vs_cluster", "Tiempo medio (s) en local y en clúster, y cuál es más rápido",
          ["Algoritmo", "N", "W", "Local (s)", "Clúster (s)", "Más rápido", "Diferencia"],
          [[A, N, W, seg(TL(A, N, W)), seg(T(A, N, W)),
            "Local" if TL(A, N, W) < T(A, N, W) else "Clúster",
            coma(100 * abs(TL(A, N, W) - T(A, N, W)) / max(TL(A, N, W), T(A, N, W)), 1) + " %"]
           for A in ALGS for N in NS for W in WS])

    # ---- 2.2 Escalabilidad comparada: barras lado a lado por workers, un panel por N
    d = carpeta("2.2_escalabilidad")
    for A in ALGS:
        fig, axs = plt.subplots(2, 3, figsize=(9, 5.4))
        for ax, N in zip(axs.flat, NS):
            xb = np.arange(len(WS))
            for k, (esc, f) in enumerate((("local", TL), ("cluster", T))):
                v = [f(A, N, W) for W in WS]
                ax.bar(xb + (k - 0.5) * 0.38, v, 0.36, color=C_ESC[esc], label=NOM_ESC[esc])
            ax.set_xticks(xb); ax.set_xticklabels([f"{W}W" for W in WS]); ax.set_title(f"N = {N}", fontsize=10)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: seg(v) if v else "0"))
        for ax in axs[:, 0]: ax.set_ylabel("Tiempo medio (s)")
        h, l = axs[0, 0].get_legend_handles_labels()
        fig.legend(h, l, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 0.99))
        fig.suptitle(f"{A}: tiempo con 1, 2 y 3 workers, local frente a clúster", y=1.04)
        fig.tight_layout(rect=(0, 0, 1, 0.95))
        guardar(fig, d, f"barras_workers_{A}")
    tabla(d, "tabla_escalabilidad", "Aceleración con 3 workers (T₁ ÷ T₃): local frente a clúster",
          ["Algoritmo", "N", "Local", "Clúster", "Escala mejor"],
          [[A, N, coma(TL(A, N, 1) / TL(A, N, 3), 2) + "×", coma(T(A, N, 1) / T(A, N, 3), 2) + "×",
            "Local" if TL(A, N, 1) / TL(A, N, 3) > T(A, N, 1) / T(A, N, 3) else "Clúster"]
           for A in ALGS for N in NS])

    # ---- 2.3 Throughput
    d = carpeta("2.3_throughput")
    for A in ALGS:
        fig, axs = plt.subplots(1, 3, figsize=(9, 3.4), sharey=True)
        for ax, W in zip(axs, WS):
            for esc, f in (("local", TL), ("cluster", T)):
                ax.plot(X, [3600 / f(A, N, W) for N in NS], color=C_ESC[esc], lw=2, marker="o", ms=4,
                        label=f"{NOM_ESC[esc]} ({W} worker{'s' if W > 1 else ''})")
            ax.set_yscale("log"); ax.minorticks_off(); ax.set_xticks(X); ax.set_xticklabels(NS, fontsize=8)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: coma(v, 0))); ax.set_xlabel("N")
            ax.set_title(f"{W} worker" + ("s" if W > 1 else "")); ax.legend(fontsize=8)
        axs[0].set_ylabel("Multiplicaciones por hora (escala log)")
        fig.suptitle(f"Throughput de {A}: local frente a clúster", y=1.03)
        guardar(fig, d, f"throughput_{A}")
    tabla(d, "tabla_throughput", "Throughput (multiplicaciones por hora)",
          ["Algoritmo", "N", "Local 1W", "Clúster 1W", "Local 2W", "Clúster 2W", "Local 3W", "Clúster 3W"],
          [[A, N] + [coma(3600 / f(A, N, W), 0) for W in WS for f in (TL, T)] for A in ALGS for N in NS])

    # ---- 2.4 Variabilidad (coeficiente de variación) por workers
    d = carpeta("2.4_variabilidad")
    for A in ALGS:
        fig, axs = plt.subplots(1, 3, figsize=(9, 3.4), sharey=True)
        for ax, W in zip(axs, WS):
            for k, (esc, D) in enumerate((("local", LOC), ("cluster", E1))):
                ax.bar(np.array(X) + (k - 0.5) * 0.38, [CV(D, (A, N, W)) for N in NS], 0.36,
                       color=C_ESC[esc], label=NOM_ESC[esc])
            ax.set_xticks(X); ax.set_xticklabels(NS, fontsize=8); ax.set_xlabel("N")
            ax.set_title(f"{W} worker" + ("s" if W > 1 else ""))
        axs[0].set_ylabel("Variación entre las 30 repeticiones (CV, %)"); axs[0].legend()
        fig.suptitle(f"{A}: qué tanto cambia el tiempo de una repetición a otra", y=1.03)
        guardar(fig, d, f"variabilidad_{A}")
    tabla(d, "tabla_variabilidad",
          "Desviación estándar (s) y coeficiente de variación (CV = desviación ÷ media) de las 30 repeticiones",
          ["Algoritmo", "N", "W", "Local media (s)", "Local desv. (s)", "Local CV", "Clúster media (s)",
           "Clúster desv. (s)", "Clúster CV"],
          [[A, N, W, seg(TL(A, N, W)), seg(st.stdev(LOC[(A, N, W)])), coma(CV(LOC, (A, N, W)), 1) + " %",
            seg(T(A, N, W)), seg(st.stdev(E1[(A, N, W)])), coma(CV(E1, (A, N, W)), 1) + " %"]
           for A in ALGS for N in NS for W in WS])

# ---- 2.5 Heterogeneidad de los nodos (opcional: velocidad_nodos.txt)
vel = os.path.join(RAIZ, "velocidad_nodos.txt")
CPU = {"NBIG333": "Xeon Gold 6240R @ 2,40 GHz", "NBIG305": "Xeon Gold 6348 @ 2,60 GHz",
       "NBIG291": "Xeon E5-2650 v4 @ 2,20 GHz", "NBIG296": "Xeon Gold 6348 @ 2,60 GHz"}
ROL = {"NBIG333": "master / local", "NBIG305": "worker 1", "NBIG291": "worker 2", "NBIG296": "worker 3"}
d = carpeta("2.5_heterogeneidad_nodos")
filas = [[n, CPU[n], ROL[n]] for n in CPU]
if os.path.exists(vel):
    dv = defaultdict(list)
    for linea in open(vel, encoding="utf-8"):
        p = linea.split()
        if len(p) == 3 and p[2].isdigit(): dv[p[0]].append(int(p[2]) / 1e6)
    nodos = [n for n in CPU if n in dv]
    m = [st.mean(dv[n]) for n in nodos]
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    ax.bar(range(len(nodos)), m, 0.55, color="#2a78d6")
    for i, v in enumerate(m): ax.text(i, v * 1.01, seg(v) + " s", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(range(len(nodos))); ax.set_xticklabels([f"{n}\n{CPU[n].split(' @')[0]}" for n in nodos], fontsize=8)
    ax.set_ylabel("Tiempo medio (s)"); ax.set_title("Mismo cálculo (FxT, N = 1536, 1 worker) en cada nodo")
    guardar(fig, d, "velocidad_nodos")
    filas = [[n, CPU[n], ROL[n], seg(st.mean(dv[n])) if n in dv else "-"] for n in CPU]
    tabla(d, "tabla_nodos", "Procesador, rol y tiempo del mismo cálculo en cada nodo",
          ["Nodo", "Procesador", "Rol en el experimento", "FxT N=1536 (s)"], filas, [0.16, 0.38, 0.24, 0.22])
else:
    tabla(d, "tabla_nodos", "Procesador y rol de cada nodo", ["Nodo", "Procesador", "Rol en el experimento"],
          filas, [0.2, 0.5, 0.3])

# ============================================================ EXPERIMENTO 3
if OVH:
    O = lambda A, N, W, k: OVH[(A, N, W)][k]
    # ---- 3.1 Overhead según N y workers
    d = carpeta("3.1_overhead_N_workers")
    for A in ALGS:
        fig, ax = plt.subplots(figsize=(6.5, 3.6))
        for W in WS:
            v = [O(A, N, W, "pct") for N in NS]
            ax.plot(X, v, color=C_W[W], lw=2, marker="o", ms=5, label=f"{W} worker" + ("s" if W > 1 else ""))
        eje_N(ax); ax.set_ylim(0, 70); ax.set_ylabel("Overhead (% del tiempo total)")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: coma(v, 0) + " %"))
        ax.set_title(f"{A}: parte del tiempo que no es cálculo"); ax.legend()
        guardar(fig, d, f"overhead_porcentaje_{A}")
    tabla(d, "tabla_overhead", "Overhead: porcentaje del tiempo total que no es cálculo",
          ["N", "FxC 1W", "FxC 2W", "FxC 3W", "FxT 1W", "FxT 2W", "FxT 3W"],
          [[N] + [coma(O(A, N, W, "pct"), 2) + " %" for A in ALGS for W in WS] for N in NS])

    # ---- 3.2 Overhead absoluto (s) frente a porcentual
    d = carpeta("3.2_overhead_absoluto_vs_porcentual")
    for A in ALGS:
        fig, ax = plt.subplots(figsize=(6.5, 3.6))
        for W in WS:
            ax.plot(X, [O(A, N, W, "ovh") for N in NS], color=C_W[W], lw=2, marker="o", ms=5,
                    label=f"{W} worker" + ("s" if W > 1 else ""))
        eje_N(ax); ax.set_ylabel("Overhead (segundos)")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: coma(v, 2)))
        ax.set_title(f"{A}: tiempo que no es cálculo, en segundos"); ax.legend()
        guardar(fig, d, f"overhead_segundos_{A}")
    tabla(d, "tabla_overhead_s_vs_pct", "Con 3 workers: overhead en segundos y en % del tiempo total",
          ["N", "FxC total (s)", "FxC overhead (s)", "FxC overhead %", "FxT total (s)", "FxT overhead (s)", "FxT overhead %"],
          [[N] + sum([[seg(O(A, N, 3, "T")), coma(O(A, N, 3, "ovh"), 3), coma(O(A, N, 3, "pct"), 2) + " %"]
                      for A in ALGS], []) for N in NS])

    # ---- 3.3 FxT vs FxC (porcentaje, escala normal)
    d = carpeta("3.3_overhead_FxT_vs_FxC")
    fig, axs = plt.subplots(1, 3, figsize=(9, 3.4), sharey=True)
    for ax, W in zip(axs, WS):
        for A in ALGS:
            ax.plot(X, [O(A, N, W, "pct") for N in NS], color=C_ALG[A], lw=2, marker="o", ms=4, label=A)
        ax.set_xticks(X); ax.set_xticklabels(NS, fontsize=8); ax.set_xlabel("N"); ax.set_ylim(0, 70)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: coma(v, 0) + " %"))
        ax.set_title(f"{W} worker" + ("s" if W > 1 else ""))
    axs[0].set_ylabel("Overhead (% del tiempo total)"); axs[0].legend()
    fig.suptitle("Overhead de FxC frente a FxT", y=1.03)
    guardar(fig, d, "overhead_FxT_vs_FxC")

    # ---- 3.4 Relación con la eficiencia del Experimento 1 (en segundos)
    d = carpeta("3.4_overhead_vs_eficiencia")
    for A in ALGS:
        fig, ax = plt.subplots(figsize=(6.5, 3.6))
        perdida = [T(A, N, 3) - T(A, N, 1) / 3 for N in NS]
        ovh = [O(A, N, 3, "ovh") for N in NS]
        ax.bar(np.array(X) - 0.19, perdida, 0.36, color="#9aa5b1", label="Tiempo perdido frente al ideal (Exp. 1)")
        ax.bar(np.array(X) + 0.19, ovh, 0.36, color=C_ALG[A], label="Overhead de comunicación (Exp. 3)")
        eje_tiempo_log(ax); eje_N(ax); ax.set_ylabel("Segundos (escala log)")
        ax.set_title(f"{A} con 3 workers: ¿cuánto de la pérdida es comunicación?")
        ax.legend(fontsize=8, loc="upper left")
        guardar(fig, d, f"perdida_vs_overhead_{A}")
    tabla(d, "tabla_perdida_vs_overhead",
          "Con 3 workers: tiempo perdido frente al ideal (T₃ − T₁/3) y cuánto de él es overhead de comunicación",
          ["Algoritmo", "N", "Real T₃ (s)", "Ideal T₁/3 (s)", "Perdido (s)", "Overhead (s)", "Eficiencia", "Overhead %"],
          [[A, N, seg(T(A, N, 3)), seg(T(A, N, 1) / 3), seg(T(A, N, 3) - T(A, N, 1) / 3), coma(O(A, N, 3, "ovh"), 3),
            coma(100 * T(A, N, 1) / (3 * T(A, N, 3)), 1) + " %", coma(O(A, N, 3, "pct"), 2) + " %"]
           for A in ALGS for N in NS])

print("\nListo. Revisa la carpeta graficas/ (una subcarpeta por análisis).")
