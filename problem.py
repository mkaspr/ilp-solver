#!/usr/bin/env python

class Problem:

    dual = False

    A = None
    b = None
    c = None
    z = 0.0

    base = None
    nonBase = None

    def getDual(self):
        dual = Problem()
        dual.dual = not self.dual
        dual.A = -self.A.transpose()
        dual.b = -self.c
        dual.c = -self.b
        dual.z = -self.z
        dual.base = self.nonBase[:]
        dual.nonBase = self.base[:]
        return dual

    def copy(self):
        copy = Problem()
        copy.dual = self.dual
        copy.A = self.A.copy()
        copy.b = self.b.copy()
        copy.c = self.c.copy()
        copy.z = self.z
        copy.base = self.base[:]
        copy.nonBase = self.nonBase[:]
        return copy

    def __str__(self):
        s  = "A:\n"
        s += str(self.A) + "\n"
        s += "b:\n"
        s += str(self.b) + "\n"
        s += "c:\n"
        s += str(self.c) + "\n"
        s += "z: " + str(self.z) + "\n"
        s += "base: " + str(self.base) + "\n"
        s += "nonBase: " + str(self.nonBase) + "\n"
        s += "dual: " + str(self.dual) + "\n"
        return s

    def toAmpl(self):
        s = ""

        # print variables
        for i in xrange(len(self.c)):
            s += "var x" + str(i) + " integer >= 0;\n"

        s += "\n"
        s += "maximize objVal: 0"

        # print obj function
        for i in xrange(len(self.c)):
            s += " + " + str(self.c[i, 0]) + " * x" + str(i)

        s += ";\n\n"

        # print constraints
        for i in xrange(len(self.b)):
            s += "c" + str(i) + ": 0"

            for j in xrange(len(self.c)):
                s += " + " + str(self.A[i, j]) + " * x" + str(j)

            s += " <= " + str(self.b[i, 0]) + ";\n"

        # print solve
        s += "\n"
        s += "solve;\n"
        s += "display objVal"

        for i in xrange(len(self.c)):
            s += ", x" + str(i)

        s += ";\n"
        s += "end;\n"
        return s
