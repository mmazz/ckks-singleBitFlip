import numpy as np
from numpy.polynomial import Polynomial

def rootOfUnity(M, k, cs=3):
    root = np.exp(1j*2*np.pi*(2*k+1)/M)
    return np.round(root.real, cs) + 1j * np.round(root.imag, cs)

def rootOfUnityPow(M, k, i, cs=3):
    root = rootOfUnity(M, k, cs=3)**i
    return np.round(root.real, cs) + 1j * np.round(root.imag, cs)

def conjugate(vec):
    n = len(vec)
    result = np.zeros(n, dtype=np.complex128)

    for i in range(1, n):
        result[i] = complex(
            -vec[n - i].imag,
            -vec[n - i].real
        )

    result[0] = complex(
        vec[0].real,
        -vec[0].imag
    )

    return result

M = 32
N = M//2
k = 0
x = rootOfUnity(M, k, cs=3)
coeff = [1+2j, 3-1j, 2, 1+.5j]

p = Polynomial(coeff)
print("Random polynomial")
print(p)

conjCoeff = conjugate(coeff)
p2 = Polynomial(conjCoeff)
print("Random polynomial with the permutation of coeff like cojugation")
print(p2)
print()
print("Evaluation in root of unity")
print(p(x))
print(p2(x))

# Por lo que entiendo, al evaluar un polinomio en las raices de la unidad, se toma hasta la potencia N-1. Y estas
# que de forma es espejada las potencias N/2 a N-1 cambia sola la parte real de signo:q


for i in range(N//2):
    print(f"k={i} and N/2-k={N//2-i}" , rootOfUnityPow(M, k, i))


# Si esto es asi cumple, por que quiero evaluar el polinomio en las mismas raices y obtener el resutaldo conjugado
# Si expando veo que el coeff 0 no esta multiplciado por nada, asi que simplemente conjugo eso.
# Y luego puedo usar propiedades de reemplazar las potencias N//4 hasta N//2 con su version dada vuelta.
# si hago la cuenta veo que haciendo ese cambio de variables obtengo lo mismo negando la parte imaginaria
