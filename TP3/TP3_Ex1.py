from z3 import *

N = 16      
EXT = 64 

def criar_variaveis():
    
    a, b = BitVecs('a b', N)
    r, r_p = BitVecs('r r_p', N)
    s, s_p = BitVecs('s s_p', N)
    t, t_p = BitVecs('t t_p', N)
    
    return (a, b, r, r_p, s, s_p, t, t_p)

def configurar_solver():

    fp = Fixedpoint()
    fp.set(engine='spacer')
    fp.set('print_answer', True)
    
    return fp

def registar_relacoes(fp):

    B16 = BitVecSort(N)
    
    Inv = Function('Inv', B16, B16, B16, B16, B16, B16, B16, B16, BoolSort())
    Fail = Function('Fail', BoolSort())

    fp.register_relation(Inv)
    fp.register_relation(Fail)
    
    return Inv, Fail

def calc_checked_next(curr_bv, q_bv, next_bv, signed_check):

    if signed_check:
        curr_ext = SignExt(EXT - N, curr_bv)
        q_ext    = ZeroExt(EXT - N, q_bv)
        next_ext = SignExt(EXT - N, next_bv)
    else:
        curr_ext = ZeroExt(EXT - N, curr_bv)
        q_ext    = ZeroExt(EXT - N, q_bv)
        next_ext = ZeroExt(EXT - N, next_bv)

    term_ext = q_ext * next_ext
    res_ext  = curr_ext - term_ext 

    res_int = BV2Int(res_ext, signed_check)

    if signed_check:
        min_int = IntVal(- (1 << (N-1)))
        max_int = IntVal((1 << (N-1)) - 1)
    else:
        min_int = IntVal(0)
        max_int = IntVal((1 << N) - 1)

    is_overflow = Or(res_int < min_int, res_int > max_int)

    res_trunc = Extract(N-1, 0, res_ext)

    return res_trunc, is_overflow

def calcular_transicao(r, r_p, s, s_p, t, t_p):

    q = UDiv(r, r_p)

    r_new, ovf_r = calc_checked_next(r, q, r_p, signed_check=False)
    s_new, ovf_s = calc_checked_next(s, q, s_p, signed_check=True)
    t_new, ovf_t = calc_checked_next(t, q, t_p, signed_check=True)

    any_overflow = Or(ovf_r, ovf_s, ovf_t)

    return r_new, s_new, t_new, any_overflow

def adicionar_regras(fp, Inv, Fail, vars_estado):

    a, b, r, r_p, s, s_p, t, t_p = vars_estado
    all_vars = [a, b, r, r_p, s, s_p, t, t_p]
    
    zero_bv = BitVecVal(0, N)

    fp.add_rule(ForAll([a, b],
                       Implies(
                           And(UGT(a, zero_bv), UGT(b, zero_bv)),
                           Inv(a, b,
                               a, b,                    
                               BitVecVal(1, N), BitVecVal(0, N), 
                               BitVecVal(0, N), BitVecVal(1, N))
                       )))

    r_new, s_new, t_new, any_overflow = calcular_transicao(r, r_p, s, s_p, t, t_p)

    fp.add_rule(ForAll(all_vars,
                       Implies(
                           And(
                               Inv(a, b, r, r_p, s, s_p, t, t_p),
                               r_p != zero_bv,
                               Not(any_overflow)
                           ),
                           Inv(a, b, r_p, r_new, s_p, s_new, t_p, t_new)
                       )))

    cond_error = Or(r == zero_bv, any_overflow)
    fp.add_rule(ForAll(all_vars,
                       Implies(
                           And(
                               Inv(a, b, r, r_p, s, s_p, t, t_p),
                               r_p != zero_bv,
                               cond_error
                           ),
                           Fail()
                       )))
    
def executar_verificacao(fp, Fail):
    res = fp.query(Fail)

    if res == unsat:
        print("\n RESULTADO: SEGURO (unsat)")
        print("  O Fixedpoint provou que não existe trace que leve a Fail (r=0 ou overflow).")
        print("\nInvariante calculado pelo solver:")
        try:
            print(fp.get_answer())
        except Z3Exception:
            print("  (fp.get_answer() não disponível)")
    elif res == sat:
        print("\n RESULTADO: INSEGURO (sat)")
        print("  O Fixedpoint encontrou um contra-exemplo que leva a Fail (r=0 ou overflow).")
        try:
            print("\nContra-exemplo / prova fornecida pelo solver:")
            print(fp.get_answer())
        except Z3Exception:
            pass
    else:
        print("\n RESULTADO: Unknown / Timeout")

def verificar_exa_sfots_modular():
    print("  VERIFICAÇÃO EXA: SFOTS COM BITVECTORS (16-bit)")
    
    fp = configurar_solver()
    vars_estado = criar_variaveis()
    Inv, Fail = registar_relacoes(fp)
    adicionar_regras(fp, Inv, Fail, vars_estado)
    executar_verificacao(fp, Fail)

if __name__ == "__main__":
    verificar_exa_sfots_modular()