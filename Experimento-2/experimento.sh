#!/bin/bash
# =============================================================================
#  experimento.sh  -  Bateria de experimentos: multiplicacion de matrices MPI
#
#  Estructura esperada (raiz = carpeta que contiene esta carpeta):
#     MPI-taller/  Makefile  nodos  src/  bin/  Experimento-2/experimento.sh
#
#  USO (en la maquina MASTER, desde cualquier carpeta):
#     ./Experimento-2/experimento.sh local    -> todos los procesos en UNA sola maquina
#     ./Experimento-2/experimento.sh cluster  -> procesos repartidos en las 4 maquinas (usa ../nodos)
#
#  Se puede cambiar la configuracion SIN editar el archivo, asi:
#     NS="600 1200" WORKERS="1 3" REPS=5 ./experimento.sh local
#
#  Resultado (en Experimento-2/): resultados_local.csv  o  resultados_cluster.csv
# =============================================================================

ESCENARIO="$1"
if [ "$ESCENARIO" != "local" ] && [ "$ESCENARIO" != "cluster" ]; then
    echo "Uso:  ./experimento.sh local     o     ./experimento.sh cluster"
    exit 1
fi

# ---------------------------- CONFIGURACION ----------------------------------
BASE="$(cd "$(dirname "$0")" && pwd)"            # carpeta de este experimento (resultados)
RAIZ="$(cd "$BASE/.." && pwd)"                   # raiz del proyecto: Makefile, nodos, src/, bin/
NS="${NS:-192 384 768 1536 2304 3072}"                   # tamanos de matriz N (deben ser multiplos de 60)
WORKERS="${WORKERS:-1 2 3}"                      # cantidad de workers a probar
REPS="${REPS:-30}"                               # repeticiones por configuracion
ALGOS="FxC FxT"                                  # FxC = clasico, FxT = con transpuesta
HOSTFILE="${HOSTFILE:-$RAIZ/nodos}"              # lista de maquinas (solo escenario cluster)
# Opciones de red iguales en los 3 experimentos: solo la interfaz ens33 (evita docker0)
EXTRA="${EXTRA:---mca btl_tcp_if_include ens33 --mca oob_tcp_if_include ens33}"
export HWLOC_COMPONENTS=-gl                      # quita el aviso "Authorization required..."
EXTRA="$EXTRA -x HWLOC_COMPONENTS"
# -----------------------------------------------------------------------------

SALIDA="$BASE/resultados_${ESCENARIO}.csv"
LOG="$BASE/log_${ESCENARIO}.txt"
ENTORNO="$BASE/entorno_${ESCENARIO}.txt"

# Compilar con el Makefile de la raiz y comprobar los binarios
mkdir -p "$RAIZ/bin"
make -C "$RAIZ" mxmMPI_FxC mxmMPI_FxT > /dev/null || { echo "ERROR: fallo la compilacion con $RAIZ/Makefile"; exit 1; }
for A in $ALGOS; do
    if [ ! -x "$RAIZ/bin/mxmMPI_$A" ]; then
        echo "ERROR: no existe $RAIZ/bin/mxmMPI_$A"
        exit 1
    fi
done
if [ "$ESCENARIO" = "cluster" ] && [ ! -f "$HOSTFILE" ]; then
    echo "ERROR: no existe el archivo de maquinas: $HOSTFILE"
    exit 1
fi

# Guardar datos de la maquina (para el informe)
{
    echo "Fecha: $(date)"
    echo "Escenario: $ESCENARIO"
    echo "Maquina: $(hostname)"
    echo "--- CPU ---";  lscpu | grep -E "Model name|^CPU\(s\)|Thread|MHz"
    echo "--- Memoria ---"; free -h | head -2
    echo "--- Sistema ---"; uname -srm
    echo "--- MPI ---"; mpirun --version | head -1
    echo "--- Configuracion ---"; echo "NS=$NS  WORKERS=$WORKERS  REPS=$REPS  EXTRA=$EXTRA"
} > "$ENTORNO"

# Encabezado del CSV (solo si el archivo no existe todavia)
if [ ! -f "$SALIDA" ]; then
    echo "escenario;algoritmo;workers;np;N;repeticion;tiempo_us;tiempo_mpi_us;fecha_hora" > "$SALIDA"
fi

# Funcion que ejecuta UNA corrida y devuelve lo que imprime el programa
#   argumentos:  algoritmo  N  np
correr() {
    local PROG="$RAIZ/bin/mxmMPI_$1"
    if [ "$ESCENARIO" = "local" ]; then
        mpirun --oversubscribe $EXTRA -np "$3" "$PROG" "$2" 1 2>>"$LOG"
    else
        mpirun --hostfile "$HOSTFILE" --map-by node $EXTRA -np "$3" "$PROG" "$2" 1 2>>"$LOG"
    fi
}

# Calcular cuantas corridas habra
TOTAL=0
for N in $NS; do for W in $WORKERS; do
    if [ $((N % W)) -eq 0 ]; then TOTAL=$((TOTAL + REPS*2)); fi
done; done
HECHAS=0
INICIO=$(date +%s)

echo "Escenario: $ESCENARIO | N: $NS | workers: $WORKERS | repeticiones: $REPS"
echo "Corridas a registrar: $TOTAL   (mas las de calentamiento, que no se guardan)"
echo "Resultados en: $SALIDA"
echo "-----------------------------------------------------------------------"

for N in $NS; do
  for W in $WORKERS; do
    NP=$((W + 1))                                   # procesos = 1 master + W workers
    if [ $((N % W)) -ne 0 ]; then
        echo "OMITIDO: N=$N no es divisible entre $W workers"
        continue
    fi

    # Calentamiento: una corrida de cada algoritmo que NO se guarda
    for A in $ALGOS; do correr "$A" "$N" "$NP" > /dev/null; done

    for R in $(seq 1 "$REPS"); do
      for A in $ALGOS; do                           # se alternan FxC y FxT a proposito
        SAL="$(correr "$A" "$N" "$NP")"
        US="$(echo "$SAL" | awk 'NF==1 && $1 ~ /^[0-9]+$/ {print $1; exit}')"
        TM="$(echo "$SAL" | awk '/Tiempo MPI/ {printf "%d", $4*1000000; exit}')"
        if [ -z "$US" ] || [ -z "$TM" ]; then
            echo "ATENCION: corrida fallida ($A N=$N W=$W rep=$R). Revisa $LOG"
            continue
        fi
        echo "$ESCENARIO;$A;$W;$NP;$N;$R;$US;$TM;$(date '+%Y-%m-%d %H:%M:%S')" >> "$SALIDA"
        HECHAS=$((HECHAS + 1))
        echo "[$HECHAS/$TOTAL] $A  N=$N  workers=$W  rep=$R  ->  $US us"
      done
    done
  done
done

FIN=$(date +%s)
echo "-----------------------------------------------------------------------"
echo "TERMINADO. Corridas guardadas: $HECHAS de $TOTAL. Duracion: $(( (FIN-INICIO)/60 )) min."
echo "Archivo: $SALIDA"
