import numpy as np
from typing import List
np.set_printoptions(precision=3, suppress=True)

def FFTSpecialInv_numpy(vals: List[complex], cyclOrder: int) -> List[complex]:

    n = cyclOrder // 4
    if len(vals) != n:
        raise ValueError(f"FFTSpecialInv_numpy: expected {n} values, got {len(vals)}")

    a = np.array(vals, dtype=np.complex128)
    p = np.fft.ifft(a)

    # Post-twist: p[j] *= xi^{-j}
    xi_inv = np.exp(-2j * np.pi / cyclOrder)
    p     *= xi_inv ** np.arange(n)

    for i in range(n):
        vals[i] = complex(p[i])
    return vals

def FFTSpecial_numpy(vals: List[complex], cyclOrder: int) -> List[complex]:

    n = cyclOrder // 4
    if len(vals) != n:
        raise ValueError(f"FFTSpecial_numpy: expected {n} values, got {len(vals)}")

    p = np.array(vals, dtype=np.complex128)

    # Pre-twist: q[j] = p[j] * xi^j
    xi = np.exp(2j * np.pi / cyclOrder)
    q  = p * (xi ** np.arange(n))

    result = np.fft.fft(q)
    for i in range(n):
        vals[i] = complex(result[i])
    return vals


def ckks_encode(slots, cyclOrder, scale):
    return FFTSpecialInv_numpy(slots, cyclOrder) * scale

def ckks_decode(coeffs, cyclOrder, scale):
    return FFTSpecial_numpy(coeffs / scale, cyclOrder)

def Conjugate(vec):
    n = len(vec)
    result = np.zeros(n, dtype=complex)

    for i in range(1, n):
        z = vec[n - i]
        result[i] = complex(-z.imag, -z.real)

    z0 = vec[0]
    result[0] = complex(z0.real, -z0.imag)

    return result



N = 8  # debe ser potencia de 2
M = 2*N
scale = 2**10

slots = np.array([complex(i, i*0.5) for i in range(N//2)])
print("Input slots:")
print(slots)
print()

encoded = ckks_encode(slots, M, scale)

print("Encoded (FFT domain):")
print(encoded)
print()


inv_encoded = Conjugate(encoded)

print("mInv(encoded):")
print(inv_encoded)
print()

# -----------------------------
#  Operación m(x) - m(1/x)
# -----------------------------
diff = encoded - inv_encoded

print("Difference (m(x) - m(1/x)):")
print(diff)
print()

decoded_original = ckks_decode(encoded, M, scale)
decoded_diff = ckks_decode(diff, M, scale)

print("Decoded original:")
print(decoded_original)
print()

print("Decoded difference:")
print(decoded_diff)
print()


print("Imag part of original slots * 2i (referencia teórica):")
print(2j * np.imag(slots))
