#!/usr/bin/env python3
# =============================================================================
#  throughput.py - Calcula el THROUGHPUT (multiplicaciones por hora) a partir de
#                  resultados_local.csv y resultados_cluster.csv, y genera:
#                    * tablas CSV listas para graficar en Excel/Calc
#                    * graficas PNG (si esta instalado matplotlib)
#
#  USO:   python3 throughput.py
#         python3 throughput.py --tiempo mpi                 (usar "Tiempo MPI")
#         python3 throughput.py --decimal punto --sep ,      (si la hoja lee mal los numeros)
#         python3 throughput.py --sin-png                    (solo CSV)
#
#  Throughput = 3600 / T   (T = tiempo medio de una multiplicacion, en segundos)
# =============================================================================
import argparse, csv, os, statistics, sys
from collections import defaultdict

ap = argparse.ArgumentParser()
ap.add_argument("--sep", default=";")
ap.add_argument("--decimal", default="coma", choices=["coma", "punto"])
ap.add_argument("--carpeta", default=".")
ap.add_argument("--tiempo", default="us", choices=["us", "mpi"])
ap.add_argument("--sin-png", action="store_true", help="no generar graficas PNG")
args = ap.parse_args()
SEP = args.sep


def f(x, d=1):
    if x is None:
        return ""
    s = f"{x:.{d}f}"
    return s.replace(".", ",") if args.decimal == "coma" else s


# ------------------------------------------------------------ 1. leer datos
grupos = defaultdict(list)
for esc in ("local", "cluster"):
    ruta = os.path.join(args.carpeta, f"resultados_{esc}.csv")
    if not os.path.exists(ruta):
        continue
    with open(ruta, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh, delimiter=";"):
            try:
                t = float(r["tiempo_us"] if args.tiempo == "us" else r["tiempo_mpi_us"])
                grupos[(r["escenario"], r["algoritmo"], int(r["workers"]), int(r["N"]))].append(t / 1e6)
            except (ValueError, KeyError):
                pass
if not grupos:
    sys.exit("No encontre resultados_local.csv ni resultados_cluster.csv en esta carpeta.")

# throughput = 3600 / tiempo medio (s)
TH = {k: 3600.0 / statistics.mean(v) for k, v in grupos.items()}
escenarios = sorted({k[0] for k in TH}, key=lambda e: 0 if e == "local" else 1)
algos = sorted({k[1] for k in TH})
Ws = sorted({k[2] for k in TH})
Ns = sorted({k[3] for k in TH})


def escribir(nombre, enc, filas):
    with open(os.path.join(args.carpeta, nombre), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=SEP)
        w.writerow(enc)
        w.writerows(filas)
    print("  creado:", nombre)


print("Archivos generados:")
mpl = None
if not args.sin_png:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        mpl = plt
    except ImportError:
        print("  (matplotlib no esta instalado: solo se crean los CSV. Para las PNG:  sudo apt install -y python3-matplotlib)")

