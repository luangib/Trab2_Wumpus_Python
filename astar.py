import heapq
from TreeNode import TreeNode

# ---------------------------------------------------------------------------
# Heurística: distância de Manhattan
# ---------------------------------------------------------------------------
def heuristic(a, b):
    """Distância de Manhattan entre dois pontos (x1,y1) e (x2,y2)."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# ---------------------------------------------------------------------------
# Vizinhos válidos (4-direções, dentro do grid, sem tiles bloqueados)
# ---------------------------------------------------------------------------
def get_neighbors(pos, grid_w, grid_h, blocked):
    """
    Retorna as coordenadas adjacentes (N/S/L/O) que estão dentro do mapa
    e não pertencem ao conjunto de tiles bloqueados.

    Parâmetros
    ----------
    pos      : (x, y)  — posição atual (1-indexed, igual ao Prolog)
    grid_w   : int     — largura do mapa  (normalmente 12)
    grid_h   : int     — altura do mapa   (normalmente 12)
    blocked  : set     — conjunto de (x, y) considerados intransitáveis
    """
    x, y = pos
    candidates = [
        (x,     y + 1),   # norte
        (x,     y - 1),   # sul
        (x + 1, y    ),   # leste
        (x - 1, y    ),   # oeste
    ]
    return [
        (nx, ny)
        for nx, ny in candidates
        if 1 <= nx <= grid_w
        and 1 <= ny <= grid_h
        and (nx, ny) not in blocked
    ]


# ---------------------------------------------------------------------------
# Algoritmo A*
# ---------------------------------------------------------------------------
def astar(start, goal, grid_w, grid_h, blocked):
    """
    Encontra o caminho de menor custo entre *start* e *goal* usando A*.

    Parâmetros
    ----------
    start    : (x, y)  — posição inicial (1-indexed)
    goal     : (x, y)  — posição destino (1-indexed)
    grid_w   : int     — largura do mapa
    grid_h   : int     — altura do mapa
    blocked  : set     — conjunto de (x, y) intransitáveis

    Retorna
    -------
    list[(x, y)] com o caminho do start ao goal (excluindo o start),
    ou lista vazia se não houver caminho.
    """
    if start == goal:
        return []

    # Fila de prioridade: (f, nó)
    open_heap = []
    g_start = 0
    h_start = heuristic(start, goal)
    start_node = TreeNode(coord=start, fx=g_start + h_start, gx=g_start)
    heapq.heappush(open_heap, start_node)

    # Mapas auxiliares
    came_from  = {}          # coord → coord pai
    g_score    = {start: 0}  # melhor custo conhecido até cada coord
    open_set   = {start}     # coords na fila (lookup rápido)
    closed_set = set()       # coords já expandidos

    while open_heap:
        current_node = heapq.heappop(open_heap)
        current = current_node.get_coord()

        if current in closed_set:
            continue
        closed_set.add(current)
        open_set.discard(current)

        # Chegou ao destino → reconstrói caminho
        if current == goal:
            return _reconstruct_path(came_from, start, goal)

        for neighbor in get_neighbors(current, grid_w, grid_h, blocked):
            if neighbor in closed_set:
                continue

            tentative_g = g_score[current] + 1  # custo uniforme (cada passo = 1)

            if tentative_g < g_score.get(neighbor, float('inf')):
                came_from[neighbor] = current
                g_score[neighbor]   = tentative_g
                f = tentative_g + heuristic(neighbor, goal)
                neighbor_node = TreeNode(coord=neighbor, fx=f, gx=tentative_g)
                heapq.heappush(open_heap, neighbor_node)
                open_set.add(neighbor)

    return []  # sem caminho


def _reconstruct_path(came_from, start, goal):
    """Reconstrói a lista de coordenadas do start ao goal."""
    path = []
    current = goal
    while current != start:
        path.append(current)
        current = came_from[current]
    path.reverse()
    return path


# ---------------------------------------------------------------------------
# Helpers de navegação — convertem caminho em ações do agente
# ---------------------------------------------------------------------------

# Mapeamento de (dx, dy) → direção cardinal
_DELTA_TO_DIR = {
    ( 0,  1): 'norte',
    ( 0, -1): 'sul',
    ( 1,  0): 'leste',
    (-1,  0): 'oeste',
}

# Ordem horária das direções (para calcular viradas)
_CLOCKWISE = ['norte', 'leste', 'sul', 'oeste']


def direction_to(current_pos, next_pos):
    """Retorna a direção cardinal necessária para ir de current_pos a next_pos."""
    dx = next_pos[0] - current_pos[0]
    dy = next_pos[1] - current_pos[1]
    return _DELTA_TO_DIR.get((dx, dy))


def turns_needed(facing, target_dir):
    """
    Retorna a lista de ações de virada ('virar_direita' / 'virar_esquerda')
    necessárias para alinhar *facing* com *target_dir*.

    Escolhe sempre o caminho mais curto (≤ 2 viradas).
    """
    if facing == target_dir:
        return []

    ci = _CLOCKWISE.index(facing)
    ti = _CLOCKWISE.index(target_dir)

    right_steps = (ti - ci) % 4   # quantas viradas à direita
    left_steps  = (ci - ti) % 4   # quantas viradas à esquerda

    if right_steps <= left_steps:
        return ['virar_direita'] * right_steps
    else:
        return ['virar_esquerda'] * left_steps


def next_action_towards(current_pos, facing, next_pos):
    """
    Dado que o agente está em *current_pos* olhando para *facing*,
    retorna a **próxima ação atômica** para avançar em direção a *next_pos*:
      - 'virar_direita'  se precisar virar à direita primeiro
      - 'virar_esquerda' se precisar virar à esquerda primeiro
      - 'andar'          se já estiver alinhado
    """
    needed_dir = direction_to(current_pos, next_pos)
    if needed_dir is None:
        return None  # next_pos não é adjacente (não deveria acontecer)

    actions = turns_needed(facing, needed_dir)
    if actions:
        return actions[0]
    return 'andar'


# ---------------------------------------------------------------------------
# Função principal de interface com o gmap.py
# ---------------------------------------------------------------------------

def get_next_action(current_pos, facing, goal, grid_w, grid_h, blocked):
    """
    Calcula a próxima ação atômica para o agente ir de *current_pos* até *goal*
    desviando dos tiles em *blocked*.

    Parâmetros
    ----------
    current_pos : (x, y)   — posição atual do agente (1-indexed)
    facing      : str      — direção atual ('norte','sul','leste','oeste')
    goal        : (x, y)   — destino desejado
    grid_w      : int      — largura do mapa (12)
    grid_h      : int      — altura do mapa  (12)
    blocked     : set      — tiles intransitáveis, ex: {(3,5), (4,2)}

    Retorna
    -------
    str  — uma das ações: 'andar', 'virar_direita', 'virar_esquerda'
    None — se não há caminho disponível
    """
    path = astar(current_pos, goal, grid_w, grid_h, blocked)
    if not path:
        return None  # sem caminho

    next_pos = path[0]
    return next_action_towards(current_pos, facing, next_pos)


def get_full_path(current_pos, goal, grid_w, grid_h, blocked):
    """
    Retorna o caminho completo (lista de coordenadas) de *current_pos* a *goal*.
    Útil para visualização ou planejamento antecipado.
    """
    return astar(current_pos, goal, grid_w, grid_h, blocked)


# ---------------------------------------------------------------------------
# Exemplo de uso / teste rápido
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    # Mapa 12x12, agente em (1,1) olhando para norte, destino (8,6)
    # Bloqueados: poços e inimigos conhecidos
    BLOCKED = {(1,3), (4,2), (6,6), (8,5), (9,3), (10,11), (11,8), (2,11)}

    start   = (1, 1)
    goal    = (8, 6)
    facing  = 'norte'

    path = get_full_path(start, goal, 12, 12, BLOCKED)
    print("Caminho encontrado:", path)
    print("Tamanho:", len(path), "passos")

    # Simula execução passo a passo (cada step pode exigir várias viradas antes de andar)
    pos = start
    dir_ = facing
    print("\nSequência de ações:")
    for step in path:
        # Primeiro resolve todas as viradas necessárias, depois anda
        needed_dir = direction_to(pos, step)
        for turn in turns_needed(dir_, needed_dir):
            print(f"  {pos} olhando {dir_:6s} → ação: {turn}")
            idx = _CLOCKWISE.index(dir_)
            if turn == 'virar_direita':
                dir_ = _CLOCKWISE[(idx + 1) % 4]
            else:
                dir_ = _CLOCKWISE[(idx - 1) % 4]
        print(f"  {pos} olhando {dir_:6s} → ação: andar  → chega em {step}")
        pos = step