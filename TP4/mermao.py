from z3 import *
import math

# ==============================================================================
# 1. CONFIGURAÇÕES E CONSTANTES
# ==============================================================================
SIGMA = 0.5
DT = 0.25
LIMIT_Z = 1.0

# Constantes dos Portos
PORTO_A_FINAL = -1
PORTO_B_FINAL = 15

# Mapas de Adjacência (Lógica)
ADJ_A = {
    11: [5, 7], 13: [9, 7],
    5: [1], 7: [1, 3], 9: [3],
    1: [0], 3: [0], 
    0: [2, 4],
    2: [6, 8], 4: [8, 10],
    6: [12], 8: [12, 14], 10: [14],
    12: [PORTO_B_FINAL], 14: [PORTO_B_FINAL], PORTO_B_FINAL: [PORTO_B_FINAL]
}

ADJ_B = {
    12: [6, 8], 14: [10, 8],
    6: [2], 8: [2, 4], 10: [4],
    2: [0], 4: [0],
    0: [1, 3],
    1: [5, 7], 3: [7, 9],
    5: [11], 7: [11, 13], 9: [13],
    11: [PORTO_A_FINAL], 13: [PORTO_A_FINAL], PORTO_A_FINAL: [PORTO_A_FINAL]
}

# ==============================================================================
# 2. GEOMETRIA 
# ==============================================================================
GEO_DATA = {
    # Coluna Esquerda (x=0)
    11: (0.0, 3.0, 0.0), 13: (0.0, 1.0, 0.0),
    # Coluna Meio-Esq (x=1)
    5:  (1.0, 3.0, 0.0), 7:  (1.0, 2.0, 0.0), 9: (1.0, 1.0, 0.0),
    # Entrada Gargalo (x=2)
    1:  (2.0, 2.5, 0.0), 3:  (2.0, 1.5, 0.0),
    # O Gargalo (x=3) - S0
    0:  (3.0, 2.0, 0.0),
    # Saída Gargalo (x=4)
    2:  (4.0, 2.5, 0.0), 4:  (4.0, 1.5, 0.0),
    # Coluna Meio-Dir (x=5)
    6:  (5.0, 3.0, 0.0), 8:  (5.0, 2.0, 0.0), 10: (5.0, 1.0, 0.0),
    # Coluna Direita (x=6)
    12: (6.0, 3.0, 0.0), 14: (6.0, 1.0, 0.0),
    # Portos Finais
    PORTO_A_FINAL: (-1.0, 2.0, 0.0), 
    PORTO_B_FINAL: (7.0, 2.0, 0.0)   
}

def get_xy(sector, z_val, is_ship_A):
    """
    Calcula x, y reais.
    CORREÇÃO: Navio B inverte a direção do X (anda para a esquerda).
    """
    if sector not in GEO_DATA: return 0.0, 0.0
    
    # x0 é sempre a borda ESQUERDA do setor
    x0, y0, phi = GEO_DATA[sector]
    
    if is_ship_A:
        # Navio A: Entra na esquerda (x0), sai na direita (x0 + 1)
        x = x0 + z_val
    else:
        # Navio B: Entra na direita (x0 + 1), sai na esquerda (x0)
        # Nota: z vai de 0 a 1, logo x vai de (x0+1) a x0
        x = (x0 + 1.0) - z_val
        
    y = y0 
    return x, y

def get_params(sector, is_ship_A):
    """Parâmetros Físicos (Gamma, Epsilon, V)"""
    if sector == PORTO_A_FINAL or sector == PORTO_B_FINAL:
        return 0.0, 0.0, 100.0

    zonas_acel = {11, 13, 2, 4}
    zonas_decel = {1, 3, 12, 14}
    zona_baixa  = {0}
    
    gamma_acel = 1.0
    gamma_decel = 0.0
    epsilon_base = 0.1
    V_limite = 2.5
    
    if is_ship_A:
        acelerar = (sector in zonas_acel)
    else:
        acelerar = (sector in zonas_decel) # B troca aceleração

    if sector in zona_baixa:
        return 0.2, 0.0, 1.0 # s0 é lento
    elif acelerar:
        return gamma_acel, epsilon_base, V_limite
    else:
        return gamma_decel, -epsilon_base, V_limite

# ==============================================================================
# 3. Z3 LOGIC
# ==============================================================================

def declare_state(i):
    s = {}
    s['sA'] = Int(f'sA_{i}')
    s['zA'] = Real(f'zA_{i}')
    s['vA'] = Real(f'vA_{i}')
    s['waitA'] = Bool(f'waitA_{i}')
    s['sB'] = Int(f'sB_{i}')
    s['zB'] = Real(f'zB_{i}')
    s['vB'] = Real(f'vB_{i}')
    s['waitB'] = Bool(f'waitB_{i}')
    return s

def init(s):
    return And(
        s['sA'] == 11, s['zA'] == 0.0, s['vA'] == 0.6, s['waitA'] == False,
        s['sB'] == 14, s['zB'] == 0.0, s['vB'] == 0.6, s['waitB'] == False
    )