COL = {"local": "#C77700", "cluster": "#0F5C6E"}
wmax = max(Ws)
for a in algos:
    cols = [(e, w) for e in escenarios for w in Ws if any((e, a, w, N) in TH for N in Ns)]
    # T1: throughput vs N (una columna por escenario y workers)
    escribir(f"t1_throughput_vs_N_{a}.csv", ["N"] + [f"{e} w={w} (mult/hora)" for e, w in cols],
             [[N] + [f(TH.get((e, a, w, N))) for e, w in cols] for N in Ns])
    # T2: throughput vs workers (una columna por escenario y N)
    cols2 = [(e, N) for e in escenarios for N in Ns if any((e, a, w, N) in TH for w in Ws)]
    escribir(f"t2_throughput_vs_workers_{a}.csv", ["workers"] + [f"{e} N={N}" for e, N in cols2],
             [[w] + [f(TH.get((e, a, w, N))) for e, N in cols2] for w in Ws])
    # T3: mejora del cluster sobre local (mismos workers)
    if "local" in escenarios and "cluster" in escenarios:
        enc = ["N"] + [f"mejora cluster/local w={w} (veces)" for w in Ws]
        escribir(f"t3_mejora_cluster_{a}.csv", enc,
                 [[N] + [f(TH[("cluster", a, w, N)] / TH[("local", a, w, N)], 3)
                         if ("cluster", a, w, N) in TH and ("local", a, w, N) in TH else "" for w in Ws] for N in Ns])

    if mpl:
        # G-T1: throughput vs N, local vs cluster (con el maximo de workers)
        fig, ax = mpl.subplots(figsize=(7, 4.2))
        for e in escenarios:
            pts = [(N, TH[(e, a, wmax, N)]) for N in Ns if (e, a, wmax, N) in TH]
            if pts:
                ax.plot(*zip(*pts), marker="o", lw=2, color=COL[e], label=f"{e} ({wmax} workers)")
        ax.set_xlabel("N (tamaño de la matriz)"); ax.set_ylabel("Throughput (multiplicaciones / hora)")
        ax.set_title(f"Throughput vs tamaño de matriz ({a})"); ax.set_yscale("log"); ax.set_xticks(Ns)
        ax.grid(alpha=.3); ax.legend(); fig.tight_layout()
        fig.savefig(os.path.join(args.carpeta, f"grafica_T1_throughput_vs_N_{a}.png"), dpi=150); mpl.close(fig)
        print(f"  creado: grafica_T1_throughput_vs_N_{a}.png")
        # G-T2: throughput vs workers (para el N mas grande)
        Nb = max(Ns)
        fig, ax = mpl.subplots(figsize=(7, 4.2))
        for e in escenarios:
            pts = [(w, TH[(e, a, w, Nb)]) for w in Ws if (e, a, w, Nb) in TH]
            if pts:
                ax.plot(*zip(*pts), marker="o", lw=2, color=COL[e], label=e)
        ax.set_xlabel("Workers"); ax.set_ylabel("Throughput (multiplicaciones / hora)")
        ax.set_title(f"Throughput vs workers, N={Nb} ({a})"); ax.set_xticks(Ws)
        ax.grid(alpha=.3); ax.legend(); fig.tight_layout()
        fig.savefig(os.path.join(args.carpeta, f"grafica_T2_throughput_vs_workers_{a}.png"), dpi=150); mpl.close(fig)
        print(f"  creado: grafica_T2_throughput_vs_workers_{a}.png")
        # G-T3: mejora del cluster (barras por N)
        if "local" in escenarios and "cluster" in escenarios:
            fig, ax = mpl.subplots(figsize=(7, 4.2))
            ancho = 0.8 / len(Ws)
            for i, w in enumerate(Ws):
                ys = [TH[("cluster", a, w, N)] / TH[("local", a, w, N)] if ("cluster", a, w, N) in TH and ("local", a, w, N) in TH else 0 for N in Ns]
                ax.bar([j + i * ancho for j in range(len(Ns))], ys, ancho, label=f"{w} workers")
            ax.axhline(1, color="gray", ls="--", lw=1)
            ax.set_xticks([j + 0.4 - ancho / 2 for j in range(len(Ns))]); ax.set_xticklabels(Ns)
            ax.set_xlabel("N (tamaño de la matriz)"); ax.set_ylabel("Mejora del cluster (veces)")
            ax.set_title(f"Throughput del cluster / throughput local ({a})\nsobre 1: el cluster gana")
            ax.grid(alpha=.3, axis="y"); ax.legend(); fig.tight_layout()
            fig.savefig(os.path.join(args.carpeta, f"grafica_T3_mejora_cluster_{a}.png"), dpi=150); mpl.close(fig)
            print(f"  creado: grafica_T3_mejora_cluster_{a}.png")

print("\nListo. Los CSV (t1_, t2_, t3_) se abren en Excel; las PNG ya son las graficas.")

