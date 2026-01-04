from z3 import *
import time

# ==============================================================================
# CONFIGURAÇÃO DO SISTEMA
# ==============================================================================
SIGMA = 0.5
DT = 0.25       # Passo de tempo
LIMIT_Z = 1.0   # Tamanho do setor

# Zonas Geográficas (Conjuntos)
ZONAS_ACEL_A = {11, 13, 2, 4}
ZONAS_DECEL_A = {1, 3, 12, 14}
ZONAS_ACEL_B = {1, 3, 12, 14}
ZONAS_DECEL_B = {11, 13, 2, 4}

# Mapa de Adjacências (Simplificado para Fluxo)
ADJ_A = {
    11: [5, 7], 13: [9, 7],
    5: [1], 7: [1, 3], 9: [3],
    1: [0], 3: [0],        # Entradas no Canal (Crítico)
    0: [2, 4],             # Saída do Canal
    2: [6, 8], 4: [10, 8],
    6: [12], 8: [12, 14], 10: [14],
    12: [99], 14: [99], 99: [99]
}

ADJ_B = {
    12: [6, 8], 14: [10, 8],
    6: [2], 8: [2, 4], 10: [4],
    2: [0], 4: [0],        # Entradas no Canal (Crítico)
    0: [1, 3],             # Saída do Canal
    1: [5, 7], 3: [9, 7],
    5: [11], 7: [11, 13], 9: [13],
    11: [98], 13: [98], 98: [98]
}

# ==============================================================================
# 1. DEFINIÇÃO DO ESTADO
# ==============================================================================
def declare_state(i):
    """Cria variáveis simbólicas para o passo i."""
    s = {}
    # Navio A
    s['sA'] = Int(f'sA_{i}')
    s['zA'] = Real(f'zA_{i}')
    s['vA'] = Real(f'vA_{i}')
    s['waitA'] = Bool(f'waitA_{i}') # Flag: A foi forçado a esperar neste passo?

    # Navio B
    s['sB'] = Int(f'sB_{i}')
    s['zB'] = Real(f'zB_{i}')
    s['vB'] = Real(f'vB_{i}')
    s['waitB'] = Bool(f'waitB_{i}') # Flag: B foi forçado a esperar neste passo?
    
    return s

def init(s):
    """Estado Inicial (t=0)."""
    return And(
        # A começa no topo esquerdo
        s['sA'] == 11, s['zA'] == 0.0, s['vA'] == 0.6, s['waitA'] == False,
        # B começa no fundo direito
        s['sB'] == 14, s['zB'] == 0.0, s['vB'] == 0.0, s['waitB'] == False
    )

# ==============================================================================
# 2. DINÂMICA E LÓGICA DE TRANSIÇÃO
# ==============================================================================
def get_gamma_A(s):
    return If(s == 0, 0.2,
           If(Or([s == z for z in ZONAS_ACEL_A]), 1.0,
           If(Or([s == z for z in ZONAS_DECEL_A]), 0.0,
           0.5)))

def get_gamma_B(s):
    return If(s == 0, 0.2,
           If(Or([s == z for z in ZONAS_ACEL_B]), 1.0,
           If(Or([s == z for z in ZONAS_DECEL_B]), 0.0,
           0.5)))

def physics_v(v, gamma):
    return v + (gamma - SIGMA * v) * DT

def trans_navio(s_curr, z_curr, v_curr, s_next, z_next, v_next, wait_next, 
                adj, get_gamma, other_s_curr, other_s_next):
    """
    Gera a lógica de transição para UM navio.
    IMPORTANTE: Recebe 'other_s_next' para resolver conflitos de entrada simultânea.
    """
    
    # 1. Flow (Continuar no mesmo setor)
    cond_flow = z_curr < LIMIT_Z
    gamma = get_gamma(s_curr)
    
    logic_flow = And(
        cond_flow,
        s_next == s_curr,
        z_next == z_curr + v_curr * DT,
        v_next == physics_v(v_curr, gamma),
        wait_next == False
    )

    # 2. Jump (Mudar de setor)
    cond_jump = z_curr >= LIMIT_Z
    
    possible_jumps = []
    
    # Itera sobre possíveis destinos
    dests = []
    # Hack para obter lista de destinos do dicionário Z3-friendly
    # (Numa impl. real fariamos lookup, aqui iteramos map estático)
    for src, targets in adj.items():
        
        choices = []
        for dst in targets:
            # --- LÓGICA DO SEMÁFORO ---
            # Pode entrar se:
            # 1. O outro navio não está lá (other_s_curr != dst)
            # 2. O outro navio não vai entrar lá AGORA (other_s_next != dst) -> MUTEX
            
            can_enter = And(other_s_curr != dst, other_s_next != dst)
            
            enter = And(
                can_enter,
                s_next == dst,
                z_next == 0.0,
                v_next == v_curr,
                wait_next == False
            )
            choices.append(enter)
            
        # Adicionar lógica de Espera (Wait) se bloqueado
        # Se escolhemos esperar ou somos forçados:
        wait_logic = And(
            s_next == s_curr,
            z_next == z_curr, # Pára na fronteira
            # Atrito atua na espera
            v_next == If(v_curr > 0, v_curr - (SIGMA * v_curr)*DT, 0.0),
            wait_next == True # Marca que esperou
        )
        choices.append(wait_logic)
        
        possible_jumps.append(Implies(s_curr == src, Or(choices)))

    # Lógica de Fim (Porto)
    finished = Or(s_curr == 99, s_curr == 98)
    logic_finish = And(
        finished, 
        s_next == s_curr, 
        v_next == 0.0, 
        wait_next == False
    )

    logic_jump = And(cond_jump, If(finished, logic_finish, And(possible_jumps)))

    return If(cond_flow, logic_flow, logic_jump)


