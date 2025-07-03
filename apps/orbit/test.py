import math

def run(v, a, b, g, t):
    for _ in range(1000):
        v = v * (1 - ((1 - math.exp(-a * t)) * b))
        v += (1 - v) * g
    return v

print(run(0, 0.0001, 1.0, 0.05, 60))