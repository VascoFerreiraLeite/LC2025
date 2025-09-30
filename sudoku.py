from ortools.sat.python import cp_model

class Sudoku3DSolver:
    def __init__(self, n):
        """
        Inicializa o solver para Sudoku 3D de dimensões n² x n² x n²
        """
        self.n = n
        self.size = n * n  # n²
        self.domain_size = n * n * n  # n³
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        
        # Cria as variáveis para cada célula (i, j, k)
        self.cells = {}
        for i in range(1, self.size + 1):
            for j in range(1, self.size + 1):
                for k in range(1, self.size + 1):
                    self.cells[(i, j, k)] = self.model.NewIntVar(
                        1, self.domain_size, f'cell_{i}_{j}_{k}'
                    )
    
    def add_fixed_values(self, fixed_assignments):
        """
        Adiciona valores fixos às células
        
        Args:
            fixed_assignments: dicionário {(i, j, k): valor} onde valor != 0
        """
        for (i, j, k), value in fixed_assignments.items():
            if value != 0:
                self.model.Add(self.cells[(i, j, k)] == value)
    
    def add_cube_box(self, start_i, start_j, start_k):
        """
        Adiciona uma box do tipo cubo com n³ células
        
        Args:
            start_i, start_j, start_k: vértice superior, anterior, esquerdo do cubo
        """
        cells_in_box = []
        for di in range(self.n):
            for dj in range(self.n):
                for dk in range(self.n):
                    i = start_i + di
                    j = start_j + dj  
                    k = start_k + dk
                    if 1 <= i <= self.size and 1 <= j <= self.size and 1 <= k <= self.size:
                        cells_in_box.append(self.cells[(i, j, k)])
        
        # Adiciona restrição all-different para o cubo
        self.model.AddAllDifferent(cells_in_box)
        
        return cells_in_box
    
    def add_path_box(self, start_vertex, end_vertex, order_constraints=None):
        """
        Adiciona uma box do tipo path
        
        Args:
            start_vertex: (i, j, k) do vértice inicial
            end_vertex: (i, j, k) do vértice final  
            order_constraints: lista de tuplas indicando ordem entre vértices
        """
        # Para um path simples entre start e end, vamos considerar todos os vértices
        # no caminho reto (esta é uma simplificação - pode ser expandida)
        path_cells = []
        
        i1, j1, k1 = start_vertex
        i2, j2, k2 = end_vertex
        
        # Gera todos os pontos no caminho reto entre start e end
        for t in range(max(abs(i2-i1), abs(j2-j1), abs(k2-k1)) + 1):
            if abs(i2-i1) > 0:
                i = i1 + t * (1 if i2 > i1 else -1)
            else:
                i = i1
                
            if abs(j2-j1) > 0:
                j = j1 + t * (1 if j2 > j1 else -1)
            else:
                j = j1
                
            if abs(k2-k1) > 0:
                k = k1 + t * (1 if k2 > k1 else -1)
            else:
                k = k1
                
            if 1 <= i <= self.size and 1 <= j <= self.size and 1 <= k <= self.size:
                path_cells.append(self.cells[(i, j, k)])
        
        # Adiciona restrição all-different para o path
        self.model.AddAllDifferent(path_cells)
        
        # Aplica constraints de ordem se fornecidas
        if order_constraints:
            for (v1, v2) in order_constraints:
                self.model.Add(self.cells[v1] < self.cells[v2])
        
        return path_cells
    
    def add_generic_box(self, box_dict):
        """
        Adiciona uma box genérica definida por um dicionário
        
        Args:
            box_dict: dicionário {(i, j, k): valor} representando a box
        """
        cells_in_box = []
        for (i, j, k), value in box_dict.items():
            if value == 0:  # Célula livre
                cells_in_box.append(self.cells[(i, j, k)])
            else:  # Célula com valor fixo
                self.model.Add(self.cells[(i, j, k)] == value)
                cells_in_box.append(self.cells[(i, j, k)])
        
        # Adiciona restrição all-different para células não fixas
        free_cells = [self.cells[(i, j, k)] for (i, j, k), value in box_dict.items() if value == 0]
        if len(free_cells) > 1:
            self.model.AddAllDifferent(free_cells)
        
        return cells_in_box
    
    def add_basic_constraints(self):
        """
        Adiciona constraints básicas do Sudoku 3D
        """
        # Restrições para linhas (i, j fixos, k varia)
        for i in range(1, self.size + 1):
            for j in range(1, self.size + 1):
                row_cells = [self.cells[(i, j, k)] for k in range(1, self.size + 1)]
                self.model.AddAllDifferent(row_cells)
        
        # Restrições para colunas (i, k fixos, j varia)
        for i in range(1, self.size + 1):
            for k in range(1, self.size + 1):
                col_cells = [self.cells[(i, j, k)] for j in range(1, self.size + 1)]
                self.model.AddAllDifferent(col_cells)
        
        # Restrições para pilhas (j, k fixos, i varia)
        for j in range(1, self.size + 1):
            for k in range(1, self.size + 1):
                stack_cells = [self.cells[(i, j, k)] for i in range(1, self.size + 1)]
                self.model.AddAllDifferent(stack_cells)
    
    def solve(self, time_limit=30000):
        """
        Resolve o problema
        
        Args:
            time_limit: tempo limite em segundos
            
        Returns:
            solution: dicionário com a solução ou None se não encontrar
        """
        self.solver.parameters.max_time_in_seconds = time_limit
        
        status = self.solver.Solve(self.model)
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            solution = {}
            for (i, j, k), var in self.cells.items():
                solution[(i, j, k)] = self.solver.Value(var)
            return solution
        else:
            print(f"Solução não encontrada. Status: {status}")
            return None
    
    def print_solution(self, solution, layer_by='k'):
        """
        Imprime a solução organizada por camadas
        
        Args:
            solution: dicionário com a solução
            layer_by: 'i', 'j', ou 'k' para organizar as camadas
        """
        if not solution:
            print("Nenhuma solução para imprimir")
            return
        
        coord_ranges = {
            'i': range(1, self.size + 1),
            'j': range(1, self.size + 1), 
            'k': range(1, self.size + 1)
        }
        
        fixed_coord = layer_by
        moving_coords = [c for c in ['i', 'j', 'k'] if c != fixed_coord]
        
        for fixed_val in coord_ranges[fixed_coord]:
            print(f"\n--- Camada {fixed_coord} = {fixed_val} ---")
            
            # Cria matriz 2D para esta camada
            layer_matrix = []
            for mv1 in coord_ranges[moving_coords[0]]:
                row = []
                for mv2 in coord_ranges[moving_coords[1]]:
                    coords = {fixed_coord: fixed_val, moving_coords[0]: mv1, moving_coords[1]: mv2}
                    value = solution[(coords['i'], coords['j'], coords['k'])]
                    row.append(value)
                layer_matrix.append(row)
            
            # Imprime a matriz
            for row in layer_matrix:
                print(' '.join(f'{val:3d}' for val in row))