def trans_navio(s_curr, z_curr, v_curr, s_next, z_next, v_next, wait_next, 
                adj, is_ship_A, other_s_curr, other_s_next):
    
    # 1. Física
    v_next_calc = v_curr 
    for sec_id in adj.keys():
        g, e, V = get_params(sec_id, is_ship_A)
        dv = If(v_curr <= V, g - (SIGMA * v_curr), e - (SIGMA * v_curr))
        v_next_calc = If(s_curr == int(sec_id), v_curr + dv * DT, v_next_calc)

    # 2. Flow
    cond_flow = z_curr < LIMIT_Z
    logic_flow = And(
        cond_flow,
        s_next == s_curr,
        z_next == z_curr + v_curr * DT,
        v_next == v_next_calc,
        wait_next == False
    )

    # 3. Jump (Semáforo + Wait Anti-Preguiça)
    cond_jump = z_curr >= LIMIT_Z
    possible_jumps = []
    
    for src, targets in adj.items():
        src_val = int(src)
        choices = []
        entry_conditions = []
        
        for dst in targets:
            dst_val = int(dst)
            # Semáforo
            can_enter = And(other_s_curr != dst_val, other_s_next != dst_val)
            entry_conditions.append(can_enter)
            
            enter = And(
                can_enter,
                s_next == dst_val,
                z_next == 0.0,
                v_next == v_curr,
                wait_next == False
            )
            choices.append(enter)
        
        # Só espera se NÃO puder entrar em lado nenhum
        if entry_conditions:
            blocked = Not(Or(entry_conditions))
        else:
            blocked = True

        wait_logic = And(
            blocked,
            s_next == s_curr,
            z_next == z_curr,
            v_next == If(v_curr > 0, v_curr - (SIGMA*v_curr)*DT, 0.0),
            wait_next == True
        )
        choices.append(wait_logic)
        possible_jumps.append(Implies(s_curr == src_val, Or(choices)))

    finished = Or(s_curr == PORTO_A_FINAL, s_curr == PORTO_B_FINAL)
    logic_finish = And(finished, s_next == s_curr, v_next == 0.0, wait_next == False)

    return If(cond_flow, logic_flow, And(cond_jump, If(finished, logic_finish, And(possible_jumps))))

def trans(curr, nxt):
    tA = trans_navio(curr['sA'], curr['zA'], curr['vA'], nxt['sA'], nxt['zA'], nxt['vA'], nxt['waitA'], ADJ_A, True, curr['sB'], nxt['sB'])
    tB = trans_navio(curr['sB'], curr['zB'], curr['vB'], nxt['sB'], nxt['zB'], nxt['vB'], nxt['waitB'], ADJ_B, False, curr['sA'], nxt['sA'])
    return And(tA, tB)

# ==============================================================================
# 4. EXECUÇÃO E VISUALIZAÇÃO
# ==============================================================================

def z3_to_float(val):
    """Converte fração Z3 para float python"""
    if is_rational_value(val):
        return float(val.numerator_as_long()) / float(val.denominator_as_long())
    return 0.0

def run_bmc(k, check_type="sufficient"):
    print(f"\n--- BMC (k={k}) | Modo: {check_type.upper()} ---")
    s = Solver()
    states = [declare_state(i) for i in range(k + 1)]
    
    s.add(init(states[0]))
    for i in range(k):
        s.add(trans(states[i], states[i+1]))
        
    unsafe_prop = False
    if check_type == "sufficient":
        collision = Or([And(states[i]['sA'] == states[i]['sB'], states[i]['sA'] != PORTO_A_FINAL, states[i]['sA'] != PORTO_B_FINAL) for i in range(k + 1)])
        unsafe_prop = collision
    elif check_type == "strong":
        waited = Or([Or(states[i]['waitA'], states[i]['waitB']) for i in range(1, k+1)])
        unsafe_prop = waited

    s.add(unsafe_prop)
    
    if s.check() == sat:
        print("Resultado: UNSAFE (Falha encontrada!)")
        print(f"{'Step':<5} | {'Navio A (Sec, v, z, x, y)':<35} | {'Navio B (Sec, v, z, x, y)':<35}")
        print("-" * 85)
        
        m = s.model()
        for i in range(k + 1):
            # Dados Navio A
            sa = m[states[i]['sA']].as_long()
            za = z3_to_float(m[states[i]['zA']])
            va = z3_to_float(m[states[i]['vA']])
            wa = is_true(m[states[i]['waitA']])
            # Passamos True para Navio A
            xa, ya = get_xy(sa, za, True)
            
            # Dados Navio B
            sb = m[states[i]['sB']].as_long()
            zb = z3_to_float(m[states[i]['zB']])
            vb = z3_to_float(m[states[i]['vB']])
            wb = is_true(m[states[i]['waitB']])
            # Passamos False para Navio B
            xb, yb = get_xy(sb, zb, False)
            
            wa_str = " [WAIT]" if wa else ""
            wb_str = " [WAIT]" if wb else ""
            
            str_a = f"s{sa:<2} v={va:.2f} z={za:.2f} ({xa:.1f}, {ya:.1f}){wa_str}"
            str_b = f"s{sb:<2} v={vb:.2f} z={zb:.2f} ({xb:.1f}, {yb:.1f}){wb_str}"
            
            print(f"{i:<5} | {str_a:<35} | {str_b:<35}")
    else:
        print("Resultado: SAFE (Nenhuma falha encontrada)")

if __name__ == "__main__":
    run_bmc(40, "sufficient")
    run_bmc(40, "strong")