from ortools.sat.python import cp_model

def solve_sudoku_3d(n, fixed_assignments=None, cube_boxes=None, path_boxes=None, generic_boxes=None, time_limit=300):
    """
    Resolve o problema de Sudoku 3D generalizado
    
    Args:
        n: parâmetro fundamental (dimensões n² x n² x n²)
        fixed_assignments: dicionário {(i,j,k): valor} com valores fixos
        cube_boxes: lista de [(start_i, start_j, start_k)] para cubos
        path_boxes: lista de [(start, end, order_constraints)] para paths
        generic_boxes: lista de [box_dict] para boxes genéricas
        time_limit: tempo limite em segundos
    """
    
    # Inicialização de parâmetros
    size = n * n  # n²
    domain_size = n * n * n  # n³
    
    # Criar modelo e solver
    model = cp_model.CpModel()
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    
    # Criar variáveis para todas as células
    cells = {}
    for i in range(1, size + 1):
        for j in range(1, size + 1):
            for k in range(1, size + 1):
                cells[(i, j, k)] = model.NewIntVar(1, domain_size, f'cell_{i}_{j}_{k}')
    
    # Adicionar valores fixos
    if fixed_assignments:
        for (i, j, k), value in fixed_assignments.items():
            if value != 0:
                model.Add(cells[(i, j, k)] == value)
    
    # Adicionar constraints básicas
    _add_basic_constraints(model, cells, size)
    
    # Adicionar boxes cúbicas
    if cube_boxes:
        for start_i, start_j, start_k in cube_boxes:
            _add_cube_box(model, cells, n, size, start_i, start_j, start_k)
    
    # Adicionar boxes de path
    if path_boxes:
        for path_info in path_boxes:
            if len(path_info) == 2:
                start, end = path_info
                order_constraints = None
            else:
                start, end, order_constraints = path_info
            _add_path_box(model, cells, size, start, end, order_constraints)
    
    # Adicionar boxes genéricas
    if generic_boxes:
        for box_dict in generic_boxes:
            _add_generic_box(model, cells, box_dict)
    
    # Resolver o problema
    status = solver.Solve(model)
    
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        solution = {}
        for (i, j, k), var in cells.items():
            solution[(i, j, k)] = solver.Value(var)
        return solution
    else:
        print(f"Solução não encontrada. Status: {status}")
        return None

def _add_basic_constraints(model, cells, size):
    """Adiciona constraints básicas de linhas, colunas e pilhas"""
    # Restrições para linhas (i, j fixos, k varia)
    for i in range(1, size + 1):
        for j in range(1, size + 1):
            row_cells = [cells[(i, j, k)] for k in range(1, size + 1)]
            model.AddAllDifferent(row_cells)
    
    # Restrições para colunas (i, k fixos, j varia)
    for i in range(1, size + 1):
        for k in range(1, size + 1):
            col_cells = [cells[(i, j, k)] for j in range(1, size + 1)]
            model.AddAllDifferent(col_cells)
    
    # Restrições para pilhas (j, k fixos, i varia)
    for j in range(1, size + 1):
        for k in range(1, size + 1):
            stack_cells = [cells[(i, j, k)] for i in range(1, size + 1)]
            model.AddAllDifferent(stack_cells)

def _add_cube_box(model, cells, n, size, start_i, start_j, start_k):
    """Adiciona uma box do tipo cubo"""
    cells_in_box = []
    for di in range(n):
        for dj in range(n):
            for dk in range(n):
                i = start_i + di
                j = start_j + dj  
                k = start_k + dk
                if 1 <= i <= size and 1 <= j <= size and 1 <= k <= size:
                    cells_in_box.append(cells[(i, j, k)])
    
    if len(cells_in_box) > 1:
        model.AddAllDifferent(cells_in_box)
    
    return cells_in_box

def _add_path_box(model, cells, size, start_vertex, end_vertex, order_constraints=None):
    """Adiciona uma box do tipo path"""
    i1, j1, k1 = start_vertex
    i2, j2, k2 = end_vertex
    
    path_cells = []
    steps = max(abs(i2 - i1), abs(j2 - j1), abs(k2 - k1))
    
    for t in range(steps + 1):
        if steps > 0:
            ratio = t / steps
            i = int(i1 + (i2 - i1) * ratio)
            j = int(j1 + (j2 - j1) * ratio)
            k = int(k1 + (k2 - k1) * ratio)
        else:
            i, j, k = i1, j1, k1
            
        if 1 <= i <= size and 1 <= j <= size and 1 <= k <= size:
            path_cells.append(cells[(i, j, k)])
    
    # Remove duplicatas mantendo a ordem
    unique_cells = []
    seen = set()
    for cell in path_cells:
        if cell not in seen:
            unique_cells.append(cell)
            seen.add(cell)
    
    if len(unique_cells) > 1:
        model.AddAllDifferent(unique_cells)
    
    # Aplica constraints de ordem se fornecidas
    if order_constraints:
        for (v1, v2) in order_constraints:
            model.Add(cells[v1] < cells[v2])
    
    return unique_cells

def _add_generic_box(model, cells, box_dict):
    """Adiciona uma box genérica definida por dicionário"""
    free_cells = []
    
    for (i, j, k), value in box_dict.items():
        if value == 0:  # Célula livre
            free_cells.append(cells[(i, j, k)])
        else:  # Célula com valor fixo
            model.Add(cells[(i, j, k)] == value)
    
    if len(free_cells) > 1:
        model.AddAllDifferent(free_cells)
    
    return free_cells

def print_solution_3d(solution, n, layer_by='k'):
    """
    Imprime a solução organizada por camadas
    
    Args:
        solution: dicionário com a solução
        n: parâmetro do problema
        layer_by: 'i', 'j', ou 'k' para organizar as camadas
    """
    if not solution:
        print("Nenhuma solução para imprimir")
        return
    
    size = n * n
    
    coord_ranges = {
        'i': range(1, size + 1),
        'j': range(1, size + 1), 
        'k': range(1, size + 1)
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
def main():
    # Configuração do problema para n=2
    n = 2
    
    # Valores fixos
    fixed_assignments = {
        (1, 1, 1): 1,
        (4, 4, 4): 8,
        (2, 2, 2): 4
    }
    
    # Boxes cúbicas
    cube_boxes = [
        (1, 1, 1),  # Cubo começando em (1,1,1)
        (1, 3, 1),  # Cubo começando em (1,3,1)
    ]
    
    # Boxes de path
    path_boxes = [
        ((1, 1, 1), (4, 4, 4), None)  # Path sem constraints de ordem
    ]
    
    # Boxes genéricas
    generic_boxes = [
        {
            (1, 2, 1): 0,  # Livre
            (1, 2, 2): 3,  # Fixo
            (2, 2, 1): 0,  # Livre  
            (2, 2, 2): 0   # Livre
        }
    ]
    
    # Resolver
    solution = solve_sudoku_3d(
        n=n,
        fixed_assignments=fixed_assignments,
        cube_boxes=cube_boxes,
        path_boxes=path_boxes,
        generic_boxes=generic_boxes,
        time_limit=300
    )
    
    if solution:
        print("Solução encontrada!")
        print_solution_3d(solution, n, layer_by='k')
        
        # Mostrar alguns valores específicos
        print("\n--- Alguns valores da solução ---")
        for coords in [(1,1,1), (2,2,2), (4,4,4)]:
            print(f"Célula {coords}: {solution[coords]}")
    else:
        print("Não foi possível encontrar solução")

if __name__ == "__main__":
    main()