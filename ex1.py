import networkx as nx
import matplotlib.pyplot as plt
from ortools.linear_solver import pywraplp

class SistemaDistribuicao:
    def __init__(self):
        self.G = nx.DiGraph()
        self.capacidade_veiculo = 10
        self.tipos_pacotes = {1: 1, 2: 2, 5: 5}  # tipo: unidades
        
    def criar_rede(self):
        """Cria a rede de distribuição"""
        # Sources (armazéns)
        self.G.add_node('S1', type='source', color='green', stock=40, veiculos=8)
        self.G.add_node('S2', type='source', color='green', stock=45, veiculos=9)
        
        # Pontos de passagem
        self.G.add_node('H1', type='passagem', color='lightblue')
        self.G.add_node('H2', type='passagem', color='lightblue')
        self.G.add_node('P1', type='passagem', color='skyblue')
        self.G.add_node('P2', type='passagem', color='skyblue')
       
        # Sinks (destinos)
        self.G.add_node('D1', type='sink', color='red')
        self.G.add_node('D2', type='sink', color='red')
        self.G.add_node('D3', type='sink', color='red')
        self.G.add_node('D4', type='sink', color='red')
       
        # Vias bidirecionais (origem, destino, capacidade)
        vias = [
            ('S1', 'H1', 12), ('S1', 'H2', 9), ('S1', 'P1', 7),
            ('S2', 'H1', 10), ('S2', 'P2', 8),
            ('H1', 'H2', 9), ('H1', 'P1', 8), ('H1', 'P2', 9),
            ('H2', 'P1', 6),
            ('P1', 'P2', 6), ('P1', 'D1', 7), ('P1', 'D2', 6),
            ('P2', 'D2', 7), ('P2', 'D3', 8), ('P2', 'D4', 9),
            ('H1', 'D1', 5), ('H1', 'D3', 6), ('H2', 'D2', 4),
            ('D1', 'D2', 4), ('D3', 'D4', 5),
        ]
        
        for orig, dest, cap in vias:
            self.G.add_edge(orig, dest, capacity=cap)
            self.G.add_edge(dest, orig, capacity=cap)
    
    def visualizar_rede(self):
        """Visualiza o grafo da rede"""
        sources = [n for n in self.G.nodes if self.G.nodes[n]['type'] == 'source']
        sinks = [n for n in self.G.nodes if self.G.nodes[n]['type'] == 'sink']
        passagem = [n for n in self.G.nodes if self.G.nodes[n]['type'] == 'passagem']
        
        pos = {}
        for i, node in enumerate(sources):
            pos[node] = (i * 2, 3)
        
        hubs = [n for n in passagem if n.startswith('H')]
        intermedios = [n for n in passagem if n.startswith('P')]
        
        for i, node in enumerate(hubs):
            pos[node] = (i * 2.5 + 0.5, 2)
        for i, node in enumerate(intermedios):
            pos[node] = (i * 2 + 1, 1)
        for i, node in enumerate(sinks):
            pos[node] = (i * 1.5 + 0.5, 0)
        
        plt.figure(figsize=(14, 10))
        
        edges = self.G.edges()
        capacities = [self.G[u][v]['capacity'] for u, v in edges]
        max_cap = max(capacities)
        widths = [2 + (cap / max_cap) * 3 for cap in capacities]
        
        node_colors = [self.G.nodes[n]['color'] for n in self.G.nodes]
        
        nx.draw_networkx_edges(self.G, pos, width=widths, alpha=0.6, 
                              edge_color='gray', arrows=True, arrowsize=15)
        nx.draw_networkx_nodes(self.G, pos, node_color=node_colors, 
                              node_size=1200, edgecolors='black', linewidths=2)
        nx.draw_networkx_labels(self.G, pos, font_size=9, font_weight='bold')
        
        edge_labels = {}
        edges_processed = set()
        for u, v in self.G.edges():
            if (v, u) not in edges_processed:
                edge_labels[(u, v)] = self.G[u][v]['capacity']
                edges_processed.add((u, v))
        
        nx.draw_networkx_edge_labels(self.G, pos, edge_labels=edge_labels, 
                                    font_size=7, bbox=dict(boxstyle="round,pad=0.2", 
                                    facecolor="white", alpha=0.8))
        
        plt.title("Rede de Distribuição", fontsize=14, fontweight='bold')
        plt.axis('off')
        plt.tight_layout()
        plt.show()
    
    def resolver_encomenda(self, encomenda):
        """Resolve o problema de otimização para uma encomenda"""
        destino = encomenda['destino']
        pacotes_pedidos = encomenda['pacotes']
        
        unidades_necessarias = sum(self.tipos_pacotes[tipo] * qtd 
                                   for tipo, qtd in pacotes_pedidos.items())
        
        print(f"DESTINO: {destino} \nPacotes: {pacotes_pedidos} | Total de Unidades: {unidades_necessarias}")
        
        solver = pywraplp.Solver.CreateSolver('SCIP')
        if not solver:
            return None
        
        sources = [n for n in self.G.nodes if self.G.nodes[n]['type'] == 'source']
        
        # Variáveis
        x = {}  # x[source, tipo] = qtd de pacotes tipo do source
        for s in sources:
            for tipo in self.tipos_pacotes:
                x[(s, tipo)] = solver.IntVar(0, solver.infinity(), f'x_{s}_{tipo}')
        
        y = {}  # y[source] = número de veículos do source
        for s in sources:
            y[s] = solver.IntVar(0, solver.infinity(), f'y_{s}')
        
        z = {}  # z[source] = 1 se source usado, 0 caso contrário
        for s in sources:
            z[s] = solver.BoolVar(f'z_{s}')
        
        # Restrições
        # 1. Atender demanda
        for tipo, qtd_pedida in pacotes_pedidos.items():
            solver.Add(sum(x[(s, tipo)] for s in sources) == qtd_pedida)
        
        # 2. Capacidade dos veículos (10 unidades)
        for s in sources:
            unidades_source = sum(self.tipos_pacotes[tipo] * x[(s, tipo)] 
                                 for tipo in self.tipos_pacotes)
            solver.Add(unidades_source <= self.capacidade_veiculo * y[s])
        
        # 3. Limite de stock
        for s in sources:
            unidades_source = sum(self.tipos_pacotes[tipo] * x[(s, tipo)] 
                                 for tipo in self.tipos_pacotes)
            solver.Add(unidades_source <= self.G.nodes[s]['stock'])
        
        # 4. Limite de veículos
        for s in sources:
            solver.Add(y[s] <= self.G.nodes[s]['veiculos'])
        
        # 5. Ligar z a y
        for s in sources:
            solver.Add(y[s] <= 1000 * z[s])
        
        # 6. Capacidade das vias
        for s in sources:
            if nx.has_path(self.G, s, destino):
                caminho = nx.shortest_path(self.G, s, destino)
                for i in range(len(caminho) - 1):
                    edge_cap = self.G[caminho[i]][caminho[i+1]]['capacity']
                    solver.Add(y[s] <= edge_cap)
        
        # Objetivo: minimizar veículos
        solver.Minimize(sum(y[s] for s in sources))
        
        status = solver.Solve()
        
        if status == pywraplp.Solver.OPTIMAL:
            print(f"\nSolução ótima: {int(solver.Objective().Value())} veículos\n")
            
            # 1. Sources envolvidos
            print("1. SOURCES ENVOLVIDOS:")
            for s in sources:
                if z[s].solution_value() > 0.5:
                    unidades = sum(self.tipos_pacotes[tipo] * int(x[(s, tipo)].solution_value()) 
                                  for tipo in self.tipos_pacotes)
                    stock_disp = self.G.nodes[s]['stock']
                    print(f"   [{s}]: {unidades}/{stock_disp} unidades (restante: {stock_disp - unidades})")
            
            # 2. Empacotamento
            print("\n2. EMPACOTAMENTO E ROTAS POR VEÍCULO:")
            veiculo_id = 1
            for s in sources:
                if z[s].solution_value() > 0.5:
                    num_veiculos = int(y[s].solution_value())
                    
                    pacotes = []
                    for tipo in self.tipos_pacotes:
                        qtd = int(x[(s, tipo)].solution_value())
                        pacotes.extend([tipo] * qtd)
                    
                    # Distribuir pacotes pelos veículos
                    pacotes_por_veiculo = [[] for _ in range(num_veiculos)]
                    unidades_por_veiculo = [0] * num_veiculos
                    
                    for pacote in sorted(pacotes, reverse=True):
                        idx = unidades_por_veiculo.index(min(unidades_por_veiculo))
                        pacotes_por_veiculo[idx].append(pacote)
                        unidades_por_veiculo[idx] += self.tipos_pacotes[pacote]
                    
                    for i in range(num_veiculos):
                        print(f"   V{veiculo_id} [{s}]: {pacotes_por_veiculo[i]} = {unidades_por_veiculo[i]} unidades")
                        veiculo_id += 1
            
            # 3. Rotas e capacidades
            print("\n3. ROTAS E CAPACIDADE DAS VIAS:")
            for s in sources:
                if z[s].solution_value() > 0.5:
                    num_veiculos = int(y[s].solution_value())
                    caminho = nx.shortest_path(self.G, s, destino)
                    
                    print(f"{' → '.join(caminho)} ({num_veiculos} veículos)")
                    
                    for i in range(len(caminho) - 1):
                        cap = self.G[caminho[i]][caminho[i+1]]['capacity']
                        ok = "✓" if num_veiculos <= cap else "✗"
                        print(f"      {caminho[i]}→{caminho[i+1]}: {num_veiculos}/{cap} {ok}")
            
            print("\n")
            return True
        else:
            print("\n✗ Sem solução ótima (capacidade/stock insuficiente)\n")
            return None


# Execução
if __name__ == "__main__":
    sistema = SistemaDistribuicao()
    sistema.criar_rede()
    sistema.visualizar_rede()
    
    # Teste 1
    encomenda1 = {
        'destino': 'D1',
        'pacotes': {1: 3, 2: 2, 5: 1}  # 12 unidades
    }
    sistema.resolver_encomenda(encomenda1)
    
    # Teste 2
    encomenda2 = {
        'destino': 'D4',
        'pacotes': {1: 5, 2: 3, 5: 2}  # 21 unidades
    }
    sistema.resolver_encomenda(encomenda2)