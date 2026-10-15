GCC= mpicc -fopenmp -lm 
MODULO= functions
BIN= bin/
SRC= src/

PROGRAMAS=  mxmMPI_FxC mxmMPI_FxT mxmMPIompFxC mxmMPIompFxT mxmMPIposixFxC mxmMPIposixFxT
all: ${PROGRAMAS}

pruebaMPI:
	$(GCC) $@.c $(SRC)$(MODULO).c -o $(BIN)$@ 

mxmMPI_FxC:
	$(GCC) $(SRC)$@.c $(SRC)$(MODULO).c -o $(BIN)$@ 

mxmMPI_FxT:
	$(GCC) $(SRC)$@.c $(SRC)$(MODULO).c -o $(BIN)$@ 

mxmMPIompFxC:
	$(GCC) $(SRC)$@.c $(SRC)$(MODULO).c -o $(BIN)$@ 

mxmMPIompFxT:
	$(GCC) $(SRC)$@.c $(SRC)$(MODULO).c -o $(BIN)$@ 

mxmMPIposixFxC:
	$(GCC) $(SRC)$@.c $(SRC)$(MODULO).c -o $(BIN)$@ 

mxmMPIposixFxT:
	$(GCC) $(SRC)$@.c $(SRC)$(MODULO).c -o $(BIN)$@ 

clean:
	$(RM) $(BIN)*
