#!/usr/bin/env python

import math

MAX_ERROR = 1E-8

# indicates if value is integral
def isIntegral(value):
    lower = math.floor(value - MAX_ERROR)
    upper = math.floor(value + MAX_ERROR)
    return lower != upper

def clean(value):
    # assign integer if close
    if isIntegral(value):
        value = int(math.floor(value - MAX_ERROR) + 1)

    return value

class Solution:

    optValue = None
    optSolution = None

    # indicates if solution is integral
    def isIntegral(self):
        # check each decision variable
        for value in self.optSolution:

            # non integral value
            if not isIntegral(value):
                return False

        # all integral
        return True

    # return string representing solution
    def __str__(self):
        s  = "  z: " + str(clean(self.optValue)) + "\n"

        # print each decision variable except last
        for i in xrange(0, len(self.optSolution) - 1):
            s += "{0: >3}".format("x" + str(i)) + ": "
            s += str(clean(self.optSolution[i, 0])) + "\n"

        # print last decision variable
        s += "{0: >3}".format("x" + str(i + 1)) + ": "
        s += str(clean(self.optSolution[i + 1, 0]))
        return s
