#!/usr/bin/env python3
"""
Trabalho Prático 4 - Verificação de Propriedades de Segurança em Sistemas Híbridos
Controle de Tráfego Marítimo num Canal Estreito

Este programa implementa:
1. Três autómatos híbridos (2 navios + semáforo)
2. FOTS (First-Order Transition System) do sistema híbrido global
3. Verificação de segurança usando BMC e k-indução com Z3
"""

from z3 import *
from typing import List, Tuple, Dict, Set
from dataclasses import dataclass
from enum import Enum
import math

# ============================================================================
# DEFINIÇÃO DOS PARÂMETROS DO SISTEMA
# ============================================================================

class Signal(Enum):
    """Sinais do semáforo"""
    GREEN = "verde"      # Permissão de transitar
    YELLOW = "amarelo"   # Autorização para sector vizinho do outro navio
    RED = "vermelho"     # Não-sincronismo

@dataclass
class SectorParams:
    """Parâmetros de cada sector"""
    gamma: float  # Aceleração linear (γ)
    epsilon: float  # Força da corrente (ε)
    phi: float  # Rumo do navio (ϕ) em radianos
    V: float  # Limite superior de velocidade
    x0: float  # Coordenada x inicial
    y0: float  # Coordenada y inicial

# ============================================================================
# CONFIGURAÇÃO DOS SECTORES
# ============================================================================

def get_sector_params_ship_A() -> Dict[int, SectorParams]:
    """
    Parâmetros para o navio A (rota A→B)
    - {s11, s13} e {s2, s4}: zonas de aceleração (γ≃1)
    - {s1, s3} e {s12, s14}: zonas de desaceleração (γ≃0)
    - {s5, s7, s9} e {s6, s8, s10}: velocidade constante/cruzeiro
    - {s0}: velocidade baixa aproximadamente constante
    """
    params = {}
    
    # s0: Porto A - velocidade baixa
    params[0] = SectorParams(gamma=0.1, epsilon=0.0, phi=0.0, V=2.0, x0=0.0, y0=0.5)
    
    # s1: desaceleração
    params[1] = SectorParams(gamma=0.0, epsilon=-0.1, phi=0.0, V=5.0, x0=0.0, y0=0.5)
    
    # s2: aceleração
    params[2] = SectorParams(gamma=1.0, epsilon=0.1, phi=0.0, V=8.0, x0=0.0, y0=0.5)
    
    # s3: desaceleração
    params[3] = SectorParams(gamma=0.0, epsilon=-0.1, phi=0.0, V=6.0, x0=0.0, y0=0.5)
    
    # s4: aceleração
    params[4] = SectorParams(gamma=1.0, epsilon=0.1, phi=0.0, V=10.0, x0=0.0, y0=0.5)
    
    # s5: cruzeiro
    params[5] = SectorParams(gamma=0.2, epsilon=0.0, phi=math.pi/6, V=10.0, x0=0.0, y0=0.0)
    
    # s6: cruzeiro
    params[6] = SectorParams(gamma=0.2, epsilon=0.0, phi=math.pi/6, V=10.0, x0=0.0, y0=0.0)
    
    # s7: cruzeiro
    params[7] = SectorParams(gamma=0.2, epsilon=0.0, phi=0.0, V=10.0, x0=0.0, y0=0.5)
    
    # s8: cruzeiro
    params[8] = SectorParams(gamma=0.2, epsilon=0.0, phi=0.0, V=10.0, x0=0.0, y0=0.5)
    
    # s9: cruzeiro
    params[9] = SectorParams(gamma=0.2, epsilon=0.0, phi=-math.pi/6, V=10.0, x0=0.0, y0=1.0)
    
    # s10: cruzeiro
    params[10] = SectorParams(gamma=0.2, epsilon=0.0, phi=-math.pi/6, V=10.0, x0=0.0, y0=1.0)
    
    # s11: aceleração
    params[11] = SectorParams(gamma=1.0, epsilon=0.1, phi=0.0, V=10.0, x0=0.0, y0=0.5)
    
    # s12: desaceleração
    params[12] = SectorParams(gamma=0.0, epsilon=-0.1, phi=0.0, V=5.0, x0=0.0, y0=0.5)
    
    # s13: aceleração
    params[13] = SectorParams(gamma=1.0, epsilon=0.1, phi=0.0, V=8.0, x0=0.0, y0=0.5)
    
    # s14: desaceleração (chegada ao porto B)
    params[14] = SectorParams(gamma=0.0, epsilon=-0.2, phi=0.0, V=2.0, x0=0.0, y0=0.5)
    
    return params

