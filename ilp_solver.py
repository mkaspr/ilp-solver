#!/usr/bin/env python

import sys
import time
from mpi_ilp import *
from mpi4py import MPI
from serial import Serial
from master import Master
from worker import Worker
from solver import Solver
from solver import SolverError
from problem_generator import ProblemGenerator
from time import clock

# runs serial or parallel solver
def startMaster(processCount):
    try:

        # get and show solution
        problem = getProblem()
        solution = getSolution(problem, processCount)
        showSolution(solution)

    # no solution found
    except SolverError:
        showError()

# reads in LP problem
def getProblem():
    # validate arguments
    if len(sys.argv) != 4:
        print "ERROR: invalid arguments"
        print "usage: rows cols seed"
        exit(0)

    # read arguments
    rows = int(sys.argv[1])
    cols = int(sys.argv[2])
    seed = int(sys.argv[3])

    # return random generator problem
    generator = ProblemGenerator()
    problem = generator.generate(rows, cols, seed)
    return problem

# gets solution from serial or parallel solver
def getSolution(problem, processCount):
    # single-process program
    if processCount == 1:
        solver = Serial(problem)

    # multi-process program
    else:
        workerCount = processCount - 1
        solver = Master(problem, workerCount)

    # get solution using correct solver
    return solver.solve()

# displays valid solution
def showSolution(solution):
    print solution

# displays non-solution error
def showError():
    print "No solution found"

# determine how MPI process should run
if __name__ == "__main__":
    start = clock()

    comm = MPI.COMM_WORLD
    size = comm.Get_size()
    rank = comm.Get_rank()

    # master process
    if rank == MASTER_RANK:
        startMaster(size)
        end = clock()
        print "RUNTIME: " + str(end - start)

    # worker process
    else:
        worker = Worker()
        worker.start()
