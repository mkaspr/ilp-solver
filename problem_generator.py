#!/usr/bin/env python

import numpy as np
import numpy.random as npr
from problem import Problem

class ProblemGenerator:

    # generate random ILP problem likely to be solveable
    def generate(self, rows, cols, seed=None):
        npr.seed(seed)

        problem = Problem()
        problem.dual = False
        problem.A = self.__getMatrixA(rows, cols)
        problem.b = self.__getVectorB(rows)
        problem.c = self.__getVectorC(cols)
        problem.base = range(cols, rows + cols)
        problem.nonBase = range(0, cols)
        problem.decVarCount = cols

        return problem

    # generate random constraint coefficient matrix
    def __getMatrixA(self, rows, cols):
        # ensure at least 1/3 positive values in each row
        data = npr.randint(-10, 10, [rows, cols])
        zeros = npr.randint(0, 3, [rows, cols]) 
        data = data * zeros
        return np.matrix(data)

    # generate random constraint value vector
    def __getVectorB(self, length):
        # ensure always positive values
        data = npr.randint(1, 10, [length, 1])
        return np.matrix(data)

    # generator random objective coefficient vector
    def __getVectorC(self, length):
        # ensure at least 1/3 positive values
        data = npr.randint(-10, 10, [length, 1])
        posCount = np.ceil(length / 3)
        data[:posCount, 0] = npr.randint(0, 10, posCount) 
        npr.shuffle(data)
        return np.matrix(data)
