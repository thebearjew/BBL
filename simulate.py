#!/usr/bin/env python

"""
simulate.py: Imports the BBL module and uses the commands therein 
to run a BBL simulation on location data of Chicago Food Trucks
Returns an element of g(E_{ia})
"""

__author__ = 'Eliot Abrams'
__copyright__ = "Copyright (C) 2015 Eliot Abrams"
__license__ = "MIT"
__version__ = "1.0.0"
__email__ = "eabrams@uchicago.edu"
__status__ = "Production"


"""
# Run BBL script to setup environment and declare functions
import os
os.chdir('/Users/eliotabrams/Desktop/BBL')
"""

# Import packages and force re-creation of module
import BBL
import ast
import multiprocessing as mp

reload(BBL)
from BBL import *

##############################
##         Simulate         ##
##############################

# Read in data
states = pd.read_csv('states.csv', index_col=0, converters={'State': ast.literal_eval})
probabilities = pd.read_csv('probabilities.csv', index_col=0)
truck_types = pd.read_csv('final_truck_types.csv', index_col=0)
state_variables = pd.read_csv('state_variables.csv', index_col=0)
state_variables = state_variables['0'].tolist()


# Estimate the coefficients and their standard errors
# Periods controls the number of days the simulation runs for.
# N controls the number of simluated paths that go into creating
# the value function. num_draws controls the number of inequalities
# used to identify the parameters.
# For the laws of large numbers in the math to work, I probably need
# periods = 700+, N = 100+, num_draws = 100+, and the xrange to be 100+.
# But need much more computing power to run.
# Try setting xrange = 1, periods = 10, N=1, and num_draws=20 to begin.

# Stage 1
g = build_g(states=states, 
            probabilities=probabilities, 
            periods=40, 
            discount=.99,
            state_variables=state_variables,
            N=5,
            truck_types=truck_types, 
            num_draws=5)

g = g.reset_index()
print g.g[0]
print g.g[1] 
print g.g[2] 
print g.g[3] 
print g.g[4] 


