from z3 import *

s = Solver()
ret = BitVecVal(0, 32)
seed = BitVec('seed', 32)
ret = 25214903917 * seed + 11
ret = ret & 0xFFFFFFFFFFFF
s.add(ret == 1364650861)  # This comment shows possible seeds: 1364650861, 1208101748

if s.check() == sat:
    model = s.model()
    print(model[seed])
