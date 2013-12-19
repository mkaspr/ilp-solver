#!/usr/bin/env python

from mpi_ilp import *
from mpi4py import MPI
from solver import Solver
from brancher import Brancher
from solution import Solution
from solver import SolverError

INT = 0
DEC = 1
INF = 2
TOT = 3
PRN = 4

class Serial:

    origProblem = None
    pendingProblems = []
    bestSolution = None
    counts = [0] * 5

    # creates master with given number of workers
    def __init__(self, problem):
        print problem.toAmpl()
        self.origProblem = problem
        self.bestSolution = Solution()
        self.bestSolution.optValue = float("-inf")


    def solve(self):
        # initalize problem list
        self.__solveRelaxed(self.origProblem)

        # loop until all branches explored
        while not self.__finished():
            self.__sendProblems()

            if self.counts[TOT] % 100 == 0:
                print "Branches " + str(self.counts[TOT]) + " (" + \
                      "i " + str(self.counts[INT]) + ", " + \
                      "d " + str(self.counts[DEC]) + ", " + \
                      "u " + str(self.counts[INF]) + ", " + \
                      "p " + str(self.counts[PRN]) + ") " + \
                      "jobs left: " + str(len(self.pendingProblems))


        # finalize and return
        return self.__getFinalSolution()


    # solves first relaxed LP problem
    def __solveRelaxed(self, problem):
        try:

            self.__trySolveRelaxed(problem)

        # kill workers on error before exiting
        except Exception as error:
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
    
    # send all available problems to ready workers
    def __sendProblems(self):
        # get number of problems to send
        sendCount = len(self.pendingProblems)

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
            self.__solveProblem(problem)
            break


    # solve problem and send any results
    def __solveProblem(self, problem):
        try:

            self.__trySolveProblem(problem)

        # no solution found
        except SolverError:
            pass


    # solve problem and send successful results
    def __trySolveProblem(self, problem):
        solver = Solver(problem)
        solution = solver.solve()

        # integral solution found
        if solution.isIntegral():
            self.__receiveIntegralSolution(solution)

        # decimal solution found
        else:
            finalDict = solver.dictionary
            self.__sendDecimal(solution, finalDict)


    # send intermediate solution and check pruning
    def __sendDecimal(self, solution, finalDict):
        proceed = self.__receiveDecimalSolution(solution)

        # branched not pruned
        if proceed:
            problem = finalDict.toProblem()
            
            # convert dual
            if problem.dual:
                problem = problem.getDual()

            self.__branch(problem)


    # adds single branch pair to problem list
    def __branch(self, problem):
        brancher = Brancher(problem)
        branches = brancher.getFirstBranches()
        self.pendingProblems += branches


    # indicates if solver is finished
    def __finished(self):
        # done when no pending problems or active workers
        return len(self.pendingProblems) == 0


    # check for any messages from workers
    def __probeMessages(self):
        result = False

        # # blocking probe for message
        # for i in xrange(20000):
        #     status = MPI.Status()
        #     result = self.comm.Iprobe(MPI.ANY_SOURCE, MPI.ANY_TAG, status)

        #     if result:
        #         break

        # if not result:
        #     self.workerCount = len(self.inactiveWorkers)
        #     return

        status = MPI.Status()
        self.comm.Probe(MPI.ANY_SOURCE, MPI.ANY_TAG, status)

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


    def __receiveIntegralSolution(self, solution):
        # better solution found
        if self.__isBetterSolution(solution.optValue):
            self.bestSolution = solution

        self.counts[INT] += 1
        self.counts[TOT] += 1

    def __receiveDecimalSolution(self, solution):
        self.counts[DEC] += 1
        self.counts[TOT] += 1

        # prunning needed
        if not self.__isBetterSolution(solution.optValue):
            self.counts[PRN] += 1
            return False

        # cannot prune
        else:
            return True

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
