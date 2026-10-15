# Taller MPI — cómo correr los experimentos

Todo se ejecuta en el nodo master (NBIG333). Los tres experimentos usan los mismos
archivos de la raíz:

```
MPI-taller/
├── Makefile        compila src/ → bin/
├── nodos           NBIG333, NBIG305, NBIG291, NBIG296 (slots=1)
├── src/            código fuente (mxmMPI_FxC.c, mxmMPI_FxT.c, functions.c/.h)
├── bin/            binarios compilados
├── Experimento-1/  principal: tiempo con 1, 2 y 3 workers
├── Experimento-2/  throughput: local vs clúster
└── Experimento-3/  overhead paralelo
```

Opciones de `mpirun` comunes a los tres:
`--mca btl_tcp_if_include ens33 --mca oob_tcp_if_include ens33` (usa solo la red del
laboratorio, evita docker0) y `-x HWLOC_COMPONENTS` con `HWLOC_COMPONENTS=-gl`
(quita el aviso "Authorization required").

## Experimento 1 — principal

```bash
nohup perl Experimento-1/lanzador.pl > Experimento-1/bateria.log 2>&1 &
tail -f Experimento-1/bateria.log
```

Resultados: `Experimento-1/Soluciones/<algoritmo>-N-<N>-W-<W>.txt`.
Tamaños, workers y repeticiones se cambian al inicio de `lanzador.pl`.

## Experimento 2 — throughput, local vs clúster

```bash
./Experimento-2/experimento.sh local
./Experimento-2/experimento.sh cluster
cd Experimento-2 && python3 throughput.py
```

Resultados: `Experimento-2/resultados_local.csv`, `resultados_cluster.csv` y las tablas
y gráficas que genera `throughput.py`. Configuración sin editar el archivo:
`NS="600 1200" WORKERS="1 3" REPS=5 ./Experimento-2/experimento.sh cluster`.

## Experimento 3 — overhead

```bash
QUICK=1 ./Experimento-3/medir_overhead.sh                                  # prueba rápida
nohup ./Experimento-3/medir_overhead.sh > Experimento-3/corrida.log 2>&1 &  # completa
```

Resultados: `Experimento-3/resultados_overhead/`. Si no encuentra `nodos` se detiene;
para correrlo en una sola máquina hay que pedirlo con `LOCAL=1`.
