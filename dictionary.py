

import numpy as np
import scipy as sp
import scipy.linalg as spl
import scipy.sparse as sps
import scipy.sparse.linalg as spsl
from problem import Problem
from solution import Solution

from numpy import asarray, empty, where, squeeze, prod
from scipy.sparse import isspmatrix_csc, isspmatrix_csr, isspmatrix, \
                SparseEfficiencyWarning, csc_matrix

class PivotError(Exception):
    pass

class Dictionary:

    MAX_ERROR = 1E-10
    MAX_ETA_FILE_SIZE = 30

    problem = None
    A = None
    b = None
    c = None
    z = None
    m = None
    n = None
    x = None
    base = None
    nonBase = None
    etaFile = None
    LU = None
    final = False
    unbounded = False

    def __init__(self, problem):
        self.problem = problem
        self.__initialize()

    def getSolution(self):
        solution = Solution()
        solution.optValue, x = self.__getObjectiveRow()
        solution.optSolution = self.__getDecisionVars()
        return solution

    def toProblem(self):
        # get current state
        A = self.__getMatrixA()
        b = self.__forwardSolve(self.b)
        objVal, c = self.__getObjectiveRow()
        dual = self.problem.dual

        # build problem
        problem = Problem()
        problem.dual = dual
        problem.A = A
        problem.b = b
        problem.c = c.transpose()
        problem.z = objVal
        problem.base = self.base[:]
        problem.nonBase = self.nonBase[:]

        return problem

    def canPivot(self):
        return not self.final and \
               not self.unbounded

    def pivot(self):
        try:
            self.__tryPivot()
        except PivotError:
            pass

    def __tryPivot(self):
        objVal, c = self.__getObjectiveRow()
        enterIndex = self.__getEnterIndex(c)
        colIndex = self.nonBase[enterIndex]
        enterCol = self.__getColumnA(colIndex)
        leaveIndex = self.__getLeaveIndex(enterCol)
        self.__swapVariables(enterIndex, leaveIndex)
        self.__updateEtaFile(enterCol, leaveIndex)

    def __getMatrixA(self):
        zeros = np.zeros((self.m, self.n))
        A = np.matrix(zeros)
        
        # add each column to matrix
        for index in xrange(0, self.n):
            col = self.nonBase[index]
            val = self.__getColumnA(col)
            A[:, index] = val

        return -A

    def __getDecisionVars(self):
        bhat = self.__forwardSolve(self.b)
        b = np.zeros((self.x, 1))
        b[self.base, :] = bhat
        return b[0:self.n, :]

    def __getObjectiveRow(self):
        # split matrix on basis
        Ai = self.A[:, self.nonBase]
        cb = self.c[self.base, :].transpose()
        cb = self.c[self.base, :]#.transpose()
        ci = self.c[self.nonBase, :].transpose()

        # compute objective row
        pi = self.__reverseSolve(cb)
        objVal = self.__getObjectiveValue(pi)
        chat = ci - pi * Ai
        return [objVal, chat]

    def __getObjectiveValue(self, pi):
        base = self.problem.z
        value = pi * self.b
        value = value[0, 0]
        return value + base

    def __getEnterIndex(self, c):
        # no valid entering variable
        if c.max() < self.MAX_ERROR:
            self.final = True
            raise PivotError("dictionary is final")

        return c.argmax()

    def __getColumnA(self, index):
        col = -self.A[:, index]
        return self.__forwardSolve(col)

    def __getLeaveIndex(self, enterCol):
        # get basis values
        b = self.__forwardSolve(self.b)

        # init search results
        leaveLimit = np.inf
        leaveIndex = -1 

        # analyze all rows
        for i in xrange(self.m):
        
            # possible leave variable row
            if enterCol[i] < 0:
                limit = -b[i] / enterCol[i]
        
                # better leave variable found
                if limit < leaveLimit - self.MAX_ERROR or \
                        (limit >= leaveLimit - self.MAX_ERROR and \
                         limit <= leaveLimit + self.MAX_ERROR and \
                         self.base[i] < self.base[leaveIndex]):

                    leaveIndex = i
                    leaveLimit = limit

        # no valid leave variable
        if leaveIndex == -1:
            self.unbounded = True
            raise PivotError("problem is unbounded")

        return leaveIndex

    def __swapVariables(self, enterIndex, leaveIndex):
        enterVar = self.nonBase[enterIndex]
        leaveVar = self.base[leaveIndex]
        self.base[leaveIndex] = enterVar
        self.nonBase[enterIndex] = leaveVar

    def __updateEtaFile(self, enterCol, leaveIndex):
        E = sps.lil_matrix((self.m, self.m))
        E.setdiag(np.ones(self.m))
        E[:, leaveIndex] = -enterCol
        self.etaFile.append(E.tocsc())

        # refactorization needed
        if len(self.etaFile) > self.MAX_ETA_FILE_SIZE:
            self.__refactorEtaFile()

    def __refactorEtaFile(self):
        R = sps.identity(self.m)

        # multiply each eta-matrix
        for eta in self.etaFile:
            R = R * eta

        # decompose matrix
        R = R.todense()
        P, L, U = spl.lu(R)
        self.LU = [L, U]
        self.etaFile = []

    def __forwardSolve(self, b):
        # use LU decomposition first
        b = spl.solve(self.LU[0], b)
        b = spl.solve(self.LU[1], b)
        
        # eta-file usage needed
        if len(self.etaFile):

            # solve with each eta-file
            for eta in self.etaFile:
                b = spsl.spsolve(eta, b)

            # always format as column vector
            b = np.matrix(b).transpose()

        return np.matrix(b)

    def __reverseSolve(self, b):
        # solve for each subsequent eta file
        if len(self.etaFile) > 0:
            b = sps.csc_matrix(b)

            # solve for each eat matrix
            for eta in reversed(self.etaFile):
                b = spsl.spsolve(eta.transpose(), b.transpose())

            b = np.matrix(b).transpose()

        # solve for the initial LU decomposition
        b = spl.solve(self.LU[1].transpose(), b)
        b = spl.solve(self.LU[0].transpose(), b)
        return np.matrix(b).transpose()

    def __initialize(self):
        # get dimensions
        self.m, self.n = self.problem.A.shape
        self.x = self.m + self.n

        # initialize basis
        self.base = self.problem.base
        self.nonBase = self.problem.nonBase

        # add slack variables
        self.A = np.hstack((self.problem.A, np.eye(self.m)))
        self.A[:, self.nonBase + self.base] = self.A.copy()
        self.b = self.problem.b
        self.c = np.matrix(np.zeros((self.x, 1)))
        self.c[self.nonBase, :] = self.problem.c

        # initialize eta-file
        I = np.eye(self.m)
        P, L, U = spl.lu(I)
        self.LU = [L, U]
        self.etaFile = []
