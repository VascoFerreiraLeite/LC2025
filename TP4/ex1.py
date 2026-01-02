import numpy as np

# --- CONFIGURAÇÕES ---
# Zonas baseadas na Rota A -> B (Navio A)
ZONAS_ACEL_A = {'s11', 's13', 's2', 's4'}
ZONAS_DECEL_A = {'s1', 's3', 's12', 's14'}
ZONA_BAIXA = {'s0'}

# Mapa de Adjacência (Grafo do Canal)
# Para o Navio A (esquerda para direita)
MAPA_A = {
    # Saída do Porto A (Entrada no Canal)
    # s11 pode ir para cima (s5) ou meio (s7)
    's11': ['s5', 's7'], 
    # s13 pode ir para baixo (s9) ou meio (s7)
    's13': ['s9', 's7'],
    
    # Zona Intermédia (3 faixas) -> Estreito (2 faixas)
    's5': ['s1'], 
    's7': ['s1', 's3'], # O meio pode ir para qualquer um dos dois do estreito
    's9': ['s3'],
    
    # Estreito
    's1': ['s0'], 's3': ['s0'], 
    's0': ['s2', 's4'],
    
    # Saída do Estreito para a Direita
    's2': ['s6', 's8'], # Pode ir para cima ou meio
    's4': ['s8', 's10'], # Pode ir para meio ou baixo
    
    # Zona Final Direita -> Porto B
    's6': ['s12'], 
    's8': ['s12', 's14'], 
    's10': ['s14'],
    
    # Chegada
    's12': ['PORTO_B'], 's14': ['PORTO_B']
}

# Mapa Reverso para o Navio B (direita para esquerda)
# Basicamente inverte as setas do mapa acima
MAPA_B = {
    # Começo da viagem (Lado do Porto B)
    's12': ['s6'], 's14': ['s10', 's8'], 
    
    # Zona intermédia direita
    's6': ['s2'], 's8': ['s2', 's4'], 's10': ['s4'],
    
    # Aproximação ao estreito
    's2': ['s0'], 's4': ['s0'],
    
    # Estreito
    's0': ['s1', 's3'],
    
    # Saída do estreito (lado esquerdo)
    's1': ['s5', 's7'], 's3': ['s7', 's9'],
    
    # Dos setores intermédios, ele vai para os da ponta (s11, s13)
    's5': ['s11'], 
    's7': ['s11', 's13'], # Assumindo que o s7 conecta aos dois
    's9': ['s13'],
    
    # Finalmente, dos setores da ponta para o Porto A
    's11': ['PORTO_A'], 
    's13': ['PORTO_A']
}

class Navio:
    def __init__(self, nome, mapa, rota_invertida, setor_inicial):
        self.nome = nome
        self.mapa = mapa
        self.invertido = rota_invertida 
        self.tau = 0.0 
        self.v = 0.0   
        self.z = 0.0   
        self.setor_atual = setor_inicial
        self.finalizado = False # Nova flag para saber se chegou

    def get_parametros_setor(self):
        s = self.setor_atual
        if self.finalizado: return 0
        
        # Parâmetros físicos (Aceleração vs Desaceleração)
        gamma_acel = 1.0
        gamma_decel = 0.0
        
        # Lógica: Se é Navio B, inverte o conceito de zona
        e_zona_acel_a = s in ZONAS_ACEL_A
        e_zona_decel_a = s in ZONAS_DECEL_A
        
        acelerar = False
        if not self.invertido: # Navio A
            if e_zona_acel_a: acelerar = True
        else: # Navio B (troca)
            if e_zona_decel_a: acelerar = True # Onde A trava, B acelera
            
        if s in ZONA_BAIXA: return 0.2
        return gamma_acel if acelerar else gamma_decel

    def flow(self, dt):
        if self.finalizado: return # Se acabou, não calcula física
        
        gamma = self.get_parametros_setor()
        sigma = 0.5
        
        self.tau += dt
        self.z += self.v * dt
        
        # Equação diferencial simples: v' = gamma - sigma*v
        dv = gamma - (sigma * self.v)
        self.v += dv * dt
        if self.v < 0: self.v = 0

    def check_guard(self):
        if self.finalizado: return False
        return self.z >= 1.0 # Guarda: percorreu 1km

    def jump(self, novo_setor):
        print(f"--- JUMP: {self.nome} mudou de {self.setor_atual} para {novo_setor} ---")
        self.setor_atual = novo_setor
        self.z = 0.0
        self.tau = 0.0
        # Verifica se chegou a QUALQUER porto
        if novo_setor in ['PORTO_A', 'PORTO_B']: 
            self.finalizado = True
            self.v = 0

# --- SIMULAÇÃO ---
def simular():
    # Configuração Inicial
    navio_a = Navio("Navio A", MAPA_A, False, 's11') # A sai de s11
    navio_b = Navio("Navio B", MAPA_B, True, 's14')  # B sai de s14
    
    dt = 0.1
    tempo = 0
    max_tempo = 25 
    
    print(f"Simulação: A em {navio_a.setor_atual} -> B | B em {navio_b.setor_atual} -> A")

    while tempo < max_tempo:
        # 1. Física
        navio_a.flow(dt)
        navio_b.flow(dt)
        tempo += dt
        
        # 2. Lógica de Transição (JUMPS)
        # Navio A tenta mover
        if navio_a.check_guard():
            vizinhos = navio_a.mapa.get(navio_a.setor_atual, [])
            if vizinhos:
                proximo = vizinhos[0] # Pega o primeiro caminho possível
                # SEMÁFORO: Só vai se B não estiver lá
                if proximo != navio_b.setor_atual:
                    navio_a.jump(proximo)
                else:
                    navio_a.v = 0 # Espera (Colisão evitada)

        # Navio B tenta mover
        if navio_b.check_guard():
            vizinhos = navio_b.mapa.get(navio_b.setor_atual, [])
            if vizinhos:
                proximo = vizinhos[0]
                # SEMÁFORO: Só vai se A não estiver lá
                if proximo != navio_a.setor_atual:
                    navio_b.jump(proximo)
                else:
                    navio_b.v = 0 

        # Logs (apenas se não estiverem ambos finalizados)
        if int(tempo/dt) % 10 == 0:
            status_a = "FIM" if navio_a.finalizado else f"{navio_a.setor_atual} (z={navio_a.z:.2f})"
            status_b = "FIM" if navio_b.finalizado else f"{navio_b.setor_atual} (z={navio_b.z:.2f})"
            print(f"t={tempo:.1f} | A: {status_a} | B: {status_b}")
            
        if navio_a.finalizado and navio_b.finalizado:
            print("\nAmbos os navios chegaram ao destino!")
            break

if __name__ == "__main__":
    simular()