def trans(curr, nxt):
    """Transição Global do Sistema"""
    
    # Construímos as transições cruzadas (passando o next do outro para mutex)
    t_A = trans_navio(
        curr['sA'], curr['zA'], curr['vA'],
        nxt['sA'], nxt['zA'], nxt['vA'], nxt['waitA'],
        ADJ_A, get_gamma_A, curr['sB'], nxt['sB']
    )
    
    t_B = trans_navio(
        curr['sB'], curr['zB'], curr['vB'],
        nxt['sB'], nxt['zB'], nxt['vB'], nxt['waitB'],
        ADJ_B, get_gamma_B, curr['sA'], nxt['sA']
    )
    
    return And(t_A, t_B)

# ==============================================================================
# 3. VERIFICAÇÃO (BMC)
# ==============================================================================
def run_bmc(k, check_type="sufficient"):
    print(f"\n--- Iniciando BMC (k={k}) | Modo: {check_type.upper()} SAFETY ---")
    solver = Solver()
    
    # Criar estados
    states = [declare_state(i) for i in range(k + 1)]
    
    # Adicionar Init
    solver.add(init(states[0]))
    
    # Adicionar Transições (Unrolling)
    for i in range(k):
        solver.add(trans(states[i], states[i+1]))
        
    # Definir condição de INSEGURANÇA (O que queremos evitar)
    unsafe_prop = False
    
    if check_type == "sufficient":
        # Falha se navios estiverem no mesmo setor (exceto fins distintos)
        # 
        collision = Or([
            And(states[i]['sA'] == states[i]['sB'], 
                states[i]['sA'] != 99, states[i]['sA'] != 98)
            for i in range(k + 1)
        ])
        unsafe_prop = collision
        
    elif check_type == "strong":
        # Falha se algum navio teve de esperar (wait == True)
        # "Nenhum navio é forçado a imobilizar-se"
        waited = Or([
            Or(states[i]['waitA'], states[i]['waitB'])
            for i in range(1, k + 1)
        ])
        unsafe_prop = waited

    # O Solver tenta encontrar um caso onde unsafe_prop é VERDADEIRO
    solver.add(unsafe_prop)
    
    start_time = time.time()
    result = solver.check()
    duration = time.time() - start_time
    
    if result == sat:
        print(f"Resultado: UNSAFE (Falha encontrada em {duration:.2f}s)")
        print(f"Contra-exemplo encontrado para '{check_type} safety':")
        m = solver.model()
        for i in range(k + 1):
            sa = m[states[i]['sA']]
            sb = m[states[i]['sB']]
            wa = is_true(m[states[i]['waitA']])
            wb = is_true(m[states[i]['waitB']])
            
            # Formatação bonita
            wa_str = " [WAIT]" if wa else ""
            wb_str = " [WAIT]" if wb else ""
            
            # Só imprime se mudou setor ou se houve wait
            if i == 0 or \
               str(sa) != str(m[states[i-1]['sA']]) or \
               str(sb) != str(m[states[i-1]['sB']]) or wa or wb:
                print(f"Step {i:02}: A no s{sa}{wa_str} | B no s{sb}{wb_str}")
        return False
    else:
        print(f"Resultado: SAFE (Nenhuma falha até k={k} em {duration:.2f}s)")
        return True

# ==============================================================================
# MAIN
# ==============================================================================
if __name__ == "__main__":
    # Passo 3 do Trabalho Prático
    
    # 1. Verificar Segurança Suficiente (Colisão)
    # Aumentei k para 30 para garantir que atravessam o canal s0
    run_bmc(k=30, check_type="sufficient")
    
    # 2. Verificar Segurança Forte (Bloqueio/Espera)
    run_bmc(k=30, check_type="strong")