def get_sector_params_ship_B() -> Dict[int, SectorParams]:
    """
    Parâmetros para o navio B (rota B→A)
    Zonas de aceleração e desaceleração trocadas em relação ao navio A
    """
    params = {}
    
    # Percurso inverso: s14 → s0
    # s14: Porto B - velocidade baixa
    params[14] = SectorParams(gamma=0.1, epsilon=0.0, phi=math.pi, V=2.0, x0=1.0, y0=0.5)
    
    # s13: desaceleração (trocado)
    params[13] = SectorParams(gamma=0.0, epsilon=-0.1, phi=math.pi, V=5.0, x0=1.0, y0=0.5)
    
    # s12: aceleração (trocado)
    params[12] = SectorParams(gamma=1.0, epsilon=0.1, phi=math.pi, V=8.0, x0=1.0, y0=0.5)
    
    # s11: desaceleração (trocado)
    params[11] = SectorParams(gamma=0.0, epsilon=-0.1, phi=math.pi, V=6.0, x0=1.0, y0=0.5)
    
    # s10: cruzeiro
    params[10] = SectorParams(gamma=0.2, epsilon=0.0, phi=math.pi+math.pi/6, V=10.0, x0=1.0, y0=1.0)
    
    # s9: cruzeiro
    params[9] = SectorParams(gamma=0.2, epsilon=0.0, phi=math.pi+math.pi/6, V=10.0, x0=1.0, y0=1.0)
    
    # s8: cruzeiro
    params[8] = SectorParams(gamma=0.2, epsilon=0.0, phi=math.pi, V=10.0, x0=1.0, y0=0.5)
    
    # s7: cruzeiro
    params[7] = SectorParams(gamma=0.2, epsilon=0.0, phi=math.pi, V=10.0, x0=1.0, y0=0.5)
    
    # s6: cruzeiro
    params[6] = SectorParams(gamma=0.2, epsilon=0.0, phi=math.pi-math.pi/6, V=10.0, x0=1.0, y0=0.0)
    
    # s5: cruzeiro
    params[5] = SectorParams(gamma=0.2, epsilon=0.0, phi=math.pi-math.pi/6, V=10.0, x0=1.0, y0=0.0)
    
    # s4: desaceleração (trocado)
    params[4] = SectorParams(gamma=0.0, epsilon=-0.1, phi=math.pi, V=6.0, x0=1.0, y0=0.5)
    
    # s3: aceleração (trocado)
    params[3] = SectorParams(gamma=1.0, epsilon=0.1, phi=math.pi, V=8.0, x0=1.0, y0=0.5)
    
    # s2: desaceleração (trocado)
    params[2] = SectorParams(gamma=0.0, epsilon=-0.1, phi=math.pi, V=5.0, x0=1.0, y0=0.5)
    
    # s1: aceleração (trocado)
    params[1] = SectorParams(gamma=1.0, epsilon=0.1, phi=math.pi, V=8.0, x0=1.0, y0=0.5)
    
    # s0: Porto A (destino) - velocidade baixa
    params[0] = SectorParams(gamma=0.0, epsilon=-0.2, phi=math.pi, V=2.0, x0=1.0, y0=0.5)
    
    return params

# ============================================================================
# AUTÓMATO HÍBRIDO - NAVIO
# ============================================================================

