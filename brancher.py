#!/usr/bin/env python

import math
import numpy as np
import solution

class BranchError(Exception):
    pass

class Brancher:

    problem = None

    def __init__(self, problem):
        self.problem = problem

    # returns first tuple of upper and lower branches
    def getFirstBranches(self):
        minIndex = float("inf")

        # search all basis values
        for i in xrange(0, len(self.problem.b)):
            # non-integral value
            if self.canBranch(i):

                if self.problem.base[i] < minIndex:
                    minIndex = i

        return self.getBranches(minIndex)

    # indicates if problem can be branched on given variable index
    def canBranch(self, index):
        value = self.problem.b[index]
        return not solution.isIntegral(value)

    # returns a tuple of the lower and upper branches
    def getBranches(self, index):
        Ai = self.problem.A[index, :]
        b  = self.problem.b[index][0, 0]
        m, n = self.problem.A.shape
        
        # get lower constraint
        bhat = np.matrix([[math.floor(b) - b]])
        lower = self.__getBranch(-Ai, bhat)

        # get upper constraint
        bhat = np.matrix([[b - math.ceil(b)]])
        upper = self.__getBranch(Ai, bhat)

        return [lower, upper]

    # returns one half of a binary branch
    def __getBranch(self, Ai, b):
        m, n = self.problem.A.shape
        problem = self.problem.copy()
        problem.A = np.append(problem.A, Ai, axis=0)
        problem.b = np.append(problem.b, b, axis=0)
        problem.base.append(m + n)
        return problem.getDual()
