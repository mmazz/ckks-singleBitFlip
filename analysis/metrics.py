
def bit_region(bit, logDelta, logQ, M):
    if bit <= logDelta // 4:
        return "A"   # ruido
    if bit <= logDelta:
        return "B"   # transición
    if bit <= (logDelta + logQ) // 2:
        return "C"   # mensaje
    if bit <= logQ:
        return "D"   # borde módulo
    return "E"       # overflow


