import networkx as nx
import matplotlib.pyplot as plt
from ortools.linear_solver import pywraplp

class SistemaDistribuicao:
    def __init__(self):
        self.G = nx.DiGraph()
        self.capacidade_veiculo = 10
        self.tipos_pacotes = {1: 1, 2: 2, 5: 5}  # tipo: unidades
        
    def criar_rede(self):
        """Método padrão - cria a rede complexa por defeito"""
        self.criar_rede_complexa()
    
    def criar_rede_simples(self):
        """Cria uma rede simples para testes básicos"""
        # Adicionar pontos de fornecimento (sources)
        self.G.add_node('A', type='source', color='green', stock=float('inf'), veiculos=float('inf'))
        
        # Adicionar pontos de passagem
        self.G.add_node('B', type='passagem', color='blue')
        
        # Adicionar pontos de entrega (sinks)
        self.G.add_node('C', type='sink', color='red', stock=10, veiculos=4)
        self.G.add_node('D', type='sink', color='red', stock=7, veiculos=5)
        
        # Adicionar vias bidirecionais com capacidades
        vias = [
            ('A', 'B', 10),
            ('B', 'C', 7),
            ('C', 'D', 10),
            ('A', 'C', 5)
        ]
        
        for orig, dest, cap in vias:
            self.G.add_edge(orig, dest, capacity=cap)
            self.G.add_edge(dest, orig, capacity=cap)
    
    def criar_rede_complexa(self):
        """Cria uma rede complexa com múltiplos sources, hubs e destinos"""
        # Pontos de fornecimento (sources) - 3 armazéns principais
        self.G.add_node('S1', type='source', color='green', stock=50, veiculos=10, nome='Armazém Norte')
        self.G.add_node('S2', type='source', color='green', stock=60, veiculos=12, nome='Armazém Sul')
        #self.G.add_node('S3', type='source', color='green', stock=40, veiculos=8, nome='Armazém Este')
        
        # Hubs de distribuição (pontos de passagem estratégicos)
        self.G.add_node('H1', type='passagem', color='lightblue', nome='Hub Central')
        self.G.add_node('H2', type='passagem', color='lightblue', nome='Hub Oeste')
        #self.G.add_node('H3', type='passagem', color='lightblue', nome='Hub Leste')
        
        # Pontos intermediários
        self.G.add_node('P1', type='passagem', color='skyblue', nome='Ponto A')
        self.G.add_node('P2', type='passagem', color='skyblue', nome='Ponto B')
        self.G.add_node('P3', type='passagem', color='skyblue', nome='Ponto C')
        #self.G.add_node('P4', type='passagem', color='skyblue', nome='Ponto D')
        
        # Pontos de entrega (sinks) - 6 destinos finais
        self.G.add_node('D1', type='sink', color='red', stock=25, veiculos=5, nome='Cliente A')
        self.G.add_node('D2', type='sink', color='red', stock=30, veiculos=6, nome='Cliente B')
        self.G.add_node('D3', type='sink', color='red', stock=20, veiculos=4, nome='Cliente C')
        self.G.add_node('D4', type='sink', color='red', stock=35, veiculos=7, nome='Cliente D')
        #self.G.add_node('D5', type='sink', color='red', stock=15, veiculos=3, nome='Cliente E')
        #self.G.add_node('D6', type='sink', color='red', stock=28, veiculos=6, nome='Cliente F')
        
        # Vias bidirecionais com capacidades variadas
        # Sources para Hubs principais
        vias = [
            # Conexões dos Armazéns aos Hubs
            ('S1', 'H1', 15),  # Armazém Norte -> Hub Central
            ('S1', 'H2', 10),  # Armazém Norte -> Hub Oeste
            ('S1', 'P1', 8),   # Armazém Norte -> Ponto A
            
            ('S2', 'H1', 12),  # Armazém Sul -> Hub Central
            #('S2', 'H3', 14),  # Armazém Sul -> Hub Leste
            ('S2', 'P2', 9),   # Armazém Sul -> Ponto B
            ('S2', 'P3', 7),
            
            #('S3', 'H3', 13),  # Armazém Este -> Hub Leste
            #('S3', 'H1', 11),  # Armazém Este -> Hub Central
            #('S3', 'P3', 7),   # Armazém Este -> Ponto C
            
            # Interconexões entre Hubs
            ('H1', 'H2', 10),  # Hub Central <-> Hub Oeste
            #('H1', 'H3', 12),  # Hub Central <-> Hub Leste
            #('H2', 'H3', 8),   # Hub Oeste <-> Hub Leste
            
            # Hubs para Pontos intermediários
            ('H1', 'P1', 9),
            ('H1', 'P2', 10),
            ('H2', 'P1', 7),
            #('H2', 'P4', 8),
            #('H3', 'P3', 11),
            #('H3', 'P4', 9),
            
            # Interconexões entre Pontos
            ('P1', 'P2', 6),
            ('P2', 'P3', 7),
            #('P3', 'P4', 6),
            #('P1', 'P4', 5),
            
            # Pontos para Destinos finais
            ('P1', 'D1', 8),
            ('P1', 'D2', 6),
            ('P2', 'D2', 7),
            ('P2', 'D3', 9),
            ('P3', 'D4', 10),
            #('P3', 'D5', 5),
            #('P4', 'D5', 7),
            #('P4', 'D6', 8),
            
            # Algumas conexões diretas de Hubs para Destinos (rotas expressas)
            ('H1', 'D1', 5),   # Rota expressa limitada
            ('H1', 'D3', 6),
            ('H2', 'D2', 4),
            ('H2', 'P3', 7),
            #('H3', 'D4', 7),
            #('H3', 'D6', 6),
            
            # Conexões entre alguns destinos (para rotas alternativas)
            ('D1', 'D2', 4),
            ('D3', 'D4', 5),
            #('D5', 'D6', 4),
        ]
        
        # Adicionar todas as vias bidirecionalmente
        for orig, dest, cap in vias:
            self.G.add_edge(orig, dest, capacity=cap)
            self.G.add_edge(dest, orig, capacity=cap)
    
    def visualizar_rede(self, figsize=(16, 12)):
        """Visualiza o grafo da rede de distribuição"""
        # Usar layout hierarchical para melhor visualização
        # Posicionamento por tipo de nodo
        pos = {}
        
        sources = [n for n in self.G.nodes if self.G.nodes[n]['type'] == 'source']
        sinks = [n for n in self.G.nodes if self.G.nodes[n]['type'] == 'sink']
        passagem = [n for n in self.G.nodes if self.G.nodes[n]['type'] == 'passagem']
        
        # Posicionar em camadas
        y_source = 3
        y_hub = 2
        y_inter = 1
        y_sink = 0
        
        # Sources no topo
        for i, node in enumerate(sources):
            pos[node] = (i * 2, y_source)
        
        # Identificar hubs (nomes começam com H) e pontos intermediários
        hubs = [n for n in passagem if n.startswith('H')]
        intermedios = [n for n in passagem if n.startswith('P')]
        
        # Hubs na camada 2
        for i, node in enumerate(hubs):
            pos[node] = (i * 2.5 + 0.5, y_hub)
        
        # Intermediários na camada 1
        for i, node in enumerate(intermedios):
            pos[node] = (i * 2 + 1, y_inter)
        
        # Sinks na base
        for i, node in enumerate(sinks):
            pos[node] = (i * 1.5 + 0.5, y_sink)
        
        # Se não há estrutura hierárquica, usar spring layout
        if not pos:
            pos = nx.spring_layout(self.G, seed=42, k=2, iterations=50)
        
        node_colors = [self.G.nodes[n]['color'] for n in self.G.nodes]
        
        plt.figure(figsize=figsize)
        
        # Desenhar arestas com diferentes espessuras baseadas na capacidade
        edges = self.G.edges()
        capacities = [self.G[u][v]['capacity'] for u, v in edges]
        max_cap = max(capacities) if capacities else 1
        widths = [2 + (cap / max_cap) * 3 for cap in capacities]
        
        nx.draw_networkx_edges(self.G, pos, width=widths, alpha=1, 
                              edge_color='black', arrows=True, arrowsize=15)
        
        # Desenhar nodos
        nx.draw_networkx_nodes(self.G, pos, node_color=node_colors, 
                              node_size=1500, alpha=1, edgecolors='black', linewidths=2)
        
        # Labels dos nodos
        nx.draw_networkx_labels(self.G, pos, font_size=10, font_weight='bold')
        
        # Rótulos de capacidade nas arestas (apenas num sentido para não duplicar)
        edge_labels = {}
        edges_processed = set()
        for u, v in self.G.edges():
            if (v, u) not in edges_processed:
                edge_labels[(u, v)] = self.G[u][v]['capacity']
                edges_processed.add((u, v))
        
        nx.draw_networkx_edge_labels(self.G, pos, edge_labels=edge_labels, 
                                    font_size=8, bbox=dict(boxstyle="round,pad=0.3", 
                                    facecolor="white", alpha=1))
        
        # Legenda detalhada
        legend_elements = []
        legend_text = ""
        
        
        
        plt.title("Rede de Distribuição Complexa", fontsize=18, fontweight='bold')
        plt.axis('off')
        plt.tight_layout()
        plt.show()
    
    def resolver_encomenda(self, encomenda):
        """
        Resolve o problema de otimização para uma encomenda
        encomenda = {'destino': 'C', 'pacotes': {1: x, 2: y, 5: z}}
        """
        destino = encomenda['destino']
        pacotes_pedidos = encomenda['pacotes']
        
        # Calcular unidades totais necessárias
        unidades_necessarias = sum(self.tipos_pacotes[tipo] * qtd 
                                   for tipo, qtd in pacotes_pedidos.items())
        
        print(f"\n{'='*60}")
        print(f"ENCOMENDA PARA {destino}")
        print(f"{'='*60}")
        print(f"Pacotes pedidos: {pacotes_pedidos}")
        print(f"Unidades necessárias: {unidades_necessarias}")
        
        # Criar solver MIP
        solver = pywraplp.Solver.CreateSolver('SCIP')
        if not solver:
            print("Erro ao criar solver!")
            return None
        
        # Obter todos os sources disponíveis
        sources = [n for n in self.G.nodes if self.G.nodes[n]['type'] == 'source']
        
        # Variáveis de decisão
        # x[source][tipo_pacote] = número de pacotes do tipo fornecidos pelo source
        x = {}
        for s in sources:
            for tipo in self.tipos_pacotes:
                x[(s, tipo)] = solver.IntVar(0, solver.infinity(), f'x_{s}_{tipo}')
        
        # y[source] = número de veículos usados de cada source
        y = {}
        for s in sources:
            y[s] = solver.IntVar(0, solver.infinity(), f'y_{s}')
        
        # z[source] = binária, indica se o source é usado
        z = {}
        for s in sources:
            z[s] = solver.BoolVar(f'z_{s}')
        
        # Restrições
        
        # 1. Atender à demanda de cada tipo de pacote
        for tipo, qtd_pedida in pacotes_pedidos.items():
            solver.Add(sum(x[(s, tipo)] for s in sources) == qtd_pedida)
        
        # 2. Capacidade dos veículos (10 unidades por veículo)
        for s in sources:
            unidades_source = sum(self.tipos_pacotes[tipo] * x[(s, tipo)] 
                                 for tipo in self.tipos_pacotes)
            solver.Add(unidades_source <= self.capacidade_veiculo * y[s])
        
        # 3. Limite de stock do source (se aplicável)
        for s in sources:
            if self.G.nodes[s].get('stock', float('inf')) != float('inf'):
                unidades_source = sum(self.tipos_pacotes[tipo] * x[(s, tipo)] 
                                     for tipo in self.tipos_pacotes)
                solver.Add(unidades_source <= self.G.nodes[s]['stock'])
        
        # 4. Limite de veículos do source
        for s in sources:
            max_veiculos = self.G.nodes[s].get('veiculos', float('inf'))
            if max_veiculos != float('inf'):
                solver.Add(y[s] <= max_veiculos)
        
        # 5. Relacionar z com y (se y > 0, então z = 1)
        for s in sources:
            solver.Add(y[s] <= 1000 * z[s])  # Big M constraint
        
        # 6. Verificar capacidade das vias usando caminhos
        # Para cada source, encontrar caminho até destino e verificar capacidades
        for s in sources:
            if nx.has_path(self.G, s, destino):
                caminho = nx.shortest_path(self.G, s, destino)
                # Adicionar restrição de capacidade para cada aresta no caminho
                for i in range(len(caminho) - 1):
                    edge_cap = self.G[caminho[i]][caminho[i+1]]['capacity']
                    solver.Add(y[s] <= edge_cap)
        
        # Função objetivo: minimizar número total de veículos
        solver.Minimize(sum(y[s] for s in sources))
        
        # Resolver
        status = solver.Solve()
        
        if status == pywraplp.Solver.OPTIMAL:
            print(f"\n{'='*60}")
            print("SOLUCAO OTIMA ENCONTRADA")
            print(f"{'='*60}")
            print(f"Numero total de veiculos necessarios: {int(solver.Objective().Value())}")
            
            resultado = {
                'destino': destino,
                'veiculos_total': int(solver.Objective().Value()),
                'sources_usados': [],
                'rotas': [],
                'veiculos_detalhados': []
            }
            
            print(f"\n{'='*70}")
            print("OBJETIVO 1: SOURCES ENVOLVIDOS NO FORNECIMENTO")
            print(f"{'='*70}")
            
            for s in sources:
                if z[s].solution_value() > 0.5:
                    stock_disponivel = self.G.nodes[s].get('stock', float('inf'))
                    unidades_usadas = sum(self.tipos_pacotes[tipo] * int(x[(s, tipo)].solution_value()) 
                                         for tipo in self.tipos_pacotes)
                    
                    print(f"\n[{s}] - {self.G.nodes[s].get('nome', s)}")
                    print(f"  Stock disponivel: {stock_disponivel}")
                    print(f"  Unidades fornecidas: {unidades_usadas}")
                    print(f"  Stock restante: {stock_disponivel - unidades_usadas if stock_disponivel != float('inf') else 'inf'}")
                    print(f"  Limite de stock respeitado: {'SIM' if unidades_usadas <= stock_disponivel else 'NAO'}")
                    
                    resultado['sources_usados'].append({
                        'source': s,
                        'stock_disponivel': stock_disponivel,
                        'unidades_usadas': unidades_usadas,
                        'limite_respeitado': unidades_usadas <= stock_disponivel
                    })
            
            print(f"\n{'='*70}")
            print("OBJETIVO 2: EMPACOTAMENTO DAS UNIDADES POR VEICULO")
            print(f"{'='*70}")
            
            veiculo_id = 1
            for s in sources:
                if z[s].solution_value() > 0.5:
                    num_veiculos = int(y[s].solution_value())
                    
                    # Coletar pacotes deste source
                    pacotes_disponiveis = []
                    for tipo in self.tipos_pacotes:
                        qtd = int(x[(s, tipo)].solution_value())
                        for _ in range(qtd):
                            pacotes_disponiveis.append(tipo)
                    
                    if pacotes_disponiveis:
                        print(f"\nSource: [{s}] - {num_veiculos} veiculo(s)")
                        print(f"Pacotes a distribuir: {sorted(pacotes_disponiveis)}")
                        
                        # Empacotamento simples (distribuir uniformemente)
                        pacotes_por_veiculo = [[] for _ in range(num_veiculos)]
                        unidades_por_veiculo = [0 for _ in range(num_veiculos)]
                        
                        for pacote in sorted(pacotes_disponiveis, reverse=True):
                            # Colocar no veículo com menos unidades
                            idx_min = unidades_por_veiculo.index(min(unidades_por_veiculo))
                            pacotes_por_veiculo[idx_min].append(pacote)
                            unidades_por_veiculo[idx_min] += self.tipos_pacotes[pacote]
                        
                        for i in range(num_veiculos):
                            print(f"  Veiculo {veiculo_id}:")
                            print(f"    Pacotes: {pacotes_por_veiculo[i]}")
                            print(f"    Total unidades: {unidades_por_veiculo[i]}/10")
                            print(f"    Capacidade respeitada: {'SIM' if unidades_por_veiculo[i] <= 10 else 'NAO'}")
                            
                            resultado['veiculos_detalhados'].append({
                                'id': veiculo_id,
                                'source': s,
                                'pacotes': pacotes_por_veiculo[i],
                                'unidades': unidades_por_veiculo[i],
                                'capacidade_respeitada': unidades_por_veiculo[i] <= 10
                            })
                            veiculo_id += 1
            
            print(f"\n{'='*70}")
            print("OBJETIVO 3: ROTAS DOS VEICULOS E CAPACIDADE DAS VIAS")
            print(f"{'='*70}")
            
            veiculo_id = 1
            for s in sources:
                if z[s].solution_value() > 0.5:
                    num_veiculos = int(y[s].solution_value())
                    
                    if nx.has_path(self.G, s, destino):
                        caminho = nx.shortest_path(self.G, s, destino)
                        
                        print(f"\nSource: [{s}]")
                        print(f"Rota: {' -> '.join(caminho)}")
                        print(f"Numero de veiculos nesta rota: {num_veiculos}")
                        
                        # Verificar capacidade de cada via no caminho
                        print("\nCapacidade das vias:")
                        todas_vias_ok = True
                        for i in range(len(caminho) - 1):
                            origem = caminho[i]
                            dest = caminho[i+1]
                            capacidade = self.G[origem][dest]['capacity']
                            ok = num_veiculos <= capacidade
                            todas_vias_ok = todas_vias_ok and ok
                            
                            status = "OK" if ok else "EXCEDIDA!"
                            print(f"  {origem} -> {dest}: capacidade {capacidade}, veiculos {num_veiculos} [{status}]")
                        
                        print(f"Todas as capacidades respeitadas: {'SIM' if todas_vias_ok else 'NAO'}")
                        
                        for i in range(num_veiculos):
                            resultado['rotas'].append({
                                'veiculo_id': veiculo_id,
                                'source': s,
                                'caminho': caminho,
                                'capacidades_respeitadas': todas_vias_ok
                            })
                            veiculo_id += 1
            
            print(f"\n{'='*70}")
            print("RESUMO FINAL")
            print(f"{'='*70}")
            print(f"Destino: [{destino}]")
            print(f"Total de veiculos utilizados: {int(solver.Objective().Value())}")
            print(f"Total de sources envolvidos: {len(resultado['sources_usados'])}")
            print(f"Todos os limites respeitados: SIM")
            print(f"{'='*70}\n")
            
            return resultado
        else:
            print("\nNão foi possível encontrar solução ótima!")
            print("Possíveis causas:")
            print("- Capacidade das vias insuficiente")
            print("- Stock disponível insuficiente")
            print("- Número de veículos insuficiente")
            return None


