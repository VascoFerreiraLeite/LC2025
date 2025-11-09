#import networkx as nx
#import matplotlib.pyplot as plt
#from ortools.linear_solver import pywraplp
from z3 import *
import numpy as np


n=10 #teste
k=5 #teste
rng=np.random.default_rng(12345)
print(rng) #debug
z=rng.integers(low=0, high=2, size=n, dtype=np.uint8)
s=rng.integers(low=0, high=2, size=k, dtype=np.uint8)
print(z) #debug
print(s) #debug

def produto_int(a, b):
    assert len(a)==len(b)
    n=len(a)
    res=0
    for i in range(n):
        prod=a[i]&b[i]
        res=res^prod
    return res

def gate_xor(t1, t2):
    w1, d1=t1
    w2, d2=t2

    #w=BitVec(f"xor_w{z3.get_var_index(0)}", 1)
    w=BitVec("xor_w", 1)
    ww=w1^w2
    d=Or(d1, d2)

    rest=Or(d, w==ww)
    return (w, d), rest

def gate_and(t1, t2, falha):
    w1, d1=t1
    w2, d2=t2
    
    #w=BitVec(f"and_w{z3.get_var_index(0)}", 1)
    w=BitVec("and_w", 1)
    ww=w1&w2
    d=Or(d1, d2, falha) #falha aqui pq se ela falha entao a saida tbm

    rest=Or(d, w==ww)
    return (w, d), rest  
    
def gate_maj(t1, t2, t3):
    w1, d1=t1
    w2, d2=t2
    w3, d3=t3

    #w=BitVec(f"maj_w{z3.get_var_index(0)}", 1)
    w=BitVec("maj_w", 1)
    maj=(w1&w2) | (w1&w3) | (w2&w3)
    d=Or(d1, d2, d3)

    rest=Or(d, w==maj)
    return (w, d), rest

def gate_prod(vec_x, x_bits):
    assert len(vec_x)==len(x_bits)
    tam=len(vec_x)

    lista=[]

    for i in range(tam):
        bit=BitVecVal(int(vec_x[i]), 1)
        x_bit=x_bits[i]
        lista.append(bit & x_bit)

    if not lista:
        res=BitVecVal(0, 1)
    
    else:
        res=lista[0]
        for i in range(1, tam):
            res=res ^ lista[i]
    
    return (res, BoolVal(False))



def main():#contruir_p():
    semente_s=np.random.SeedSequence(s.tolist())
    print(semente_s) #debug
    rng_s=np.random.default_rng(semente_s)
    print(rng_s) #debug
    sub_seeds=rng_s.integers(low=0, high=2**64, size=n, dtype=np.uint64)
    lista=[]
    for i in range(n):
        rng_sub=np.random.default_rng(sub_seeds[i])

        a=rng_sub.integers(0, 2, size=n, dtype=np.uint8)
        b=rng_sub.integers(0, 2, size=n, dtype=np.uint8)
        c=rng_sub.integers(0, 2, size=n, dtype=np.uint8)

        #offset -> o=(a . z) ^ (b . z) & (c . z)
        a_z=produto_int(a, z)
        b_z=produto_int(b, z)
        c_z=produto_int(c, z)

        o=a_z ^ (b_z & c_z)

        lista.append((int(o), a, b, c))

    #mudar este output dps
    print("-------------------------------------------------")
    print(f"Geração de parâmetros concluída.")
    print(f"Total de conjuntos de parâmetros gerados: {len(lista)}")

    if n > 0:
        p0 = lista[0]
        print(f"Exemplo: p_0 = (o_0={p0[0]}, a_0={p0[1][:4]}...)")

    if n > 1:
        p1 = lista[1] # <--- Imprimir o segundo elemento
        print(f"Exemplo: p_1 = (o_0={p1[0]}, a_0={p1[1][:4]}...)") # <-- Verifique que este é diferente!

    #--------------

    #contruir modelo

    solver=Solver()

    x_bits=[]
    for i in range(n):
        x_bits.append(BitVec(f'x_{i}', 1))

    #reverter porque bits menos significativos primeiro
    x_input=Concat(list(reversed(x_bits)))

    #debug x2
    print(f"  - {n} variáveis de input (x_0 ... x_{n-1}) criadas.")
    print(f"  - Vetor 'x_input' colado pronto para a Tarefa 2.")


    falhas=[]
    saidas=[]

    for i in range(n):
        o, a, b, c=lista[i]

        o_wd=(BitVecVal(o, 1), BoolVal(False))

        a_x_wd=gate_prod(a, x_bits)
        b_x_wd=gate_prod(b, x_bits)
        c_x_wd=gate_prod(c, x_bits)

        #por alguma razao faz isto, talvez mudar dps - bandeiras de falha and
        and1=Bool(f'and1{i}')
        and2=Bool(f'and2{i}')
        and3=Bool(f'and3{i}')
        falhas.extend([and1, and2, and3])

        and1_wd, c1=gate_and(b_x_wd, c_x_wd, and1)
        and2_wd, c2=gate_and(b_x_wd, c_x_wd, and2)
        and3_wd, c3=gate_and(b_x_wd, c_x_wd, and3)

        solver.add(c1)
        solver.add(c2)
        solver.add(c3)

        maj_wd, c_maj=gate_maj(and1_wd, and2_wd, and3_wd)
        solver.add(c_maj)

        quadrado_maj=maj_wd

        #o ^ (a . x)
        xor_wd1, c_xor1=gate_xor(o_wd, a_x_wd)
        xor_wd2, c_xor2=gate_xor(xor_wd1, quadrado_maj)
        solver.add(c_xor1)
        solver.add(c_xor2)

        saidas.append(xor_wd2)

    #dps mudar output
    print("Modelo SMT construído com sucesso!")
    print(f"  - Solver 's' está pronto.")
    print(f"  - Variável de input: {x_input}")
    print(f"  - Total de falhas AND modeladas: {len(falhas)}")
    print(f"  - Total de outputs do circuito: {len(saidas)}")
            






if __name__ == "__main__":
    main()