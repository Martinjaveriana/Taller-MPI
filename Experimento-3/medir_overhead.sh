#!/usr/bin/env bash
# KPI de OVERHEAD paralelo (MPI) en CLUSTER: FxC y FxT
#   T_total  = tiempo del master (gettimeofday)
#   T_comp   = MAX entre workers del tiempo puro de calculo
#   OVERHEAD = T_total - T_comp ;  KPI = OVERHEAD% = 100*OVERHEAD/T_total
# Estructura esperada (raiz = carpeta que contiene esta carpeta):
#   MPI-taller/  nodos  src/  Experimento-3/medir_overhead.sh
# Lee ../nodos y ../src (sin modificarlos). Escribe solo en ESTA carpeta
# (src_ovh/, bin/, resultados_overhead*/) y en <esta carpeta>/bin de los workers.
# Uso: ./Experimento-3/medir_overhead.sh | QUICK=1 ... | LOCAL=1 ... (local explicito)
export LC_ALL=C; set -u; cd "$(dirname "$0")"; HERE="$PWD"; RAIZ="$(cd .. && pwd)"; export RAIZ
log(){ echo "[$(date +%H:%M:%S)] $*"; }
# Opciones de red iguales en los 3 experimentos: solo la interfaz ens33 (evita docker0)
OPC_RED="${OPC_RED:---mca btl_tcp_if_include ens33 --mca oob_tcp_if_include ens33}"
export HWLOC_COMPONENTS=-gl                      # quita el aviso "Authorization required..."
HOSTFILE="${HOSTFILE:-$RAIZ/nodos}"; REPS="${REPS:-30}"
SIZES="${SIZES:-192 384 768 1536 2304 3072}"; WORKERS="${WORKERS:-1 2 3}"
TMO="${TMO:-900}"; OUT="resultados_overhead"
[ "${QUICK:-0}" = "1" ] && { REPS=3; SIZES="192 384"; OUT="resultados_overhead_quick"; }
mkdir -p "$OUT" bin src_ovh

log "1/5 Parcheando fuentes de $RAIZ/src (copias en src_ovh/*_ovh.c)"
python3 - <<'PY' || { echo "Fallo el parche"; exit 1; }
import os
RAIZ = os.environ["RAIZ"]
for alg in ("FxC", "FxT"):
    s = open(f"{RAIZ}/src/mxmMPI_{alg}.c", encoding="utf-8", errors="replace").read()
    def rep(old, new):
        global s
        assert old in s, f"no se encontro: {old}"
        s = s.replace(old, new, 1)
    rep("double tti, ttf;", "double tti, ttf, t_comp=0.0, t_trp=0.0, t_comp_max=0.0, c0;")
    if alg == "FxC":
        rep("mxmFxC(tW_matA, matrixB, tW_matC, tW, N);",
            "c0=MPI_Wtime(); mxmFxC(tW_matA, matrixB, tW_matC, tW, N); t_comp=MPI_Wtime()-c0;")
    else:
        rep("mxmFxT(tW_matA, matrixT, tW_matC, tW, N);",
            "c0=MPI_Wtime(); mxmFxT(tW_matA, matrixT, tW_matC, tW, N); t_comp=MPI_Wtime()-c0;")
        rep("matrixTRP(matrixB, matrixT, N);",
            "c0=MPI_Wtime(); matrixTRP(matrixB, matrixT, N); t_trp=MPI_Wtime()-c0;")
    rep("ttf = MPI_Wtime();",
        "ttf = MPI_Wtime();\n\tMPI_Reduce(&t_comp, &t_comp_max, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);")
    rep('printf("Tiempo MPI = %10f\\n", (ttf-tti));',
        'printf("Tiempo MPI = %10f\\n", (ttf-tti));\n\t\tprintf("OVH %f %f\\n", t_comp_max, t_trp);')
    open(f"src_ovh/mxmMPI_{alg}_ovh.c", "w").write(s)
