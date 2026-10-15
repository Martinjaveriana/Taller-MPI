#!/usr/bin/perl
#**************************************************************************************
#   Pontificia Universidad Javeriana
#   Taller MPI - Experimento 1 (principal)
#
#   Ejecuta cada combinación (algoritmo, tamaño de matriz, número de trabajadores)
#   $repeticiones veces en el clúster y guarda las ejecuciones en un .txt por
#   combinación.
#
#   Estructura esperada del proyecto (raíz = carpeta que contiene esta carpeta):
#       MPI-taller/
#         Makefile  nodos  src/  bin/
#         Experimento-1/lanzador.pl   <- este script
#
#   Uso (desde cualquier carpeta, en el nodo maestro NBIG333):
#       perl Experimento-1/lanzador.pl
#       nohup perl Experimento-1/lanzador.pl > Experimento-1/bateria.log 2>&1 &
#
#   Salida:  Experimento-1/Soluciones/<algoritmo>-N-<N>-W-<W>.txt
#       Ejecucion   Tiempo_us   TiempoMPI_s
#**************************************************************************************
use strict;
use warnings;
use FindBin;
use Cwd qw(abs_path);

#---------------------------- Rutas del proyecto -------------------------------------
my $dirExp   = $FindBin::Bin;                     # .../MPI-taller/Experimento-1
my $raiz     = abs_path("$dirExp/..");            # .../MPI-taller
my $hostfile = "$raiz/nodos";
my $dirBin   = "$raiz/bin";

#---------------------------- Parámetros de la batería -------------------------------
my @algoritmos   = ("mxmMPI_FxC", "mxmMPI_FxT");     # Algoritmo 1 y Algoritmo 2
my @tamanos      = (192, 384, 768, 1536, 2304, 3072);# N (múltiplos de 12)
my @trabajadores = (1, 2, 3);                        # W = np - 1
my $repeticiones = 30;
my $dirSalida    = "$dirExp/Soluciones";

#---------------------------- Opciones de mpirun (iguales en los 3 experimentos) -----
# Usar solo la interfaz real del laboratorio (ens33): evita que Open MPI intente
# comunicarse por docker0 (172.17.0.1) y se quede bloqueado.
my $opcionesRed = "--mca btl_tcp_if_include ens33 --mca oob_tcp_if_include ens33";
# Quita el aviso "Authorization required...": apaga el módulo gráfico (gl) de hwloc
# y envía la variable a todos los nodos con -x.
$ENV{HWLOC_COMPONENTS} = "-gl";
$opcionesRed .= " -x HWLOC_COMPONENTS";

#---------------------------- Comprobaciones -----------------------------------------
-f $hostfile or die "Error: no existe el archivo de nodos: $hostfile\n";

mkdir $dirBin unless -d $dirBin;
system("make", "-C", $raiz, @algoritmos) == 0
    or die "Error: no se pudieron compilar @algoritmos con $raiz/Makefile\n";
foreach my $alg (@algoritmos) {
    -x "$dirBin/$alg" or die "Error: no existe el binario $dirBin/$alg\n";
}

mkdir $dirSalida unless -d $dirSalida;
my $logErrores = "$dirSalida/errores.log";        # avisos de mpirun, fuera de la pantalla

my $total  = @algoritmos * @tamanos * @trabajadores;
my $actual = 0;

print "Proyecto: $raiz\nNodos:    $hostfile\nSalida:   $dirSalida\n\n";

#---------------------------- Ejecución ----------------------------------------------
foreach my $alg (@algoritmos) {
    foreach my $N (@tamanos) {
        foreach my $W (@trabajadores) {
            $actual++;
            my $np      = $W + 1;                     # maestro + trabajadores
            my $archivo = "$dirSalida/$alg-N-$N-W-$W.txt";

            open(my $fh, ">", $archivo) or die "No se puede crear $archivo: $!\n";
            printf $fh "%-12s%-14s%s\n", "Ejecucion", "Tiempo_us", "TiempoMPI_s";

            print "[$actual/$total] $alg  N=$N  W=$W  (np=$np)\n";

            for (my $r = 1; $r <= $repeticiones; $r++) {
                my $cmd    = "mpirun --hostfile $hostfile -np $np --map-by node $opcionesRed "
                           . "$dirBin/$alg $N 1 2>>$logErrores";
                my @salida = `$cmd`;

                if ($? != 0 || !@salida) {
                    warn "   Fallo en la ejecucion $r: $cmd\n";
                    printf $fh "%-12d%-14s%s\n", $r, "ERROR", "ERROR";
                    next;
                }

                # Línea 1: tiempo en microsegundos (endTime); otra línea: "Tiempo MPI = x"
                my ($us)  = $salida[0] =~ /(\d+)/;
                my ($mpi) = map { /Tiempo MPI\s*=\s*([\d.]+)/ ? $1 : () } @salida;
                $us  = "NA" unless defined $us;
                $mpi = "NA" unless defined $mpi;

                printf $fh "%-12d%-14s%s\n", $r, $us, $mpi;
                print  "   ejecucion $r: $us us\n";
            }
            close($fh);
        }
    }
}

print "\nBateria terminada: $total combinaciones x $repeticiones ejecuciones.\n";
print "Resultados en $dirSalida/\n";
