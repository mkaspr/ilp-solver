# ILP Solver
A parallel ILP Solver implemented in Python with MPI

## Instructions
The following outlines how to setup and run the program.

### Setup
To run this application you will need the following Python modules:

- mpi4py
- numpy
- scipy

### Execution
Once you have downloaded the source and installed the required modules, you can
try running an example on a random ILP problem using the following command from
within the project directory:

`make run M=<int> N=<int> S=<int> P=<int>`

The Makefile arguments are explained below:

- M: number of constraints in the generated ILP problem
- N: number of decision variables in the generated ILP problem
- S: seed for random number generator used to create the problem
- P: number of MPI processes used to solve the problem

### Results
When the program is executed, it first creates a random ILP problem. This
problem is then printed to the console in the format of an ampl file. This
serves as a convenience for checking results with GLPK.

    $ make run M=4 N=4 S=2 P=4

    var x0 integer >= 0;
    var x1 integer >= 0;
    var x2 integer >= 0;
    var x3 integer >= 0;

    maximize objVal: 0 + -2 * x0 + 8 * x1 + 9 * x2 + 4 * x3;

    c0: 0 + -4 * x0 + 0 * x1 + 6 * x2 + -4 * x3 <= 5;
    c1: 0 + 2 * x0 + 8 * x1 + 2 * x2 + 0 * x3 <= 3;
    c2: 0 + -3 * x0 + 0 * x1 + 0 * x2 + 2 * x3 <= 5;
    c3: 0 + 10 * x0 + -5 * x1 + -6 * x2 + 0 * x3 <= 2;

    solve;
    display objVal, x0, x1, x2, x3;
    end;

On larger ILP problems, the solver will periodically print out its
current progress as shown below:

    Branches 600 (i 3, d 422, u 175, p 63) jobs left: 138
    Branches 700 (i 3, d 492, u 205, p 79) jobs left: 154
    Branches 800 (i 3, d 563, u 234, p 91) jobs left: 176
    Branches 900 (i 3, d 623, u 274, p 102) jobs left: 177
    Branches 1000 (i 3, d 686, u 311, p 108) jobs left: 191
    Branches 1100 (i 3, d 746, u 351, p 116) jobs left: 193

Descriptions for each field is described below:
    
    Branches: number of LP problems solved
    i: number of integer solutions found
    d: number of decimal solutions found
    u: number of infeasible solutions found
    p: number of branches pruned
    jobs left: number of branches left to be explored

Finally, when the final solution is found, the results will be displayed as
shown below:

    z: 17
    x0: 0
    x1: 0
    x2: 1
    x3: 2
    RUNTIME: 0.06

It is also possible that no feasible solution is found. If this is the case,
the program will simply display the words `No solution found`.

### Problems of Interest
To avoid hunting for a randomly generated problem that's feasible, here are a
few problems of interest, known to have feasible solutions:

    $ make run M=4 N=4 S=2    (runtime: very short)
    $ make run M=8 N=8 S=19   (runtime: short)
    $ make run M=10 N=10 S=1  (runtime: medium)
    $ make run M=12 N=12 S=5  (runtime: long)
    $ make run M=15 N=15 S=15 (runtime: very long)

### User-Specified Problems
At the moment, the program only solves randomly generated problems.  However,
if you wanted to modify the code to solve a user-specified problem, you would
need to modify the `getProblem` function found in `ilp_solver.py`.  Here you
would need to construct your own `Problem` object manually. A problem object
consist of the following fields:

    A (numpy.matrix) : MxN matrix of constraint coefficients
    b (numpy.matrix) : column vector of length M of constraint constants
    c (numpy.matrix) : column vector of length N of decision variable coefficients
    z (double) : optimal solution base value
    base (list) : list of length N of indices of basic variables
    nonBase (list) : list of length M of indices of non-basic varaibles
    dual (bool) : indicates whether this problem is a dual form of the original problem

Some of the seemingly superflous fields are used in solving an updated version
of the original problem as the solver branches. An original problem should use
the following default values:

    z : 0.0
    base : range(0, N)
    nonBase : range(N, M + N)
    dual : False

## Implementation
As previously mentioned, this ILP solver was implemented in Python using MPI.
The general approach was toe create a Master process, which is in charge of
issuing LP problems to Worker processes and updating the current best integer
solution. Each Worker then solves the relaxed LP problem and notifies the
Master of the results.  If a non-integral solution was found, the worker will
branch the LP problem on an non-integral value, send one branch back to the
Master, and begins solving the other branch.  A simplified diagram of class
dependencies is shown below:

![Alt text](https://raw.github.com/mkaspr/ilp-solver/master/images/class_diagram.png)

## Evaluation
- ran on Janus
- branch runtimes
- results description
- image

- problem runtimes
- results description
- image

![Alt text](https://raw.github.com/mkaspr/ilp-solver/master/images/speedup.png)

## Future Work
The following briefly describes current problems and areas where the program
could be improved:

##### Pickling Error
This program currently exhibits a problem when running with more than 20 MPI
processes. During the first few iterations, on average 5% of the processes
fail, due to an Python pickling error. This may alter the final solution, if one
of the failed Workers was processing a branch with an optimal solution. This
problem should be solved by moving away from the `mpy4py` pickling
communication functions.

##### Improve ETA File Usage
The ETA file used inside `solver.py` could be altered to improve performance.
Optinally, the GLPK LP solver could be used instead of the current Python
implementation.

##### Branch-and-Cut
Using Branch-and-Cut instead of Branch-and-Bound would further reduce MPI
communicatoin overhead, as Workers would search a given branch longer, without
needing to send results back to the master after every solution.

##### Broadcasting Integer Solutions
Currently, each Worker sends the results of non-integral solutions back to the
Master, so the Master can inform the Worker if the that branch can be pruned.
To reduce this communication, the Master could broadcast each new integer
solution to each Worker, as these are relatively rare, so each worker can make
the decision to prune themselves.

##### Reading AMPL Input Files
As mentioned above, this program currently works on randomly generated problems.
Providing an ampl file parser that creates `Problem` objects would beneficial
for solving actual problems.
