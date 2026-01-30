def bits_to_flip_generator(logQ: int, logDelta: int, bit_per_coeff: int):
    res = []

    M = bit_per_coeff - 1

    def clamp(v: int) -> int:
        return min(v, M)

    def push_unique(v: int):
        v = clamp(v)
        if v not in res:
            res.append(v)

    push_unique(0)
    push_unique(logDelta // 4)

    push_unique(logDelta // 2)
    if logDelta > 0:
        push_unique(logDelta - 1)

    if logQ>=120:
        push_unique((logDelta + logQ) // 6);
        push_unique((logDelta + logQ) // 4);
        push_unique((logDelta + logQ) // 3);
        push_unique(logQ-logDelta);
    push_unique(logDelta)
    push_unique((logDelta + logQ) // 2)

    if logQ > 0:
        push_unique(logQ - 1)
    push_unique(logQ)

    push_unique((logQ + M) // 2)
    push_unique(M)

    return res