class ShipAutomaton:
    """
    Autómato híbrido representando um navio
    """
    def __init__(self, name: str, route: List[int], sigma: float, initial_sector: int, initial_v: float):
        self.name = name
        self.route = route  # Lista ordenada de sectores
        self.sigma = sigma  # Coeficiente de atrito
        self.initial_sector = initial_sector
        self.initial_v = initial_v
        
        # Parâmetros dos sectores
        if name == "ShipA":
            self.sector_params = get_sector_params_ship_A()
        else:
            self.sector_params = get_sector_params_ship_B()
        
        # Variáveis contínuas
        self.tau = Real(f'{name}_tau')  # tempo
        self.v = Real(f'{name}_v')  # velocidade
        self.z = Real(f'{name}_z')  # deslocamento
        
        # Variável discreta (modo/sector atual)
        self.sector = Int(f'{name}_sector')
        
    def get_flow_equations(self, sector_id: int) -> List:
        """
        Retorna as equações de fluxo para um dado sector
        
        Equações diferenciais:
        - τ̇ = 1
        - v̇ = γ - σv  se v ≤ V
        - v̇ = ε - σv  se v > V
        - ż = v
        """
        params = self.sector_params[sector_id]
        
        # Aproximação discreta: dx/dt ≈ (x' - x) / dt
        # Assumindo dt = 1 para simplificação
        dt = 1.0
        
        tau_next = self.tau + dt
        z_next = self.z + self.v * dt
        
        # Condição: se v ≤ V, então v̇ = γ - σv, senão v̇ = ε - σv
        v_dot_low = params.gamma - self.sigma * self.v
        v_dot_high = params.epsilon - self.sigma * self.v
        
        v_next = If(self.v <= params.V,
                    self.v + v_dot_low * dt,
                    self.v + v_dot_high * dt)
        
        return [tau_next, v_next, z_next]
    
    def get_position_constraints(self, sector_id: int) -> And:
        """
        Retorna as restrições de posição dentro do sector
        0 ≤ x₀ + z·cos(φ) ≤ 1
        0 ≤ y₀ + z·sin(φ) ≤ 1
        """
        params = self.sector_params[sector_id]
        
        x = params.x0 + self.z * math.cos(params.phi)
        y = params.y0 + self.z * math.sin(params.phi)
        
        return And(
            0 <= x, x <= 1,
            0 <= y, y <= 1,
            self.z >= 0,
            self.v >= 0,
            self.tau >= 0
        )
    
    def get_transition_condition(self, from_sector: int, to_sector: int) -> Bool:
        """
        Condição para transição entre sectores (quando atinge o limite do sector)
        """
        params = self.sector_params[from_sector]
        
        # Transição ocorre quando z atinge o limite do sector
        # Aproximadamente quando x ou y atinge o limite
        x = params.x0 + self.z * math.cos(params.phi)
        y = params.y0 + self.z * math.sin(params.phi)
        
        # Condição de saída do sector
        exit_condition = Or(
            x >= 0.99,
            x <= 0.01,
            y >= 0.99,
            y <= 0.01
        )
        
        return exit_condition

# ============================================================================
# AUTÓMATO HÍBRIDO - SEMÁFORO
# ============================================================================

class TrafficLightAutomaton:
    """
    Autómato híbrido representando o semáforo de controle
    Modos: pares (sA, sB) onde sA é o sector do navio A e sB é o sector do navio B
    """
    def __init__(self):
        self.name = "TrafficLight"
        
        # Variáveis
        self.t = Real('TL_t')  # tempo mestre
        self.sA = Int('TL_sA')  # sector do navio A
        self.sB = Int('TL_sB')  # sector do navio B
        
    def get_signal(self, ship_A_sector: int, ship_B_sector: int, 
                   target_sector_A: int, target_sector_B: int) -> Tuple[Signal, Signal]:
        """
        Determina os sinais para cada navio baseado nas posições atuais e destinos
        
        Verde: permissão de transitar
        Amarelo: autorização para sector vizinho do outro navio
        Vermelho: não-sincronismo (esperar)
        """
        # Se estão no mesmo sector: AMBOS VERMELHO (violação de segurança!)
        if ship_A_sector == ship_B_sector:
            return (Signal.RED, Signal.RED)
        
        # Se o sector destino está ocupado pelo outro navio: VERMELHO
        signal_A = Signal.RED if target_sector_A == ship_B_sector else Signal.GREEN
        signal_B = Signal.RED if target_sector_B == ship_A_sector else Signal.GREEN
        
        # Se o sector destino é vizinho do outro navio: AMARELO
        if abs(target_sector_A - ship_B_sector) == 1:
            signal_A = Signal.YELLOW
        if abs(target_sector_B - ship_A_sector) == 1:
            signal_B = Signal.YELLOW
        
        return (signal_A, signal_B)

