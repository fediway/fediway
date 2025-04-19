
from functools import reduce
import operator

def flatten(arr):
    return reduce(operator.add, arr)