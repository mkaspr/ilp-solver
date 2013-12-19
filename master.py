#!/usr/bin/env python

from mpi_ilp import *
from mpi4py import MPI
from solver import Solver
from brancher import Brancher
from solution import Solution

INT = 0
DEC = 1
INF = 2
TOT = 3
PRN = 4

class Master:

    origProblem = None
    pendingProblems = []
    inactiveWorkers = []
    workerCount = 0
    bestSolution = None
    handlers = None
    comm = None
    counts = [0] * 5

    # creates master with given number of workers
    def __init__(self, problem, workerCount):
        print problem.toAmpl()
        self.origProblem = problem
        self.workerCount = workerCount
        self.inactiveWorkers = range(1, workerCount + 1)
        self.comm = MPI.COMM_WORLD
        self.__createMessageHandlers()
        self.bestSolution = Solution()
        self.bestSolution.optValue = float("-inf")


    def solve(self):
        # initalize problem list
        self.__solveRelaxed(self.origProblem)

        # loop until all branches explored
        while not self.__finished():
            self.__sendProblems()

            # potentially can receive message from worker
            if len(self.inactiveWorkers) < self.workerCount:
                self.__probeMessages()

            if self.counts[TOT] % 100 == 0:
                print "Branches " + str(self.counts[TOT]) + " (" + \
                      "i " + str(self.counts[INT]) + ", " + \
                      "d " + str(self.counts[DEC]) + ", " + \
                      "u " + str(self.counts[INF]) + ", " + \
                      "p " + str(self.counts[PRN]) + ") " + \
                      "jobs left: " + str(len(self.pendingProblems))


        # finalize and return
        self.__killWorkers()
        return self.__getFinalSolution()


    # solves first relaxed LP problem
    def __solveRelaxed(self, problem):
        try:

            self.__trySolveRelaxed(problem)

        # kill workers on error before exiting
        except Exception as error:
            self.__killWorkers()
            raise error

    # attempts to solve first relaxed LP problem
    def __trySolveRelaxed(self, problem):
        solver = Solver(problem)
        solution = solver.solve()

        # integral solution found
        if solution.isIntegral():
            self.bestSolution = solution

        # decimal solution found
        else:
            finalDict = solver.dictionary
            problem = finalDict.toProblem()
            self.__branch(problem)


    # adds single branch pair to problem list
    def __branch(self, problem):
        brancher = Brancher(problem)
        branches = brancher.getFirstBranches()
        self.pendingProblems += branches


    # indicates if solver is finished
    def __finished(self):
        # done when no pending problems or active workers
        return len(self.pendingProblems) == 0 and \
               len(self.inactiveWorkers) == self.workerCount

    
    # send all available problems to ready workers
    def __sendProblems(self):
        # get number of problems to send
        readyProblemCount = len(self.pendingProblems)
        readyWorkerCount = len(self.inactiveWorkers)
        sendCount = min(readyProblemCount, readyWorkerCount)

        # send each problem to worker
        for i in xrange(sendCount):
            problem = self.pendingProblems.pop(0)
            optValue = problem.z

            # negate dual values
            if problem.dual:
                optValue *= -1;

            # problem can now be pruned
            if not self.__isBetterSolution(optValue):
                self.counts[PRN] += 1
                continue

            # mark worker as active
            worker = self.inactiveWorkers.pop(0)
            self.comm.isend(problem, dest=worker, tag=PROBLEM_TAG)

    # check for any messages from workers
    def __probeMessages(self):
        result = False

        # blocking probe for message
        for i in xrange(20000):
            status = MPI.Status()
            result = self.comm.Iprobe(MPI.ANY_SOURCE, MPI.ANY_TAG, status)

            if result:
                break

        if not result:
            self.workerCount = len(self.inactiveWorkers)
            return

        #status = MPI.Status()
        #self.comm.Probe(MPI.ANY_SOURCE, MPI.ANY_TAG, status)

        # send to handler based on tag
        tag = status.Get_tag()
        rank = status.Get_source()
        self.handlers[tag](rank)


    # sends kill message to all workers
    def __killWorkers(self):
        requests = [MPI.REQUEST_NULL] * self.workerCount

        # send kill message to each worker
        for worker in xrange(1, self.workerCount + 1):
            index = worker - 1
            requests[index] = self.comm.isend(0, dest=worker, tag=KILL_TAG)

        # wait for all workers to receive
        MPI.Request.Waitall(requests)


    def __getFinalSolution(self):
        solution = self.bestSolution
        varCount = len(self.origProblem.c)
        varValues = solution.optSolution
        solution.optSolution = varValues[0:varCount]
        return solution


    def __receiveNoSolution(self, rank):
        self.comm.recv(source=rank, tag=NO_SOL_TAG)
        self.inactiveWorkers.append(rank)

        self.counts[INF] += 1
        self.counts[TOT] += 1


    def __receiveIntegralSolution(self, rank):
        solution = self.comm.recv(source=rank, tag=INT_SOL_TAG)

        # better solution found
        if self.__isBetterSolution(solution.optValue):
            self.bestSolution = solution

        # worker is inactive regardless
        self.inactiveWorkers.append(rank)

        self.counts[INT] += 1
        self.counts[TOT] += 1

    def __receiveDecimalSolution(self, rank):
        solution = self.comm.recv(source=rank, tag=DEC_SOL_TAG)

        # prunning needed
        if not self.__isBetterSolution(solution.optValue):
            self.comm.isend(False, rank, PROCEED_TAG)
            self.inactiveWorkers.append(rank)
            self.counts[PRN] += 1

        # cannot prune
        else:
            self.comm.isend(True, rank, PROCEED_TAG)

        self.counts[DEC] += 1
        self.counts[TOT] += 1

    def __receiveProblem(self, rank):
        problem = self.comm.recv(source=rank, tag=PROBLEM_TAG)
        self.pendingProblems.append(problem)


    # indicates if value is a better solution
    def __isBetterSolution(self, value):
        return value > self.bestSolution.optValue

    
    def __createMessageHandlers(self):
        self.handlers = {}
        self.handlers[PROBLEM_TAG] = self.__receiveProblem;
        self.handlers[INT_SOL_TAG] = self.__receiveIntegralSolution;
        self.handlers[DEC_SOL_TAG] = self.__receiveDecimalSolution;
        self.handlers[NO_SOL_TAG] = self.__receiveNoSolution;