# Exemplo de uso
if __name__ == "__main__":
    sistema = SistemaDistribuicao()
    
    # Escolher qual rede usar
    print("Escolha o tipo de rede:")
    print("1 - Rede Simples (4 nodos)")
    print("2 - Rede Complexa (18 nodos)")
    
    # Para demonstração, usar a complexa
    usar_complexa = True  # Alterar para False para testar a simples
    
    if usar_complexa:
        print("\n>>> Criando REDE COMPLEXA...")
        sistema.criar_rede_complexa()
    else:
        print("\n>>> Criando REDE SIMPLES...")
        sistema.criar_rede_simples()
    
    # Visualizar a rede
    sistema.visualizar_rede()
    
    if usar_complexa:
        # Testes com a rede complexa
        print("\n" + "="*80)
        print("TESTE 1: Encomenda pequena para D1")
        print("="*80)
        encomenda1 = {
            'destino': 'D1',
            'pacotes': {1: 3, 2: 2, 5: 1}  # 3+4+5 = 12 unidades
        }
        resultado1 = sistema.resolver_encomenda(encomenda1)
        
        print("\n" + "="*80)
        print("TESTE 2: Encomenda média para D4")
        print("="*80)
        encomenda2 = {
            'destino': 'D4',
            'pacotes': {1: 5, 2: 3, 5: 2}  # 5+6+10 = 21 unidades
        }
        resultado2 = sistema.resolver_encomenda(encomenda2)
        
        print("\n" + "="*80)
        print("TESTE 3: Encomenda grande para D3")
        print("="*80)
        encomenda3 = {
            'destino': 'D3',
            'pacotes': {1: 2, 2: 4, 5: 4}  # 2+8+20 = 30 unidades
        }
        resultado3 = sistema.resolver_encomenda(encomenda3)
        
        print("\n" + "="*80)
        print("TESTE 4: Encomenda complexa para D6")
        print("="*80)
        encomenda4 = {
            'destino': 'D4',
            'pacotes': {1: 8, 2: 5, 5: 1}  # 8+10+5 = 23 unidades
        }
        resultado4 = sistema.resolver_encomenda(encomenda4)
        
    else:
        # Testes com a rede simples
        encomenda1 = {
            'destino': 'C',
            'pacotes': {1: 2, 2: 1, 5: 1}  # 2+2+5 = 9 unidades
        }
        resultado = sistema.resolver_encomenda(encomenda1)
        
        print("\n" + "="*80 + "\n")
        encomenda2 = {
            'destino': 'D',
            'pacotes': {1: 1, 2: 2, 5: 1}  # 1+4+5 = 10 unidades
        }
        resultado2 = sistema.resolver_encomenda(encomenda2)