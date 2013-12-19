RUN=mpirun
PYT=ilp_solver.py

P=12

M=12
N=12
S=5

run:
	$(RUN) -np $(P) python $(PYT) $(M) $(N) $(S)

clean:
	rm -rf *.pyc
