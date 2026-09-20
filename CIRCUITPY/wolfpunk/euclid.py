# Euclidean rhythm generator (Bresenham-line style): spreads `hits` triggers
# as evenly as possible across `steps` slots. Simpler than the classic
# recursive Bjorklund construction and gives the same practical result -
# evenly-spaced hits rather than clumped ones, which is what makes a
# Euclidean pattern feel intentional instead of random.


def euclidean_rhythm(steps, hits):
    if hits <= 0:
        return [False] * steps
    if hits >= steps:
        return [True] * steps
    pattern = [False] * steps
    bucket = 0
    for i in range(steps):
        bucket += hits
        if bucket >= steps:
            bucket -= steps
            pattern[i] = True
    return pattern
