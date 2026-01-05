from z3 import *
import time

# ==============================================================================
# 1. CONFIGURAÇÕES E CONSTANTES
# ==============================================================================
SIGMA = 0.5       # Coeficiente de atrito
DT = 0.25         # Passo de tempo
LIMIT_Z = 1.0     # Tamanho do setor (1 km)

# Definir os Portos como números inteiros (para o Z3 não se queixar)
PORTO_A_FINAL = -1
PORTO_B_FINAL = 15

# Mapa de Adjacências (Topologia Real com bifurcações)
# Igual ao que funcionou bem, mas com os IDs numéricos
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
# 2. PARÂMETROS FÍSICOS (O que faltava!)
# ==============================================================================

def get_params(sector, is_ship_A):
    """
    Retorna (gamma, epsilon, V) para um dado setor.
    Implementa a lógica do enunciado:
    - Navio A: Zonas Acel={11,13,2,4}, Decel={1,3,12,14}, Baixa={0}
    - Navio B: Troca Aceleração com Desaceleração.
    """
    # Se for um estado final, física nula
    if sector == PORTO_A_FINAL or sector == PORTO_B_FINAL:
        return 0.0, 0.0, 100.0

    # Definição das Zonas (Baseado na imagem do enunciado)
    zonas_acel = {11, 13, 2, 4}
    zonas_decel = {1, 3, 12, 14}
    zona_baixa  = {0}
    
    # Valores Típicos (Ajustados ao enunciado)
    gamma_acel = 1.0
    gamma_decel = 0.0
    epsilon_base = 0.1  # Corrente
    V_limite = 2.5      # Limite de velocidade V
    
    # Lógica de Troca para Navio B
    if is_ship_A:
        acelerar = (sector in zonas_acel)
    else:
        # Para B, onde A desacelera, B acelera (troca)
        acelerar = (sector in zonas_decel)

    # Atribuição dos valores
    if sector in zona_baixa:
        # s0: Velocidade baixa constante
        return 0.2, 0.0, 1.0 
    elif acelerar:
        return gamma_acel, epsilon_base, V_limite
    else:
        return gamma_decel, -epsilon_base, V_limite

# ==============================================================================
# 3. LÓGICA DE ESTADO E TRANSIÇÃO
# ==============================================================================

def declare_state(i):
    """Cria as variáveis Z3 para o passo i."""
    s = {}
    # Navio A
    s['sA'] = Int(f'sA_{i}')
    s['zA'] = Real(f'zA_{i}')
    s['vA'] = Real(f'vA_{i}')
    s['waitA'] = Bool(f'waitA_{i}')
    # Navio B
    s['sB'] = Int(f'sB_{i}')
    s['zB'] = Real(f'zB_{i}')
    s['vB'] = Real(f'vB_{i}')
    s['waitB'] = Bool(f'waitB_{i}')
    return s

def init(s):
    """Estado Inicial simétrico para provocar o encontro."""
    return And(
        s['sA'] == 11, s['zA'] == 0.0, s['vA'] == 0.6, s['waitA'] == False,
        s['sB'] == 14, s['zB'] == 0.0, s['vB'] == 0.6, s['waitB'] == False
    )

