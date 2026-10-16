# Taller MPI — Multiplicación de matrices distribuida

Pontificia Universidad Javeriana · Introducción a Sistemas Distribuidos

Evaluación del rendimiento de la multiplicación de matrices cuadradas distribuida con
MPI sobre un clúster de cuatro nodos Linux. Se comparan dos algoritmos con 1, 2 y 3
workers. También se compara la ejecución en clúster con la ejecución local y se mide el
overhead de la comunicación.

**Autores:** Ana María Murcia Gómez, Martín David Sanmiguel Delgado, Jhon Sebastián
Mejía, David Felipe Mannios.
El informe completo está en [docs/](docs/).

## Algoritmos

| Programa | Algoritmo | Idea |
|---|---|---|
| `mxmMPI_FxC` | Filas × Columnas (clásico) | Recorre B por columnas, así que hay muchos fallos de caché (C guarda las matrices por filas, *row-major*). |
| `mxmMPI_FxT` | Filas × Transpuesta | El master transpone B antes de enviarla y los workers recorren las dos matrices por filas (localidad espacial). |

Los dos usan el esquema **master–worker**:

1. El master (rank 0) inicializa A y B. En FxT también calcula la transpuesta de B.
2. Envía B (o Bᵀ) completa a todos con `MPI_Bcast`.
3. Reparte A en tajadas de `N/W` filas con `MPI_Send` (W = número de workers = `np - 1`).
4. Cada worker multiplica su tajada y devuelve la parte de C con `MPI_Send`.
5. El master junta los resultados con `MPI_Recv` e imprime los tiempos.

El master no calcula; solo distribuye y recibe.

## Estructura

```
Taller-MPI/
├── Makefile          compila src/ → bin/
├── nodos             hostfile: NBIG333 (master), NBIG305, NBIG291, NBIG296 (slots=1)
├── src/              mxmMPI_FxC.c, mxmMPI_FxT.c, functions.c/.h
├── bin/              binarios compilados
├── Experimento-1/    principal: tiempo con 1, 2 y 3 workers en el clúster
├── Experimento-2/    local vs clúster y throughput
├── Experimento-3/    overhead paralelo
├── graficas.py       genera graficas/  (tablas y figuras del informe)
├── graficas2.py      genera graficas2/ (las mismas figuras, con otro formato de tablas)
└── docs/             informe en PDF
```

## Requisitos

- Open MPI (`mpicc`, `mpirun`). Se usó Open MPI 4.1.2 en Ubuntu.
- SSH sin contraseña desde el master hacia los workers.
- Los binarios deben estar en la misma ruta en todos los nodos.
- Perl (Experimento 1), Bash y Python 3 con `matplotlib` y `numpy` (gráficas).

## Compilar

```bash
make mxmMPI_FxC mxmMPI_FxT
```

> `make` sin argumentos falla, porque el Makefile también lista variantes OpenMP/Pthreads
> (`mxmMPIompFxC`, `mxmMPIposixFxT`, …) cuyos fuentes no están en `src/`.

## Ejecutar una multiplicación

```bash
mpirun --hostfile nodos -np <W+1> --map-by node \
       --mca btl_tcp_if_include ens33 --mca oob_tcp_if_include ens33 \
       -x HWLOC_COMPONENTS=-gl \
       bin/mxmMPI_FxT <N> 1
```

- `N`: dimensión de la matriz. Debe ser divisible por el número de workers.
- El segundo argumento (hilos) es obligatorio pero no se usa.
- `-np` = master + workers, así que con 3 workers es `-np 4`.
- Salida: la primera línea es el tiempo en microsegundos (`gettimeofday` en el master).
  Después sale `Tiempo MPI = <s>`. Si `N < 14`, también se imprimen las matrices.
- Las opciones `--mca … ens33` hacen que Open MPI use solo la red del laboratorio (sin
  ellas puede intentar usar `docker0` y quedarse bloqueado). `HWLOC_COMPONENTS=-gl`
  quita el aviso *"Authorization required"*.