# ============================================================================
# SISTEMA HÍBRIDO GLOBAL - FOTS
# ============================================================================

class HybridSystem:
    """
    First-Order Transition System (FOTS) representando o sistema híbrido global
    """
    def __init__(self):
        # Inicializar autómatos
        self.ship_A = ShipAutomaton(
            name="ShipA",
            route=list(range(0, 15)),  # s0 → s14
            sigma=0.05,  # Coeficiente de atrito
            initial_sector=0,
            initial_v=1.0
        )
        
        self.ship_B = ShipAutomaton(
            name="ShipB",
            route=list(range(14, -1, -1)),  # s14 → s0
            sigma=0.05,
            initial_sector=14,
            initial_v=1.0
        )
        
        self.traffic_light = TrafficLightAutomaton()
        
        self.solver = Solver()
        
    def get_initial_state(self) -> And:
        """
        Estado inicial do sistema
        """
        return And(
            # Navio A começa em s0
            self.ship_A.sector == 0,
            self.ship_A.tau == 0,
            self.ship_A.v == self.ship_A.initial_v,
            self.ship_A.z == 0,
            
            # Navio B começa em s14
            self.ship_B.sector == 14,
            self.ship_B.tau == 0,
            self.ship_B.v == self.ship_B.initial_v,
            self.ship_B.z == 0,
            
            # Semáforo
            self.traffic_light.t == 0,
            self.traffic_light.sA == 0,
            self.traffic_light.sB == 14
        )
    
    def get_safety_sufficient_condition(self) -> Bool:
        """
        Condição de segurança suficiente:
        Os dois navios não podem estar no mesmo sector simultaneamente
        """
        return self.ship_A.sector != self.ship_B.sector
    
    def get_safety_strong_condition(self) -> Bool:
        """
        Condição de segurança forte:
        1. Segurança suficiente (não estão no mesmo sector)
        2. Nenhum navio é forçado a imobilizar-se aguardando o outro
        """
        # Segurança suficiente
        sufficient = self.get_safety_sufficient_condition()
        
        # Nenhum navio parado indefinidamente
        # (ambos devem poder progredir ou estar em velocidade positiva)
        no_deadlock_A = Or(
            self.ship_A.v > 0,
            self.ship_A.sector == 14  # Chegou ao destino
        )
        
        no_deadlock_B = Or(
            self.ship_B.v > 0,
            self.ship_B.sector == 0  # Chegou ao destino
        )
        
        return And(sufficient, no_deadlock_A, no_deadlock_B)
    
    def transition_relation(self, curr_state: Dict, next_state: Dict) -> And:
        """
        Relação de transição entre estados
        """
        constraints = []
        
        # Transição do navio A
        curr_sector_A = curr_state['ship_A_sector']
        next_sector_A = next_state['ship_A_sector']
        
        # Se o navio A pode transitar (sinal verde ou amarelo)
        curr_sector_B = curr_state['ship_B_sector']
        
        # Verificar se pode transitar
        can_transit_A = next_sector_A != curr_sector_B
        
        # Se transita, sector incrementa; senão permanece
        if curr_sector_A < 14:
            constraints.append(
                If(can_transit_A,
                   next_sector_A == curr_sector_A + 1,
                   next_sector_A == curr_sector_A)
            )
        else:
            constraints.append(next_sector_A == curr_sector_A)
        
        # Similar para navio B (direção oposta)
        next_sector_B = next_state['ship_B_sector']
        can_transit_B = next_sector_B != curr_state['ship_A_sector']
        
        if curr_sector_B > 0:
            constraints.append(
                If(can_transit_B,
                   next_sector_B == curr_sector_B - 1,
                   next_sector_B == curr_sector_B)
            )
        else:
            constraints.append(next_sector_B == curr_sector_B)
        
        # Atualizar semáforo
        constraints.append(next_state['TL_sA'] == next_sector_A)
        constraints.append(next_state['TL_sB'] == next_sector_B)
        constraints.append(next_state['TL_t'] == curr_state['TL_t'] + 1)
        
        return And(constraints)