PY

log "2/5 Compilando"
for A in FxC FxT; do
  mpicc -fopenmp -I"$RAIZ/src" src_ovh/mxmMPI_${A}_ovh.c "$RAIZ/src/functions.c" -o bin/mxmMPI_${A}_ovh -lm 2>/dev/null \
    || { echo "Fallo compilando $A (esta instalado openmpi?)"; exit 1; }
done

HOSTS=""; MODE=local
if [ "${LOCAL:-0}" != "1" ]; then
  [ -s "$HOSTFILE" ] || { echo "ERROR: no existe o esta vacio el archivo de nodos: $HOSTFILE (usa LOCAL=1 para correr local)"; exit 1; }
  HOSTS=$(grep -v '^[[:space:]]*#' "$HOSTFILE" | awk 'NF{print $1}')
  [ -n "$HOSTS" ] || { echo "ERROR: $HOSTFILE no tiene maquinas"; exit 1; }
  MODE=cluster
fi

if [ "$MODE" = cluster ]; then
  NH=$(echo "$HOSTS" | wc -w); MPI="mpirun $OPC_RED -x HWLOC_COMPONENTS --hostfile $HOSTFILE"
  log "3/5 Distribuyendo binarios a los workers (solo $HERE/bin)"
  for h in $HOSTS; do
    case "$h" in "$(hostname)"|localhost|127.0.0.1) continue;; esac
    ssh -o BatchMode=yes -o ConnectTimeout=8 "$h" "mkdir -p '$HERE/bin'" \
      || { echo "No hay SSH sin clave hacia $h"; exit 1; }
    scp -q -o BatchMode=yes bin/mxmMPI_FxC_ovh bin/mxmMPI_FxT_ovh "$h:$HERE/bin/" \
      || { echo "Fallo scp a $h"; exit 1; }
    log "   ok $h"
  done
  log "4/5 Prueba del cluster: mpirun -np $NH hostname"
  OUTH=$(timeout 60 $MPI -np $NH hostname 2>&1) || { echo "$OUTH"; echo "mpirun fallo o excedio 60s"; exit 1; }
  echo "$OUTH"
  if [ "${SKIPCHECK:-0}" != "1" ] && [ "$(echo "$OUTH" | grep -x -F -f <(echo "$HOSTS") | sort -u | wc -l)" -ne "$NH" ]; then
    echo "ERROR: se esperaban $NH maquinas distintas"; exit 1
  fi
else
  NH=4; MPI="mpirun --oversubscribe -x HWLOC_COMPONENTS"
  log "3-4/5 Modo LOCAL (--oversubscribe), sin distribucion"
fi
log "   verificando que los nodos esten libres de trabajos ajenos"
BUSY=0
for h in $HOSTS; do
  if [ "$h" = "$(hostname)" ]; then o=$(pgrep -fa "mpirun|mxmMPI_" | grep -v -E "pgrep|_ovh")
  else o=$(ssh -o BatchMode=yes -o ConnectTimeout=8 "$h" 'pgrep -fa "mpirun|mxmMPI_" | grep -v -E "pgrep|_ovh"' 2>/dev/null); fi
  [ -n "$o" ] && { echo "OCUPADO $h:"; echo "$o"; BUSY=1; }
done
[ "$BUSY" = 1 ] && [ "${FORCE:-0}" != 1 ] && { echo "Hay trabajos ajenos en el cluster. Coordina turno (o FORCE=1 bajo tu riesgo)."; exit 1; }
{ echo "fecha: $(date -Is)"; echo "modo: $MODE"; echo "hosts: $HOSTS"
  lscpu | grep -E 'Model name|^CPU\(s\)|L2|L3'; mpirun --version | head -1
  echo "REPS=$REPS SIZES=$SIZES WORKERS=$WORKERS"; } > "$OUT/entorno.txt"

