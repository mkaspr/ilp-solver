#!/usr/bin/env python

import numpy as np
from mpi_ilp import *
from mpi4py import MPI
from solver import Solver
from solver import SolverError
from solution import Solution
from brancher import Brancher
from dictionary import Dictionary

class Worker:

    comm = None
    rank = None
    working = True
    problem = None
    handlers = None

    def __init__(self):
        self.comm = MPI.COMM_WORLD
        self.rank = self.comm.Get_rank()
        self.__createMessageHandlers()


    def start(self):
        # work until killed
        while self.working:
            if self.problem != None:
                self.__solveProblem()
            else:
                self.__probeMessages()


    def __probeMessages(self):
        status = MPI.Status()
        self.comm.Probe(MASTER_RANK, MPI.ANY_TAG, status)
        tag = status.Get_tag()
        self.handlers[tag]()


    # solve problem and send any results
    def __solveProblem(self):
        try:

            self.__trySolveProblem()

        # no solution found
        except SolverError:
            self.__sendNoSolution()

    # solve problem and send successful results
    def __trySolveProblem(self):
        solver = Solver(self.problem)
        solution = solver.solve()

        # integral solution found
        if solution.isIntegral():
            self.__sendIntegral(solution)

        # decimal solution found
        else:
            finalDict = solver.dictionary
            self.__sendDecimal(solution, finalDict)


    # send non-result and wait for work
    def __sendNoSolution(self):
        self.comm.isend(0, dest=MASTER_RANK, tag=NO_SOL_TAG)
        self.problem = None


    # send solution and wait for work
    def __sendIntegral(self, solution):
        self.comm.isend(solution, dest=MASTER_RANK, tag=INT_SOL_TAG)
        self.problem = None


    # send intermediate solution and check pruning
    def __sendDecimal(self, solution, finalDict):
        self.comm.isend(solution, dest=MASTER_RANK, tag=DEC_SOL_TAG)
        proceed = self.comm.recv(source=MASTER_RANK, tag=PROCEED_TAG)
        self.problem = None

        # branched not pruned
        if proceed:
            problem = finalDict.toProblem()
            
            # convert dual
            if problem.dual:
                problem = problem.getDual()

            self.__branch(problem)


    # branch problem sending one to master
    def __branch(self, problem):
        brancher = Brancher(problem)
        lower, upper = brancher.getFirstBranches()
        self.comm.isend(upper, dest=MASTER_RANK, tag=PROBLEM_TAG)
        self.problem = lower


    # recieve new problem for solving
    def __receiveProblem(self):
        self.problem = self.comm.recv(source=MASTER_RANK, tag=PROBLEM_TAG)


    # receive kill message and change status
    def __receiveKill(self):
        self.comm.recv(source=MASTER_RANK, tag=KILL_TAG)
        self.working = False

    # create dictionary of messages handlers
    def __createMessageHandlers(self):
        self.handlers = {}
        self.handlers[PROBLEM_TAG] = self.__receiveProblem;
        self.handlers[KILL_TAG] = self.__receiveKill;