def trans_navio(s_curr, z_curr, v_curr, s_next, z_next, v_next, wait_next, 
                adj, is_ship_A, other_s_curr, other_s_next):
    
    # 1. FÍSICA (Cálculo da Velocidade) - Igual ao anterior
    v_next_calc = v_curr 
    for sec_id in adj.keys():
        g, e, V = get_params(sec_id, is_ship_A)
        dv = If(v_curr <= V, g - (SIGMA * v_curr), e - (SIGMA * v_curr))
        v_next_calc = If(s_curr == int(sec_id), v_curr + dv * DT, v_next_calc)

    # 2. FLOW (Movimento dentro do setor)
    cond_flow = z_curr < LIMIT_Z
    logic_flow = And(
        cond_flow,
        s_next == s_curr,
        z_next == z_curr + v_curr * DT,
        v_next == v_next_calc,
        wait_next == False
    )

    # 3. JUMP (Transição de Setor)
    cond_jump = z_curr >= LIMIT_Z
    possible_jumps = []
    
    for src, targets in adj.items():
        src_val = int(src)
        
        choices = []
        entry_conditions = [] # Lista para guardar as "Luzes Verdes"
        
        for dst in targets:
            dst_val = int(dst)
            
            # Condição de Semáforo: Livre se o outro não estiver lá nem a entrar
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
        
        # --- AQUI ESTÁ A CORREÇÃO ---
        # Só pode esperar se NÃO houver nenhuma luz verde (Blocked)
        # Se houver pelo menos um caminho livre, cannot_enter_any será False
        if entry_conditions:
            cannot_enter_any = Not(Or(entry_conditions))
        else:
            cannot_enter_any = True # Se não há destinos (fim do mapa), para.

        wait_logic = And(
            cannot_enter_any, # <--- OBRIGA A AVANÇAR SE PUDER
            s_next == s_curr,
            z_next == z_curr,
            v_next == If(v_curr > 0, v_curr - (SIGMA*v_curr)*DT, 0.0),
            wait_next == True
        )
        choices.append(wait_logic)
        
        possible_jumps.append(Implies(s_curr == src_val, Or(choices)))

    # Lógica de Fim (Porto)
    finished = Or(s_curr == PORTO_A_FINAL, s_curr == PORTO_B_FINAL)
    logic_finish = And(
        finished, 
        s_next == s_curr, 
        v_next == 0.0, 
        wait_next == False
    )

    logic_jump = And(cond_jump, If(finished, logic_finish, And(possible_jumps)))

    return If(cond_flow, logic_flow, logic_jump)


def trans(curr, nxt):
    tA = trans_navio(curr['sA'], curr['zA'], curr['vA'], nxt['sA'], nxt['zA'], nxt['vA'], nxt['waitA'], 
                     ADJ_A, True, curr['sB'], nxt['sB'])
    
    tB = trans_navio(curr['sB'], curr['zB'], curr['vB'], nxt['sB'], nxt['zB'], nxt['vB'], nxt['waitB'], 
                     ADJ_B, False, curr['sA'], nxt['sA'])
    return And(tA, tB)

# ==============================================================================
# 4. EXECUÇÃO (BMC)
# ==============================================================================

def run_bmc(k, check_type="sufficient"):
    print(f"\n--- BMC (k={k}) | Modo: {check_type.upper()} ---")
    s = Solver()
    states = [declare_state(i) for i in range(k + 1)]
    
    s.add(init(states[0]))
    for i in range(k):
        s.add(trans(states[i], states[i+1]))
        
    unsafe_prop = False
    if check_type == "sufficient":
        # Colisão: mesmo setor e não é porto final
        collision = Or([
            And(states[i]['sA'] == states[i]['sB'], 
                states[i]['sA'] != PORTO_A_FINAL, states[i]['sA'] != PORTO_B_FINAL)
            for i in range(k + 1)
        ])
        unsafe_prop = collision
    elif check_type == "strong":
        # Bloqueio: alguém teve de esperar
        waited = Or([Or(states[i]['waitA'], states[i]['waitB']) for i in range(1, k+1)])
        unsafe_prop = waited

    s.add(unsafe_prop)
    if s.check() == sat:
        print("Resultado: UNSAFE (Falha encontrada!)")
        m = s.model()
        for i in range(k + 1):
            sa, sb = m[states[i]['sA']], m[states[i]['sB']]
            wa = is_true(m[states[i]['waitA']])
            wb = is_true(m[states[i]['waitB']])
            if i==0 or str(sa)!=str(m[states[i-1]['sA']]) or str(sb)!=str(m[states[i-1]['sB']]) or wa or wb:
                print(f"Passo {i:02}: A:{sa}{'[WAIT]' if wa else ''} | B:{sb}{'[WAIT]' if wb else ''}")
    else:
        print("Resultado: SAFE (Nenhuma falha encontrada)")

if __name__ == "__main__":
    run_bmc(30, "sufficient")
    run_bmc(30, "strong")