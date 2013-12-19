#!/usr/bin/env python

from dictionary import Dictionary

class SolverError(Exception):
    pass

class Solver:

    problem = None
    dictionary = None

    def __init__(self, problem):
        self.problem = problem
        self.dictionary = Dictionary(problem)

    def solve(self):
        # pivot until solution found
        while self.dictionary.canPivot():
            self.dictionary.pivot()

        # unbounded problem
        if self.dictionary.unbounded:
            raise SolverError("problem is unbounded")

        return self.__getSolution()

    # returns solution only in primal form
    def __getSolution(self):
        dic = self.dictionary

        # convert dual solutions
        if self.problem.dual:
            dual = dic.toProblem()
            primal = dual.getDual()
            dic = Dictionary(primal)
            
        return dic.getSolution()