CSV="$OUT/overhead_crudo.csv"
echo "algoritmo,N,workers,rep,t_total_s,t_comp_max_s,t_trp_s,overhead_s,overhead_pct" > "$CSV"
run_one() {   # $1=algo $2=N $3=W
  local out us oc
  out=$(timeout "$TMO" $MPI -np $(( $3 + 1 )) ./bin/mxmMPI_$1_ovh "$2" 1 2>&1) || return 1
  us=$(echo "$out" | awk 'NF==1 && $1 ~ /^[0-9.]+$/ {print $1; exit}')
  oc=$(echo "$out" | awk '$1=="OVH" {print $2","$3; exit}')
  [ -n "$us" ] && [ -n "$oc" ] && echo "$(awk -v u="$us" 'BEGIN{printf "%.6f", u/1e6}'),$oc"
}
total=$(( $(echo $SIZES | wc -w) * $(echo $WORKERS | wc -w) * 2 * REPS )); n=0
log "5/5 Midiendo ($total ejecuciones)"
for N in $SIZES; do for W in $WORKERS; do
  [ $((N % W)) -ne 0 ] && { echo "SKIP N=$N W=$W (no divisible)"; continue; }
  [ $((W + 1)) -gt "$NH" ] && [ "$MODE" = cluster ] && { echo "SKIP W=$W (faltan nodos)"; continue; }
  log "calentamiento N=$N W=$W"
  for A in FxC FxT; do run_one $A $N $W >/dev/null; done
  for ((r=1;r<=REPS;r++)); do for A in FxC FxT; do
    res=$(run_one $A $N $W) || { echo "!! fallo $A N=$N W=$W rep=$r"; n=$((n+1)); continue; }
    IFS=, read -r tt tc tr <<< "$res"
    awk -v a=$A -v N=$N -v W=$W -v r=$r -v tt=$tt -v tc=$tc -v tr=$tr \
      'BEGIN{o=tt-tc; printf "%s,%d,%d,%d,%.6f,%.6f,%.6f,%.6f,%.2f\n",a,N,W,r,tt,tc,tr,o,100*o/tt}' >> "$CSV"
    n=$((n+1)); echo "[$n/$total] $A N=$N W=$W rep=$r  T=$tt comp=$tc"
  done; done
done; done

python3 - "$CSV" "$OUT" <<'PY'
import csv, sys, statistics as st, collections
rows = list(csv.DictReader(open(sys.argv[1])))
g = collections.defaultdict(list)
for r in rows: g[(r["algoritmo"], int(r["N"]), int(r["workers"]))].append(r)
f = lambda k, x: [float(r[k]) for r in x]
out = ["algoritmo,N,workers,reps,T_total_media_s,T_comp_media_s,overhead_media_s,overhead_pct_media,overhead_pct_desv"]
print(f"\n{'alg':4} {'N':>5} {'W':>2} {'reps':>4} {'T(s)':>9} {'comp(s)':>9} {'ovh(s)':>9} {'OVH %':>7} {'desv':>6}")
for (a, N, W), x in sorted(g.items()):
    p = f("overhead_pct", x); sd = st.stdev(p) if len(p) > 1 else 0.0
    m = lambda k: st.mean(f(k, x))
    line = (a, N, W, len(x), m("t_total_s"), m("t_comp_max_s"), m("overhead_s"), st.mean(p), sd)
    out.append("{},{},{},{},{:.4f},{:.4f},{:.4f},{:.2f},{:.2f}".format(*line))
    print("{:4} {:5d} {:2d} {:4d} {:9.3f} {:9.3f} {:9.3f} {:7.1f} {:6.1f}".format(*line))
open(sys.argv[2] + "/overhead_resumen.csv", "w").write("\n".join(out) + "\n")
print("\nListo:", sys.argv[2] + "/overhead_crudo.csv  y  overhead_resumen.csv")
PY
