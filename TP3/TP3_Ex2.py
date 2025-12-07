from z3 import *

def main():
    print("=== INÍCIO DA VERIFICAÇÃO OTIMIZADA (EEA 16-bits) ===\n")

    # 1. Variáveis de estado
    a, b = BitVecs('a b', 16)
    r, r_linha = BitVecs('r r_linha', 16)
    s, s_linha = BitVecs('s s_linha', 16)
    t, t_linha = BitVecs('t t_linha', 16)

    # Variáveis do próximo estado
    r_prox, r_linha_prox = BitVecs('r_next r_linha_next', 16)
    s_prox, s_linha_prox = BitVecs('s_next s_linha_next', 16)
    t_prox, t_linha_prox = BitVecs('t_next t_linha_next', 16)

    # ### CORREÇÃO DE PERFORMANCE ###
    # Em vez de calcular q = UDiv(r, r_linha), criamos q como uma variável livre.
    # Se provarmos que funciona para QUALQUER q, então funciona para o q da divisão.
    q = BitVec('q', 16)

    # Invariante
    def Invariante(_r, _s, _t, _rl, _sl, _tl):
        return And(
            a * _s + b * _t == _r,
            a * _sl + b * _tl == _rl
        )

    # Transição Genérica (Independente da lógica da divisão, depende apenas da atualização linear)
    transicao_loop = And(
        r_linha != 0,
        r_prox == r_linha,
        r_linha_prox == r - q * r_linha, 
        s_prox == s_linha,
        s_linha_prox == s - q * s_linha,
        t_prox == t_linha,
        t_linha_prox == t - q * t_linha
    )

    # =========================================================================
    # PARTE A: PROVA DE CORREÇÃO (k-Indução)
    # =========================================================================
    print("--- PARTE A: k-Indução ---")
    S = Solver()
    
    # Passo Base
    print("1. Verificando Passo Base...")
    init_cond = And(r == a, r_linha == b, s == 1, s_linha == 0, t == 0, t_linha == 1)
    S.add(init_cond)
    S.add(Not(Invariante(r, s, t, r_linha, s_linha, t_linha)))
    if S.check() == unsat:
        print("   [SUCESSO] Passo Base provado.")
    else:
        print("   [FALHA] Passo Base.")

    # Passo Indutivo
    print("2. Verificando Passo Indutivo (Com abstração de q)...")
    S.reset() # Limpar o solver para a nova prova
    S.add(a > 0, b > 0)
    
    # Hipótese: Invariante é verdade AGORA
    S.add(Invariante(r, s, t, r_linha, s_linha, t_linha))
    
    # Acontece uma transição (com um q qualquer)
    S.add(transicao_loop)
    
    # Tese (negada): Invariante FALHA DEPOIS
    S.add(Not(Invariante(r_prox, s_prox, t_prox, r_linha_prox, s_linha_prox, t_linha_prox)))
    
    if S.check() == unsat:
        print("   [SUCESSO] Passo Indutivo provado.")
    else:
        print("   [FALHA] Passo Indutivo falhou.")
        # print(S.model())

    # =========================================================================
    # PARTE B: PROVA DE TERMINAÇÃO
    # =========================================================================
    print("\n--- PARTE B: Terminação ---")
    # Aqui precisamos mesmo da divisão (ou resto), não podemos abstrair o q.
    # Mas usamos URem (Unsigned Remainder) que é mais direto para o Z3 que a fórmula manual.
    
    S_term = Solver()
    S_term.add(r_linha != 0) 
    
    # O próximo r_linha é, na verdade, r % r_linha
    # Usar URem (resto) é mais eficiente que reconstruir com multiplicação
    prox_rl_real = URem(r, r_linha)
    
    # Propriedade: O novo r' tem de ser estritamente menor que o r' atual
    ranking = UGT(r_linha, prox_rl_real)
    
    print("3. Verificando decrescimento estrito...")
    S_term.add(Not(ranking))
    
    if S_term.check() == unsat:
        print("   [SUCESSO] Terminação Provada.")
    else:
        print("   [FALHA] Terminação.")

if __name__ == "__main__":
    main()