# Exemplo de uso
def example_usage():
    # Cria solver para n=2 (dimensões 4x4x4, valores 1-8)
    solver = Sudoku3DSolver(n=7)
    
    # Adiciona constraints básicas
    solver.add_basic_constraints()
    
    # Adiciona alguns cubos
    solver.add_cube_box(1, 1, 1)  # Cubo começando em (1,1,1)
    solver.add_cube_box(1, 3, 1)  # Cubo começando em (1,3,1)
    
    # Adiciona um path
    solver.add_path_box((1, 1, 1), (4, 4, 4))
    
    # Adiciona alguns valores fixos
    fixed_values = {
        (1, 1, 1): 1,
        (4, 4, 4): 8,
        (2, 2, 2): 4
    }
    solver.add_fixed_values(fixed_values)
    
    # Adiciona uma box genérica
    generic_box = {
        (1, 2, 1): 0,  # Livre
        (1, 2, 2): 3,  # Fixo
        (2, 2, 1): 0,  # Livre  
        (2, 2, 2): 0   # Livre
    }
    solver.add_generic_box(generic_box)
    
    # Resolve
    solution = solver.solve()
    
    if solution:
        print("Solução encontrada!")
        solver.print_solution(solution, layer_by='k')
    else:
        print("Não foi possível encontrar solução")

if __name__ == "__main__":
    example_usage()