import math
import random

# ==============================================================================
# 1. MAPAS COMPLETOS (Com todas as opções, como no enunciado)
# ==============================================================================
# O código vai escolher aleatoriamente quando houver bifurcação (ex: s11 -> s5 ou s7)

MAPA_A = {
    11: [(5, 1, 0), (7, 0.707, -0.707)], 
    13: [(9, 1, 0), (7, 0.707, 0.707)],
    5: [(1, 0.707, -0.707)], 
    7: [(1, 0.707, 0.707), (3, 0.707, -0.707)], 
    9: [(3, 0.707, 0.707)],
    1: [(0, 1, 0)], 3: [(0, 1, 0)],
    0: [(2, 0.707, 0.707), (4, 0.707, -0.707)],
    2: [(6, 1, 0), (8, 0.707, -0.707)], 
    4: [(10, 1, 0), (8, 0.707, 0.707)],
    6: [(12, 1, 0)], 
    8: [(12, 0.707, 0.707), (14, 0.707, -0.707)], 
    10: [(14, 1, 0)],
    12: [(99, 1, 0)], 14: [(99, 1, 0)], 99: [(99, 0, 0)]
}

MAPA_B = {
    12: [(6, -1, 0), (8, -0.707, -0.707)], 
    14: [(10, -1, 0), (8, -0.707, 0.707)],
    6: [(2, -1, 0)], 8: [(2, -0.707, 0.707), (4, -0.707, -0.707)], 10: [(4, -1, 0)],
    2: [(0, -0.707, -0.707)], 4: [(0, -0.707, 0.707)],
    0: [(1, -0.707, 0.707), (3, -0.707, -0.707)],
    1: [(5, -0.707, 0.707), (7, -0.707, -0.707)], 
    3: [(9, -0.707, -0.707), (7, -0.707, 0.707)],
    5: [(11, -1, 0)], 7: [(11, -0.707, 0.707), (13, -0.707, -0.707)], 9: [(13, -1, 0)],
    11: [(98, -1, 0)], 13: [(98, -1, 0)], 98: [(98, 0, 0)]
}

# ==============================================================================
# 2. CONFIGURAÇÃO
# ==============================================================================
SIGMA, V_LIM, EPSILON = 0.5, 1.2, 0.1
DT = 0.25
STEPS = 200 # Bastantes passos para garantir chegada

ZONAS_ACEL_A = {11, 13, 2, 4}
ZONAS_DECEL_A = {1, 3, 12, 14}
ZONAS_ACEL_B = {1, 3, 12, 14}
ZONAS_DECEL_B = {11, 13, 2, 4}