## Experimentos

Los tres usan los mismos parámetros: FxC y FxT, N ∈ {192, 384, 768, 1536, 2304, 3072},
W ∈ {1, 2, 3} y 30 repeticiones por combinación. Se ejecutan desde el nodo master
(NBIG333) y compilan solos con el Makefile de la raíz.

### Experimento 1 — tiempo vs número de workers

```bash
nohup perl Experimento-1/lanzador.pl > Experimento-1/bateria.log 2>&1 &
tail -f Experimento-1/bateria.log
```

Resultados: `Experimento-1/Soluciones/<algoritmo>-N-<N>-W-<W>.txt`, con las columnas
`Ejecucion  Tiempo_us  TiempoMPI_s`. Los tamaños, workers y repeticiones se cambian al
principio de `lanzador.pl`.

### Experimento 2 — local vs clúster y throughput

```bash
./Experimento-2/experimento.sh local      # todos los procesos en una sola máquina
./Experimento-2/experimento.sh cluster    # procesos repartidos según ./nodos
cd Experimento-2 && python3 throughput.py # throughput = 3600 / tiempo medio
```

Resultados: `Experimento-2/resultados_<escenario>.csv` (separado por `;`). También deja
`entorno_<escenario>.txt` con los datos de la máquina. Antes de cada combinación hace una
corrida de calentamiento que no se guarda. La configuración se puede cambiar con variables
de entorno:

```bash
NS="600 1200" WORKERS="1 3" REPS=5 ./Experimento-2/experimento.sh cluster
```

### Experimento 3 — overhead

```bash
QUICK=1 ./Experimento-3/medir_overhead.sh                                   # prueba rápida
nohup ./Experimento-3/medir_overhead.sh > Experimento-3/corrida.log 2>&1 &  # completa
```

El script copia `src/` a `Experimento-3/src_ovh/` y le agrega medición de tiempos (no
modifica `src/`). Luego compila, copia los binarios a los workers por `scp` y verifica que
no haya otros trabajos MPI corriendo. Las medidas son:

- `T_total`: tiempo del master.
- `T_comp`: el tiempo de cálculo del worker más lento (`MPI_Reduce` con `MPI_MAX`).
- `Overhead = T_total − T_comp` y `Overhead % = 100 · Overhead / T_total`.

Resultados: `Experimento-3/resultados_overhead/overhead_crudo.csv` y `overhead_resumen.csv`.
Variables: `LOCAL=1` (correr en una sola máquina), `REPS`, `SIZES`, `WORKERS` y `FORCE=1`
(corre aunque haya trabajos ajenos en el clúster).

## Gráficas

```bash
python3 graficas.py    # → graficas/
python3 graficas2.py   # → graficas2/
```

Leen los resultados de los tres experimentos y generan una carpeta por análisis
(`1.1_FxC_vs_FxT`, `2.3_throughput`, `3.1_overhead_N_workers`, …). Cada carpeta tiene
figuras PNG y tablas en CSV (con coma decimal, para Excel en español) y en PNG.

## Conclusiones principales

- **FxT es más rápido que FxC en todos los casos**, y la diferencia aumenta con N. Con
  3072 × 3072 la mejora llega a ~400 %.
- **Distribuir solo vale la pena con matrices grandes.** Con N = 192 y 384 el overhead se
  come casi toda la ganancia. Desde N = 768 la eficiencia supera el 89 %.
- **El overhead en porcentaje baja rápido al crecer N** y sube con más workers. FxT tiene
  un poco más de overhead porque el master transpone B, pero su tiempo total es menor.
- **Local vs clúster:** con matrices pequeñas siempre gana la ejecución local, porque los
  mensajes van por memoria compartida y no por la red. Con matrices grandes el clúster gana
  en FxC; en FxT la ejecución local ganó en todos los tamaños.
