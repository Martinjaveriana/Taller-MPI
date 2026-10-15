/************************************************************************************************
								=	Pontificia Universidad Javeriana	=

	Author: John Corredor
	Versión Prototipo "Inicial" MPI Distribución de Matrices en Nodos de Cómputo	

	Descripción:
		=> MPI_Init:				- Inicializacíón del entorno MPI 
		=> MPI_Comm_size:			- Obtener cantidad de procesos o workers en ejecución
		=> MPI_Comm_rank:			- Obtener el ID del proceso o worker  
		=> MPI_Get_processor_name:	- Obtener nombre del Nodo de Cómputo 
		=> MPI_Finalize:			- Finalización del entorno MPI

	Ejecución:
		$mpirun -hostfile fileHOSTSMPI -np 3 ./mmMPIv1 8 1
************************************************************************************************/

#ifndef __MODULOMPI_H__
#define __MODULOMPI_H__

// Estructura de datos para la función de Hilos Posix Pthread
struct parametros{
	int nHilos;			// Cantidad de hilos pthreads
	int idHilo;			// Identificación del hilo pthreads 
	int N;          	// Dimensión Matrix 
	int tW;         	// Tajada de matrix para cada hilo pthread
	double *matA;		// Copia de matrixA en hilo pthread
	double *matB;		// Copia de matrixA en hilo pthread
	double *matC;		// Copia de matrixA en hilo pthread
};


//Función inicialización matrices
void iniMatrix(double *mA, double *mB, int D);

//Función impresión para verificación
void impMatrix(double *matrix, int D);

//Función matrix Transpuesta
void matrixTRP(double *mB, double *mT, int D);

//Función MxM: algoritmo clásico filasxcolumnas
void mxmFxC(double *mA, double *mB, double *mC, int tw, int D);

//Función MxM: algoritmo filas x transpuesta (filasA x filasB) 
void mxmFxT(double *mA, double *mB, double *mC, int tw, int D);

//Función MxM: algoritmo clásico con uso de OpenMP
void mxmOmpFxC(double *mA, double *mB, double *mC, int tw, int D, int nH);

//Función MxM: algoritmo FilasxFilas <Matrix Transpuesta> con OpenMP 
void mxmOmpFxT(double *mA, double *mB, double *mC, int tw, int D, int nH);

//Función MxM: algoritmo clásico con uso de Hilos Posix Pthreads 
void *mxmPosixFxC(void *variables);

//Función MxM: algoritmo FilasxFIlas <<matrix transpuesta>> con uso de Hilos Pthreads
void *mxmPosixFxT(void *variables);



//Función prueba OMP
void functionOMP(int nhilos);






void iniMatrixPrueba(double *mA, double *mB, int D);

void iniTime();

void endTime();

void argumentos(int cantidad);

void verificarDiv(int qworkers, int Dim);

void mensajeVerifica(int N, int cantidadW);

#endif