# ==============================================================================
# 3. CLASSE DE SIMULAÇÃO (Representa o FOTS)
# ==============================================================================
class Navio:
    def __init__(self, nome, s, v, z, x, y, dx, dy, mapa, zonas_acel, zonas_decel):
        self.nome = nome
        self.s = s
        self.v = v
        self.z = z
        self.x, self.y = x, y
        self.dx, self.dy = dx, dy
        self.mapa = mapa
        self.acel = zonas_acel
        self.decel = zonas_decel
        self.finished = False

    def get_gamma(self):
        if self.s == 0: return 0.2
        if self.s in self.acel: return 1.0
        if self.s in self.decel: return 0.0
        return 0.5

    def physics(self):
        # EDO: v' = v + (Força - sigma*v)*dt
        force = self.get_gamma() if self.v <= V_LIM else EPSILON
        self.v += (force - SIGMA * self.v) * DT

    def wait(self):
        # Lógica de espera (Segurança Forte): Atrito atua, z não mexe
        self.v -= (SIGMA * self.v) * DT
        if self.v < 0: self.v = 0

    def step(self, other_s):
        # 1. Tentar JUMP
        if self.z >= 1.0 and not self.finished:
            opcoes = self.mapa.get(self.s, [])
            
            # Filtro do Semáforo: Só destinos onde o outro navio NÃO está
            validas = []
            for (dst, ddx, ddy) in opcoes:
                if dst != other_s: # Semáforo Verde
                    validas.append((dst, ddx, ddy))
            
            if validas:
                # AQUI ESTÁ A TUA IDEIA: Escolhe UM agora!
                # Se houver mais que um, escolhe aleatoriamente (dinâmico)
                novo_s, novo_dx, novo_dy = random.choice(validas)
                
                print(f"   >>> {self.nome} JUMP: s{self.s} -> s{novo_s} (Opções: {len(validas)})")
                
                self.s = novo_s
                self.dx, self.dy = novo_dx, novo_dy
                self.z = 0.0
                # Reset visual coords para ficar bonito no gráfico
                if self.dx > 0: self.x = 0.0
                elif self.dx < 0: self.x = 1.0
                if self.dy > 0: self.y = 0.0
                elif self.dy < 0: self.y = 1.0
                
                # Chegou ao Porto?
                if self.s in [98, 99]: self.finished = True
                return # Fez jump, não faz flow neste tick

            else:
                # Semáforo Vermelho (bloqueado) -> Wait Logic
                self.wait()
                return

        # 2. Se não saltou, faz FLOW
        if not self.finished:
            self.physics()
            self.z += self.v * DT
            # Atualizar x,y visualmente
            self.x += self.v * DT * self.dx
            self.y += self.v * DT * self.dy
        else:
            self.v = 0 # Parado no porto

# ==============================================================================
# 4. LOOP PRINCIPAL (A tua ideia de "olhar e escolher")
# ==============================================================================
def main():
    print("--- INICIANDO SIMULAÇÃO DINÂMICA (INSTANTÂNEA) ---")
    
    # Init Assimétrico para evitar deadlock no s0
    # Navio A sai de s11 (Cima)
    nav_a = Navio("A", 11, 0.6, 0.0, 0.0, 1.0, 1, 0, MAPA_A, ZONAS_ACEL_A, ZONAS_DECEL_A)
    # Navio B sai de s14 (Baixo)
    nav_b = Navio("B", 14, 0.0, 0.0, 1.0, 0.0, -1, 0, MAPA_B, ZONAS_ACEL_B, ZONAS_DECEL_B)

    print("\n" + "="*95)
    print(f"{'T':<5} | {'NAVIO A (Setor, x, y)':<35} | {'NAVIO B (Setor, x, y)':<35}")
    print("="*95)

    rota_a = []
    rota_b = []

    for t_step in range(STEPS):
        time = t_step * DT
        
        # Guardar estado atual para print
        pos_a = f"s{nav_a.s:<2} ({nav_a.x:5.2f}, {nav_a.y:5.2f})"
        pos_b = f"s{nav_b.s:<2} ({nav_b.x:5.2f}, {nav_b.y:5.2f})"
        
        # Log da rota (apenas quando muda)
        if len(rota_a) == 0 or rota_a[-1] != str(nav_a.s): rota_a.append(str(nav_a.s))
        if len(rota_b) == 0 or rota_b[-1] != str(nav_b.s): rota_b.append(str(nav_b.s))

        # Print (a cada 1 segundo ou se houver evento)
        # Nota: Os prints de JUMP acontecem dentro da classe
        if t_step % 4 == 0: 
            print(f"{time:<5.1f} | {pos_a:<35} | {pos_b:<35}")

        # --- A MAGIA: OLHAR O PRÓXIMO PASSO E ESCOLHER ---
        # Passamos o setor do outro navio para verificar o semáforo
        nav_a.step(nav_b.s)
        nav_b.step(nav_a.s)
        
        # Critério de paragem
        if nav_a.finished and nav_b.finished:
            print("\n!!! AMBOS CHEGARAM AO DESTINO !!!")
            break

    print("="*95)
    print(f"Rota A: {' -> '.join(rota_a)}")
    print(f"Rota B: {' -> '.join(rota_b)}")

if __name__ == "__main__":
    main()

#falta mudar inicio e angulo de entrada e numero fim (pelo menos isto)