# ============================================================================
# VERIFICAÇÃO DE SEGURANÇA
# ============================================================================

class SafetyVerifier:
    """
    Verificador de segurança usando BMC e k-indução
    """
    def __init__(self, system: HybridSystem):
        self.system = system
        
    def bounded_model_checking(self, k: int, strong: bool = False) -> Tuple[str, List]:
        """
        Bounded Model Checking (BMC)
        Verifica se existe uma violação de segurança em até k passos
        
        Retorna: ("SAFE" ou "UNSAFE", contraexemplo)
        """
        print(f"\n{'='*70}")
        print(f"BMC - Verificação com k={k} ({'Segurança Forte' if strong else 'Segurança Suficiente'})")
        print(f"{'='*70}")
        
        solver = Solver()
        
        # Criar variáveis para cada passo
        states = []
        for i in range(k + 1):
            state = {
                'ship_A_sector': Int(f'sA_sector_{i}'),
                'ship_A_tau': Real(f'sA_tau_{i}'),
                'ship_A_v': Real(f'sA_v_{i}'),
                'ship_A_z': Real(f'sA_z_{i}'),
                'ship_B_sector': Int(f'sB_sector_{i}'),
                'ship_B_tau': Real(f'sB_tau_{i}'),
                'ship_B_v': Real(f'sB_v_{i}'),
                'ship_B_z': Real(f'sB_z_{i}'),
                'TL_t': Real(f'TL_t_{i}'),
                'TL_sA': Int(f'TL_sA_{i}'),
                'TL_sB': Int(f'TL_sB_{i}'),
            }
            states.append(state)
        
        # Estado inicial
        solver.add(states[0]['ship_A_sector'] == 0)
        solver.add(states[0]['ship_B_sector'] == 14)
        solver.add(states[0]['TL_sA'] == 0)
        solver.add(states[0]['TL_sB'] == 14)
        solver.add(states[0]['TL_t'] == 0)
        
        # Restrições básicas
        for i in range(k + 1):
            solver.add(states[i]['ship_A_sector'] >= 0)
            solver.add(states[i]['ship_A_sector'] <= 14)
            solver.add(states[i]['ship_B_sector'] >= 0)
            solver.add(states[i]['ship_B_sector'] <= 14)
            solver.add(states[i]['ship_A_v'] >= 0)
            solver.add(states[i]['ship_B_v'] >= 0)
        
        # Transições
        for i in range(k):
            curr = states[i]
            next_s = states[i + 1]
            
            # Calcular próximos sectores desejados
            next_A_desired = curr['ship_A_sector'] + 1
            next_B_desired = curr['ship_B_sector'] - 1
            
            # REGRA CRÍTICA: Evitar colisão
            # Se ambos querem ir para o mesmo sector, apenas um pode (prioridade A)
            will_collide = And(
                curr['ship_A_sector'] < 14,
                curr['ship_B_sector'] > 0,
                next_A_desired == next_B_desired
            )
            
            # Navio A: avança se sector destino não está ocupado por B
            # E não vai colidir com B no próximo movimento
            can_A_move = And(
                curr['ship_A_sector'] < 14,
                next_A_desired != curr['ship_B_sector'],
                Not(will_collide)  # Se vai colidir, A tem prioridade mas B não move
            )
            
            solver.add(
                If(can_A_move,
                   next_s['ship_A_sector'] == next_A_desired,
                   next_s['ship_A_sector'] == curr['ship_A_sector'])
            )
            
            # Navio B: recua se sector destino não está ocupado por A
            # E não vai colidir com A no próximo movimento
            can_B_move = And(
                curr['ship_B_sector'] > 0,
                next_B_desired != curr['ship_A_sector'],
                Not(will_collide)  # Se vai colidir, B é bloqueado
            )
            
            solver.add(
                If(can_B_move,
                   next_s['ship_B_sector'] == next_B_desired,
                   next_s['ship_B_sector'] == curr['ship_B_sector'])
            )
            
            # Atualizar semáforo
            solver.add(next_s['TL_sA'] == next_s['ship_A_sector'])
            solver.add(next_s['TL_sB'] == next_s['ship_B_sector'])
            solver.add(next_s['TL_t'] == curr['TL_t'] + 1)
        
        # Procurar violação de segurança em algum passo
        violation_found = False
        for i in range(k + 1):
            solver.push()
            
            # Adicionar negação da propriedade de segurança
            if strong:
                # Segurança forte: não podem estar no mesmo sector E não podem estar bloqueados
                solver.add(Or(
                    states[i]['ship_A_sector'] == states[i]['ship_B_sector'],
                    And(states[i]['ship_A_sector'] < 14,
                        states[i]['ship_A_sector'] + 1 == states[i]['ship_B_sector'],
                        states[i]['ship_B_sector'] > 0,
                        states[i]['ship_B_sector'] - 1 == states[i]['ship_A_sector'])
                ))
            else:
                # Segurança suficiente: não podem estar no mesmo sector
                solver.add(states[i]['ship_A_sector'] == states[i]['ship_B_sector'])
            
            result = solver.check()
            
            if result == sat:
                print(f"❌ UNSAFE: Violação encontrada no passo {i}")
                model = solver.model()
                
                # Extrair contraexemplo
                counterexample = []
                for j in range(i + 1):
                    step = {
                        'step': j,
                        'ship_A_sector': model.eval(states[j]['ship_A_sector']),
                        'ship_B_sector': model.eval(states[j]['ship_B_sector'])
                    }
                    counterexample.append(step)
                    print(f"  Passo {j}: Navio A em s{step['ship_A_sector']}, "
                          f"Navio B em s{step['ship_B_sector']}")
                
                solver.pop()
                return ("UNSAFE", counterexample)
            
            solver.pop()
        
        print(f"✓ SAFE: Nenhuma violação encontrada até k={k}")
        return ("SAFE", [])
    
    def k_induction(self, k: int, strong: bool = False) -> str:
        """
        Verificação usando k-indução
        
        Base case: BMC até k
        Inductive step: assumir propriedade para k passos, provar para k+1
        """
        print(f"\n{'='*70}")
        print(f"K-INDUÇÃO - Verificação com k={k} ({'Segurança Forte' if strong else 'Segurança Suficiente'})")
        print(f"{'='*70}")
        
        # Passo base: BMC
        print("\n[Passo Base]")
        result, _ = self.bounded_model_checking(k, strong)
        if result == "UNSAFE":
            return "UNSAFE"
        
        # Passo indutivo
        print("\n[Passo Indutivo]")
        solver = Solver()
        
        # Criar k+1 estados
        states = []
        for i in range(k + 2):
            state = {
                'ship_A_sector': Int(f'ind_sA_sector_{i}'),
                'ship_B_sector': Int(f'ind_sB_sector_{i}'),
                'TL_t': Real(f'ind_TL_t_{i}'),
            }
            states.append(state)
        
        # Assumir propriedade para os primeiros k passos
        for i in range(k + 1):
            if strong:
                solver.add(states[i]['ship_A_sector'] != states[i]['ship_B_sector'])
                solver.add(Or(
                    states[i]['ship_A_sector'] == 14,
                    states[i]['ship_A_sector'] + 1 != states[i]['ship_B_sector']
                ))
                solver.add(Or(
                    states[i]['ship_B_sector'] == 0,
                    states[i]['ship_B_sector'] - 1 != states[i]['ship_A_sector']
                ))
            else:
                solver.add(states[i]['ship_A_sector'] != states[i]['ship_B_sector'])
            
            # Restrições de domínio
            solver.add(states[i]['ship_A_sector'] >= 0)
            solver.add(states[i]['ship_A_sector'] <= 14)
            solver.add(states[i]['ship_B_sector'] >= 0)
            solver.add(states[i]['ship_B_sector'] <= 14)
        
        # Adicionar transições
        for i in range(k + 1):
            curr = states[i]
            next_s = states[i + 1]
            
            # Calcular próximos sectores
            next_A_desired = curr['ship_A_sector'] + 1
            next_B_desired = curr['ship_B_sector'] - 1
            
            # Evitar colisão: se ambos querem mesmo sector, dar prioridade a A
            will_collide = And(
                curr['ship_A_sector'] < 14,
                curr['ship_B_sector'] > 0,
                next_A_desired == next_B_desired
            )
            
            # Navio A pode mover se não ocupado por B e não vai colidir
            can_A_move = And(
                curr['ship_A_sector'] < 14,
                next_A_desired != curr['ship_B_sector'],
                Not(will_collide)
            )
            
            solver.add(
                If(can_A_move,
                   next_s['ship_A_sector'] == next_A_desired,
                   next_s['ship_A_sector'] == curr['ship_A_sector'])
            )
            
            # Navio B pode mover se não ocupado por A e não vai colidir
            can_B_move = And(
                curr['ship_B_sector'] > 0,
                next_B_desired != curr['ship_A_sector'],
                Not(will_collide)  # B é bloqueado em caso de colisão
            )
            
            solver.add(
                If(can_B_move,
                   next_s['ship_B_sector'] == next_B_desired,
                   next_s['ship_B_sector'] == curr['ship_B_sector'])
            )
        
        # Tentar provar que a propriedade NÃO vale no passo k+1
        if strong:
            solver.add(Or(
                states[k + 1]['ship_A_sector'] == states[k + 1]['ship_B_sector'],
                And(states[k + 1]['ship_A_sector'] < 14,
                    states[k + 1]['ship_A_sector'] + 1 == states[k + 1]['ship_B_sector'],
                    states[k + 1]['ship_B_sector'] > 0,
                    states[k + 1]['ship_B_sector'] - 1 == states[k + 1]['ship_A_sector'])
            ))
        else:
            solver.add(states[k + 1]['ship_A_sector'] == states[k + 1]['ship_B_sector'])
        
        result = solver.check()
        
        if result == unsat:
            print(f"✓ SAFE: Propriedade provada por {k}-indução")
            return "SAFE"
        else:
            print(f"? UNKNOWN: Não foi possível provar por {k}-indução")
            print(f"  (Pode ser necessário aumentar k)")
            return "UNKNOWN"

# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def main():
    """
    Função principal do programa
    """
    print("="*70)
    print("TRABALHO PRÁTICO 4")
    print("Verificação de Propriedades de Segurança em Sistemas Híbridos")
    print("Controle de Tráfego Marítimo")
    print("="*70)
    
    # Criar o sistema híbrido
    print("\n[1] Criando autómatos híbridos...")
    system = HybridSystem()
    print(f"  ✓ Navio A: rota {system.ship_A.route}")
    print(f"  ✓ Navio B: rota {system.ship_B.route}")
    print(f"  ✓ Semáforo de controle")
    
    # Criar FOTS
    print("\n[2] Construindo FOTS (First-Order Transition System)...")
    print(f"  ✓ Sistema híbrido global criado")
    print(f"  ✓ Predicado de segurança suficiente: sA ≠ sB")
    print(f"  ✓ Predicado de segurança forte: sA ≠ sB ∧ sem deadlock")
    
    # Criar verificador
    verifier = SafetyVerifier(system)
    
    # Verificação de segurança
    print("\n[3] Verificação de Segurança...")
    
    # BMC - Segurança Suficiente
    k_values = [10, 20, 30]
    
    for k in k_values:
        result_sufficient, _ = verifier.bounded_model_checking(k, strong=False)
        if result_sufficient == "UNSAFE":
            break
    
    # BMC - Segurança Forte
    for k in k_values:
        result_strong, _ = verifier.bounded_model_checking(k, strong=True)
        if result_strong == "UNSAFE":
            break
    
    # K-indução - Segurança Suficiente
    for k in [3, 5, 7]:
        result = verifier.k_induction(k, strong=False)
        if result == "SAFE":
            break
    
    # K-indução - Segurança Forte
    for k in [3, 5, 7]:
        result = verifier.k_induction(k, strong=True)
        if result == "SAFE":
            break
    
    print("\n" + "="*70)
    print("VERIFICAÇÃO CONCLUÍDA")
    print("="*70)

if __name__ == "__main__":
    main()