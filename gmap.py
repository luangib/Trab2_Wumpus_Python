################################################
import pygame
import sys, time, random, os, tkinter
from tkinter import filedialog
from pyswip import Prolog, Functor, Variable, Query

import pathlib
current_path = pathlib.Path().resolve()
mapa_atual = None   # guarda o caminho do último .pl carregado (None = aleatório)

elapsed_time = 0
auto_play_tempo = 0.5
auto_play = True   # True = agente roda sozinho | tecla A alterna
show_map = False

# Estado de fim de jogo
game_over       = False   # True quando o jogo encerrou
game_over_motivo = ''     # 'vitoria', 'morte', 'poco'
game_over_pontos = 0      # pontuação capturada no momento do encerramento

# Sensor de grito (inimigo morto) — exibido por N ciclos
grito_ciclos    = 0       # quantos ciclos ainda exibir o grito
GRITO_DURACAO   = 4       # ciclos que o grito fica visível no painel

# Sensor de impacto na parede — exibido por N ciclos
impacto_ciclos  = 0
IMPACTO_DURACAO = 3

# Painel lateral de KB / Plano
PANEL_W  = 280          # largura do painel em pixels
plano_atual   = []      # lista de ações pendentes lida do Prolog
objetivo_atual = None   # (x, y) destino atual
sensores_atuais = []    # observações da posição atual

scale = 60
size_x = 12
size_y = 12
width = size_x * scale  #Largura Janela (só o mapa)
height = size_y * scale #Altura Janela

player_pos = (1,1,'norte')
energia = 0
pontuacao = 0


mapa=[['','','','','','','','','','','',''],
      ['','','','','','','','','','','',''],
      ['','','','','','','','','','','',''],
      ['','','','','','','','','','','',''],
      ['','','','','','','','','','','',''],
      ['','','','','','','','','','','',''],
      ['','','','','','','','','','','',''],
      ['','','','','','','','','','','',''],
      ['','','','','','','','','','','',''],
      ['','','','','','','','','','','',''],
      ['','','','','','','','','','','',''],
      ['','','','','','','','','','','','']]

visitados = []
certezas = []

# ── Carrega mapa: argumento de linha de comando ou gera aleatório ──────────
def gerar_mapa_aleatorio(caminho_saida):
    """
    Gera mapa 12x12 com quantidades definidas pelo enunciado e salva como .pl.
    Elementos:
      P  = poço           (8)
      D  = inimigo dano 20 (2, maiúsculo = D)  [verifica_player usa 'D']
      d  = inimigo dano 50 (2, minúsculo = d)  [verifica_player usa 'd']
      T  = teletransportador (4)
      O  = ouro           (3)
      U  = powerup        (3)
    A posição (1,1) fica sempre vazia (saída do agente).
    """
    import random as _rnd

    SIZE = 12
    todas = [(x, y) for x in range(1, SIZE+1) for y in range(1, SIZE+1)
             if (x, y) != (1, 1)]

    elementos = (
        ['P'] * 8 +
        ['D'] * 2 +
        ['d'] * 2 +
        ['T'] * 4 +
        ['O'] * 3 +
        ['U'] * 3
    )

    posicoes = _rnd.sample(todas, len(elementos))
    _rnd.shuffle(elementos)

    grade = {(x, y): '' for x in range(1, SIZE+1) for y in range(1, SIZE+1)}
    for pos, elem in zip(posicoes, elementos):
        grade[pos] = elem

    linhas = [":-dynamic tile/3.", ""]
    linhas += ["%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%",
               "%% Definição do mapa (gerado aleatoriamente)",
               "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%", ""]
    linhas.append(f"map_size({SIZE},{SIZE}).")
    linhas.append("")
    for y in range(SIZE, 0, -1):
        for x in range(1, SIZE+1):
            v = grade[(x, y)]
            linhas.append(f"tile({x},{y},'{v}').")
        linhas.append("")

    with open(caminho_saida, 'w', encoding='utf-8') as f:
        f.write("\n".join(linhas))

    print(f"[mapa] Mapa aleatório gerado em: {caminho_saida}")


def carregar_mapa_pl(caminho_pl):
    """Reescreve mapa.pl com o conteúdo do arquivo escolhido e recarrega Prolog."""
    destino = current_path / 'mapa.pl'
    with open(caminho_pl, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    with open(destino, 'w', encoding='utf-8') as f:
        f.write(conteudo)
    print(f"[mapa] Carregado: {caminho_pl}")


# Decide qual mapa usar
if len(sys.argv) > 1:
    mapa_arg = pathlib.Path(sys.argv[1])
    if mapa_arg.exists():
        carregar_mapa_pl(mapa_arg)
        mapa_atual = mapa_arg
    else:
        print(f"[aviso] Arquivo '{mapa_arg}' não encontrado. Gerando mapa aleatório.")
        gerar_mapa_aleatorio(current_path / 'mapa.pl')
        mapa_atual = None
else:
    # Sem argumento → gera aleatório
    gerar_mapa_aleatorio(current_path / 'mapa.pl')
    mapa_atual = None

pl_file = str(current_path / 'main.pl').replace('\\', '/')
prolog = Prolog()
prolog.consult(pl_file)

last_action = ""

def reiniciar_jogo():
    """
    R — Reinicia o jogo mantendo o mapa atual.
    Se o mapa veio de um arquivo, recarrega o mesmo arquivo.
    Se foi gerado aleatoriamente, gera um novo mapa aleatório.
    """
    global mapa_atual
    if mapa_atual is not None:
        # Recarrega o mesmo arquivo fixo
        carregar_mapa_pl(mapa_atual)
        print(f"[reiniciar] Mesmo mapa: {mapa_atual}")
    else:
        # Gera novo mapa aleatório
        gerar_mapa_aleatorio(current_path / 'mapa.pl')
        print("[reiniciar] Novo mapa aleatório gerado")

    mapa_pl_path = str(current_path / 'mapa.pl').replace('\\', '/')
    list(prolog.query(f"recarrega_mapa('{mapa_pl_path}')"))
    update_prolog()


def abrir_dialogo_mapa():
    """Abre seletor de arquivo .pl e recarrega o jogo com o mapa escolhido."""
    # tkinter precisa de janela raiz oculta para o filedialog
    root = tkinter.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    caminho = filedialog.askopenfilename(
        title="Selecionar mapa (.pl)",
        filetypes=[("Prolog files", "*.pl"), ("All files", "*.*")],
        initialdir=str(current_path)
    )
    root.destroy()
    if caminho:
        global mapa_atual
        mapa_atual = pathlib.Path(caminho)
        carregar_mapa_pl(caminho)
        # Usa recarrega_mapa/1 que limpa tiles antigos antes de recarregar
        mapa_pl_path = str(current_path / 'mapa.pl').replace('\\', '/')
        list(prolog.query(f"recarrega_mapa('{mapa_pl_path}')"))
        update_prolog()
        print(f"[mapa] Jogo reiniciado com: {caminho}")


def decisao():

    acao = ""    
    
    acoes = list(prolog.query("executa_acao(X)"))
    if len(acoes) > 0:
        acao = acoes[0]['X']

    return acao


def exec_prolog(a):
    global last_action
    if a != "":
        list(prolog.query(a))
    last_action = a

def _checar_fim_de_jogo():
    """
    Consulta o Prolog e decide se o jogo encerrou.
    Retorna (encerrou: bool, motivo: str).
    Motivos possíveis: 'morte', 'poco', 'vitoria'
    """
    # Morreu por dano ou caiu em poço → posicao(_,_,morto)
    if player_pos[2] == 'morto':
        # Distingue morte por poço (energia foi a -1000 de uma vez)
        # vs morte por inimigo; para o painel basta saber "morto"
        motivo = 'poco' if list(prolog.query("posicao(X,Y,morto), tile(X,Y,'P')")) else 'morte'
        return True, motivo

    # Saiu do labirinto: voltou para (1,1) depois de já ter visitado outras casas
    if player_pos[0] == 1 and player_pos[1] == 1 and len(visitados) > 1:
        # Checa se o Prolog considera o jogo encerrado
        if list(prolog.query("jogo_encerrado")):
            return True, 'vitoria'

    return False, ''


def _checar_grito():
    """Retorna True se o Prolog tem o fato grito/0 pendente e o retracta."""
    if list(prolog.query("grito")):
        list(prolog.query("retract(grito)"))
        return True
    return False


def update_prolog():
    global player_pos, mapa, energia, pontuacao, visitados, show_map
    global game_over, game_over_motivo, game_over_pontos, auto_play
    global grito_ciclos, impacto_ciclos

    pos_antes = player_pos  # guarda posição antes de executar para detectar impacto

    list(prolog.query("atualiza_obs, verifica_player"))

    x = Variable()
    y = Variable()
    visitado = Functor("visitado", 2)
    visitado_query = Query(visitado(x,y))
    visitados.clear()
    while visitado_query.nextSolution():
        visitados.append((x.value,y.value))
    visitado_query.closeQuery()

    x = Variable()
    y = Variable()
    certeza = Functor("certeza", 2)
    certeza_query = Query(certeza(x,y))
    certezas.clear()
    while certeza_query.nextSolution():
        certezas.append((x.value,y.value))
    certeza_query.closeQuery()
        
    if show_map:    
        x = Variable()
        y = Variable()
        z = Variable()    
        tile = Functor("tile", 3)
        tile_query = Query(tile(x,y,z))
        while tile_query.nextSolution():
            mapa[y.get_value()-1][x.get_value()-1] = str(z.value)
        tile_query.closeQuery()

    else:

        y = 0
        for j in mapa:
            x = 0
            for i in j:
                mapa[y][x] = ''
                x  += 1
            y +=  1

        x = Variable()
        y = Variable()
        z = Variable()    
        memory = Functor("memory", 3)
        memory_query = Query(memory(x,y,z))
        while memory_query.nextSolution():
            for s in z.value:
                
                if str(s) == 'brisa':
                    mapa[y.get_value()-1][x.get_value()-1] += 'P'
                elif str(s) == 'palmas':
                    mapa[y.get_value()-1][x.get_value()-1] += 'T'
                elif str(s) == 'passos':
                    mapa[y.get_value()-1][x.get_value()-1] += 'D'
                elif str(s) == 'reflexo':
                    mapa[y.get_value()-1][x.get_value()-1] += 'U'
                elif str(s) == 'brilho':
                    mapa[y.get_value()-1][x.get_value()-1] += 'O'
            
        memory_query.closeQuery()

    x = Variable()
    y = Variable()
    z = Variable()

    posicao = Functor("posicao", 3)
    position_query = Query(posicao(x,y,z))
    position_query.nextSolution()
    player_pos = (x.value,y.value,str(z.value))
    position_query.closeQuery()

    x = Variable()
    energia = Functor("energia", 1)
    energia_query = Query(energia(x))
    energia_query.nextSolution()
    energia = x.value
    energia_query.closeQuery()

    x = Variable()
    pontuacao = Functor("pontuacao", 1)
    pontuacao_query = Query(pontuacao(x))
    pontuacao_query.nextSolution()
    pontuacao = x.value
    pontuacao_query.closeQuery()

    #print(mapa)
    #print(player_pos)

    # Lê plano pendente do Prolog
    global plano_atual, objetivo_atual, sensores_atuais
    plano_atual = []
    try:
        res = list(prolog.query("plano(L)"))
        if res:
            plano_atual = [str(a) for a in res[0]['L']]
    except Exception:
        pass

    # Lê objetivo atual
    objetivo_atual = None
    try:
        res = list(prolog.query("objetivo(OX, OY)"))
        if res:
            objetivo_atual = (res[0]['OX'], res[0]['OY'])
    except Exception:
        pass

    # Lê sensores da posição atual (memory da posição do agente)
    sensores_atuais = []
    try:
        px, py = player_pos[0], player_pos[1]
        res = list(prolog.query(f"memory({px},{py},L)"))
        if res:
            sensores_atuais = [str(s) for s in res[0]['L']]
    except Exception:
        pass

    # ── Sensor de grito: inimigo morreu no Prolog ───────────────────────
    if _checar_grito():
        grito_ciclos = GRITO_DURACAO

    if grito_ciclos > 0:
        if 'grito' not in sensores_atuais:
            sensores_atuais.append('grito')
        grito_ciclos -= 1

    # ── Sensor de impacto: posição não mudou após última ação "andar" ───
    if last_action == 'andar' and player_pos[:2] == pos_antes[:2]:
        impacto_ciclos = IMPACTO_DURACAO

    if impacto_ciclos > 0:
        if 'impacto' not in sensores_atuais:
            sensores_atuais.append('impacto')
        impacto_ciclos -= 1

    # ── Verificação de fim de jogo ───────────────────────────────────────
    if not game_over:
        encerrou, motivo = _checar_fim_de_jogo()
        if encerrou:
            game_over         = True
            game_over_motivo  = motivo
            game_over_pontos  = pontuacao
            auto_play         = False
            pygame.display.set_caption('INF1771 Trabalho 2 - Agente Lógico [FIM]')


def load():
    global sys_font, clock, img_wall, img_grass, img_start, img_finish, img_path
    global img_gold,img_health, img_pit, img_bat, img_enemy1, img_enemy2,img_floor
    global bw_img_gold,bw_img_health, bw_img_pit, bw_img_bat, bw_img_enemy1, bw_img_enemy2,bw_img_floor
    global img_player_up, img_player_down, img_player_left, img_player_right, img_tomb

    sys_font       = pygame.font.Font(pygame.font.get_default_font(), 20)
    global small_font, panel_font
    small_font  = pygame.font.Font(pygame.font.get_default_font(), 13)
    panel_font  = pygame.font.Font(pygame.font.get_default_font(), 14)
    clock = pygame.time.Clock() 

    img_wall = pygame.image.load('wall.jpg')
    #img_wall2_size = (img_wall.get_width()/map_width, img_wall.get_height()/map_height)
    img_wall_size = (width/size_x, height/size_y)
    
    img_wall = pygame.transform.scale(img_wall, img_wall_size)

    
    img_player_up = pygame.image.load('player_up.png')
    img_player_up_size = (width/size_x, height/size_y)
    img_player_up = pygame.transform.scale(img_player_up, img_player_up_size)

    img_player_down = pygame.image.load('player_down.png')
    img_player_down_size = (width/size_x, height/size_y)
    img_player_down = pygame.transform.scale(img_player_down, img_player_down_size)

    img_player_left = pygame.image.load('player_left.png')
    img_player_left_size = (width/size_x, height/size_y)
    img_player_left = pygame.transform.scale(img_player_left, img_player_left_size)

    img_player_right = pygame.image.load('player_right.png')
    img_player_right_size = (width/size_x, height/size_y)
    img_player_right = pygame.transform.scale(img_player_right, img_player_right_size)


    img_tomb = pygame.image.load('tombstone.png')
    img_tomb_size = (width/size_x, height/size_y)
    img_tomb = pygame.transform.scale(img_tomb, img_tomb_size)



    img_grass = pygame.image.load('grass.jpg')
    img_grass_size = (width/size_x, height/size_y)
    img_grass = pygame.transform.scale(img_grass, img_grass_size)

    img_floor = pygame.image.load('floor.png')
    img_floor_size = (width/size_x, height/size_y)
    img_floor = pygame.transform.scale(img_floor, img_floor_size)

    img_gold = pygame.image.load('gold.png')
    img_gold_size = (width/size_x, height/size_y)
    img_gold = pygame.transform.scale(img_gold, img_gold_size)

    img_pit = pygame.image.load('pit.png')
    img_pit_size = (width/size_x, height/size_y)
    img_pit = pygame.transform.scale(img_pit, img_pit_size)

    img_enemy1 = pygame.image.load('enemy1.png')
    img_enemy1_size = (width/size_x, height/size_y)
    img_enemy1 = pygame.transform.scale(img_enemy1, img_enemy1_size)

    img_enemy2 = pygame.image.load('enemy2.png')
    img_enemy2_size = (width/size_x, height/size_y)
    img_enemy2 = pygame.transform.scale(img_enemy2, img_enemy2_size)

    img_bat = pygame.image.load('bat.png')
    img_bat_size = (width/size_x, height/size_y)
    img_bat = pygame.transform.scale(img_bat, img_bat_size)

    img_health = pygame.image.load('health.png')
    img_health_size = (width/size_x, height/size_y)
    img_health = pygame.transform.scale(img_health, img_health_size)    
    
    bw_img_floor = pygame.image.load('bw_floor.png')
    bw_img_floor_size = (width/size_x, height/size_y)
    bw_img_floor = pygame.transform.scale(bw_img_floor, bw_img_floor_size)

    bw_img_gold = pygame.image.load('bw_gold.png')
    bw_img_gold_size = (width/size_x, height/size_y)
    bw_img_gold = pygame.transform.scale(bw_img_gold, bw_img_gold_size)

    bw_img_pit = pygame.image.load('bw_pit.png')
    bw_img_pit_size = (width/size_x, height/size_y)
    bw_img_pit = pygame.transform.scale(bw_img_pit, bw_img_pit_size)

    bw_img_enemy1 = pygame.image.load('bw_enemy1.png')
    bw_img_enemy1_size = (width/size_x, height/size_y)
    bw_img_enemy1 = pygame.transform.scale(bw_img_enemy1, bw_img_enemy1_size)

    bw_img_enemy2 = pygame.image.load('bw_enemy2.png')
    bw_img_enemy2_size = (width/size_x, height/size_y)
    bw_img_enemy2 = pygame.transform.scale(bw_img_enemy2, bw_img_enemy2_size)

    bw_img_bat = pygame.image.load('bw_bat.png')
    bw_img_bat_size = (width/size_x, height/size_y)
    bw_img_bat = pygame.transform.scale(bw_img_bat, bw_img_bat_size)

    bw_img_health = pygame.image.load('bw_health.png')
    bw_img_health_size = (width/size_x, height/size_y)
    bw_img_health = pygame.transform.scale(bw_img_health, bw_img_health_size)  

def update(dt, screen):
    
    global elapsed_time
    
    elapsed_time += dt
    
    if (elapsed_time / 1000) > auto_play_tempo:
        
        if auto_play and player_pos[2] != 'morto' and not game_over:
            exec_prolog(decisao())
            update_prolog()
       
        elapsed_time = 0
        
    

def key_pressed(event):
    
    global show_map, auto_play, game_over, game_over_motivo, game_over_pontos
    global grito_ciclos, impacto_ciclos

    #leitura do teclado
    if event.type == pygame.KEYDOWN:

        # ESC sai do jogo
        if event.key == pygame.K_ESCAPE:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
            return

        # R reinicia — também reseta o estado de game_over
        if event.key == pygame.K_r:
            game_over        = False
            game_over_motivo = ''
            game_over_pontos = 0
            grito_ciclos     = 0
            impacto_ciclos   = 0
            reiniciar_jogo()
            return

        # L carrega mapa — também reseta game_over
        if event.key == pygame.K_l:
            game_over        = False
            game_over_motivo = ''
            game_over_pontos = 0
            grito_ciclos     = 0
            impacto_ciclos   = 0
            abrir_dialogo_mapa()
            return

        if not auto_play and player_pos[2] != 'morto' and not game_over:
            if event.key == pygame.K_LEFT: #tecla esquerda
                exec_prolog("virar_esquerda")
                update_prolog()

            elif event.key == pygame.K_RIGHT: #tecla direita
                exec_prolog("virar_direita")
                update_prolog()

            elif event.key == pygame.K_UP: #tecla  cima
                exec_prolog("andar")
                update_prolog()

            if event.key == pygame.K_SPACE:
                exec_prolog("pegar")
                update_prolog()
    
        if event.key == pygame.K_m:
            show_map = not show_map
            update_prolog()

        # A = alternar auto_play (agente automático) — só faz sentido se não acabou
        if event.key == pygame.K_a and not game_over:
            auto_play = not auto_play
            modo = "AUTO" if auto_play else "MANUAL"
            pygame.display.set_caption(f'INF1771 Trabalho 2 - Agente Lógico [{modo}]')


# Cores do painel
COR_FUNDO_PAINEL = (18, 18, 30)
COR_TITULO       = (100, 180, 255)
COR_TEXTO        = (220, 220, 220)
COR_ACAO_PROX    = (80, 255, 120)
COR_ACAO_REST    = (160, 210, 160)
COR_PERIGO       = (255, 80, 80)
COR_SEGURO       = (80, 220, 80)
COR_NEUTRO       = (180, 180, 180)
COR_SEPARADOR    = (50, 50, 80)
COR_OBJ          = (255, 210, 80)

# Mapeamento de nome de ação → texto legível
ACAO_LABEL = {
    'andar':         '▶ Andar',
    'virar_direita': '↻ Virar direita',
    'virar_esquerda':'↺ Virar esquerda',
    'pegar':         '✦ Pegar item',
}

# Mapeamento sensor → texto + cor
SENSOR_INFO = {
    'brisa':   ('💨 Brisa (poço próximo)',   COR_PERIGO),
    'palmas':  ('🦇 Flash (morcego próx.)',  COR_PERIGO),
    'passos':  ('👣 Passos (inimigo próx.)', COR_PERIGO),
    'brilho':  ('✨ Brilho (ouro aqui!)',    COR_OBJ),
    'reflexo': ('💊 Reflexo (powerup)',      COR_SEGURO),
    'grito':   ('💀 Grito! Inimigo morto',  COR_OBJ),
    'impacto': ('🧱 Impacto na parede',     COR_NEUTRO),
}


def draw_panel(screen):
    """Desenha painel lateral com plano, objetivo e KB resumida."""
    px_start = width   # começa logo após o mapa
    panel_h  = height + 30
    rect = pygame.Rect(px_start, 0, PANEL_W, panel_h)
    pygame.draw.rect(screen, COR_FUNDO_PAINEL, rect)
    pygame.draw.line(screen, COR_SEPARADOR, (px_start, 0), (px_start, panel_h), 2)

    margin  = 10
    x0      = px_start + margin
    y       = 10
    lh_t    = 22   # altura de linha título
    lh_s    = 18   # altura de linha normal

    def titulo(txt):
        nonlocal y
        t = panel_font.render(txt, True, COR_TITULO)
        screen.blit(t, (x0, y))
        y += lh_t
        pygame.draw.line(screen, COR_SEPARADOR,
                         (x0, y), (px_start + PANEL_W - margin, y), 1)
        y += 4

    def linha(txt, cor=COR_TEXTO):
        nonlocal y
        # Trunca se muito longo
        max_chars = (PANEL_W - 2*margin) // 8
        if len(txt) > max_chars:
            txt = txt[:max_chars-1] + '…'
        t = small_font.render(txt, True, cor)
        screen.blit(t, (x0 + 4, y))
        y += lh_s

    # ── Posição e direção ───────────────────────────────────────────────
    titulo("AGENTE")
    px, py, pdir = player_pos
    linha(f"Pos: ({px}, {py})   Dir: {pdir}")
    linha(f"Energia: {energia}   Pts: {pontuacao}")
    linha(f"Visitados: {len(visitados)}   Certezas: {len(certezas)}")
    y += 6

    # ── Sensores atuais ─────────────────────────────────────────────────
    titulo("SENSORES (posição atual)")
    if sensores_atuais:
        for s in sensores_atuais:
            label, cor = SENSOR_INFO.get(s, (s, COR_NEUTRO))
            linha(label, cor)
    else:
        linha("Nenhum — sala segura", COR_SEGURO)
    y += 6

    # ── Objetivo ────────────────────────────────────────────────────────
    titulo("OBJETIVO")
    if objetivo_atual:
        linha(f"→ ({objetivo_atual[0]}, {objetivo_atual[1]})", COR_OBJ)
    else:
        linha("Nenhum definido", COR_NEUTRO)
    y += 6

    # ── Plano pendente ──────────────────────────────────────────────────
    titulo(f"PLANO  ({len(plano_atual)} ações restantes)")
    if plano_atual:
        # Primeira ação em destaque
        label = ACAO_LABEL.get(plano_atual[0], plano_atual[0])
        linha(f"  {label}", COR_ACAO_PROX)
        # Próximas (até 10)
        for a in plano_atual[1:11]:
            label = ACAO_LABEL.get(a, a)
            linha(f"  {label}", COR_ACAO_REST)
        if len(plano_atual) > 11:
            linha(f"  … +{len(plano_atual)-11} mais", COR_NEUTRO)
    else:
        linha("Plano vazio", COR_NEUTRO)
    y += 6

    # ── Legenda ─────────────────────────────────────────────────────────
    titulo("LEGENDA (teclas)")
    for txt in ["M  mapa real/agente", "A  auto/manual",
                "L  carregar mapa", "R  reiniciar jogo",
                "←→↑  mover (manual)", "SPACE  pegar (manual)"]:
        linha(txt, COR_NEUTRO)


def draw_game_over(screen):
    """Sobrepõe painel semitransparente de fim de jogo sobre a tela inteira."""
    total_w = width + PANEL_W
    total_h = height + 30

    # Overlay escuro semitransparente
    overlay = pygame.Surface((total_w, total_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    # Caixa central
    box_w, box_h = 460, 240
    box_x = (total_w - box_w) // 2
    box_y = (total_h - box_h) // 2
    pygame.draw.rect(screen, (20, 20, 40), (box_x, box_y, box_w, box_h), border_radius=16)
    pygame.draw.rect(screen, (80, 80, 140), (box_x, box_y, box_w, box_h), width=2, border_radius=16)

    # Título e emoji de status
    if game_over_motivo == 'vitoria':
        titulo_txt = '🏆  MISSÃO CONCLUÍDA!'
        cor_titulo = (80, 255, 160)
        subtitulo  = 'Pitfall Harry saiu do labirinto com sucesso.'
    elif game_over_motivo == 'poco':
        titulo_txt = '💀  CAIU NUM POÇO!'
        cor_titulo = (255, 80, 80)
        subtitulo  = 'Harry foi engolido pelas trevas...'
    else:
        titulo_txt = '💀  GAME OVER'
        cor_titulo = (255, 80, 80)
        subtitulo  = 'Harry sucumbiu aos inimigos da floresta.'

    font_grande = pygame.font.Font(pygame.font.get_default_font(), 26)
    font_medio  = pygame.font.Font(pygame.font.get_default_font(), 16)
    font_pts    = pygame.font.Font(pygame.font.get_default_font(), 22)

    t = font_grande.render(titulo_txt, True, cor_titulo)
    screen.blit(t, t.get_rect(centerx=box_x + box_w // 2, top=box_y + 28))

    t = font_medio.render(subtitulo, True, (200, 200, 200))
    screen.blit(t, t.get_rect(centerx=box_x + box_w // 2, top=box_y + 80))

    # Pontuação final em destaque
    pts_txt = f'Pontuação final:  {game_over_pontos}'
    t = font_pts.render(pts_txt, True, (255, 210, 80))
    screen.blit(t, t.get_rect(centerx=box_x + box_w // 2, top=box_y + 120))

    # Linha separadora
    pygame.draw.line(screen, (80, 80, 140),
                     (box_x + 30, box_y + 166), (box_x + box_w - 30, box_y + 166), 1)

    # Instruções
    inst = font_medio.render('R  reiniciar     L  carregar mapa     ESC  sair', True, (140, 140, 160))
    screen.blit(inst, inst.get_rect(centerx=box_x + box_w // 2, top=box_y + 182))


def draw_screen(screen):
    
    screen.fill((0,0,0))
 
    y = 0
    for j in mapa:
        x = 0
        for i in j:

            if (x+1,12-y) in visitados:
                screen.blit(img_floor, (x * img_floor.get_width(), y * img_floor.get_height()))
            else:
                screen.blit(bw_img_floor, (x * bw_img_floor.get_width(), y * bw_img_floor.get_height()))

            if mapa[11-y][x].find('P') > -1:
                if (x+1,12-y) in certezas:
                    screen.blit(img_pit, (x * img_pit.get_width(), y * img_pit.get_height()))                            
                else:
                    screen.blit(bw_img_pit, (x * bw_img_pit.get_width(), y * bw_img_pit.get_height()))                            

            if mapa[11-y][x].find('T') > -1:
                if (x+1,12-y) in certezas:
                    screen.blit(img_bat, (x * img_bat.get_width(), y * img_bat.get_height()))
                else:
                    screen.blit(bw_img_bat, (x * bw_img_bat.get_width(), y * bw_img_bat.get_height()))

            if mapa[11-y][x].find('D') > -1:
                if (x+1,12-y) in certezas:
                    screen.blit(img_enemy1, (x * img_enemy1.get_width(), y * img_enemy1.get_height()))                                               
                else:
                    screen.blit(bw_img_enemy1, (x * bw_img_enemy1.get_width(), y * bw_img_enemy1.get_height()))                                               
                            
            if mapa[11-y][x].find('d') > -1:
                if (x+1,12-y) in certezas:
                    screen.blit(img_enemy2, (x * img_enemy2.get_width(), y * img_enemy2.get_height()))                                               
                else:
                    screen.blit(bw_img_enemy2, (x * bw_img_enemy2.get_width(), y * bw_img_enemy2.get_height()))                                               

            if mapa[11-y][x].find('U') > -1:
                if (x+1,12-y) in certezas:
                    screen.blit(img_health, (x * img_health.get_width(), y * img_health.get_height()))                               
                else:
                    screen.blit(bw_img_health, (x * bw_img_health.get_width(), y * bw_img_health.get_height()))                               

            if mapa[11-y][x].find('O') > -1:
                if (x+1,12-y) in certezas:
                    screen.blit(img_gold, (x * img_gold.get_width(), y * img_gold.get_height()))                
                else:
                    screen.blit(bw_img_gold, (x * bw_img_gold.get_width(), y * bw_img_gold.get_height()))                
            
            if x == player_pos[0] - 1  and  y == 12 - player_pos[1]:
                if player_pos[2] == 'norte':
                    screen.blit(img_player_up, (x * img_player_up.get_width(), y * img_player_up.get_height()))                                               
                elif player_pos[2] == 'sul':
                    screen.blit(img_player_down, (x * img_player_down.get_width(), y * img_player_down.get_height()))                                               
                elif player_pos[2] == 'leste':
                    screen.blit(img_player_right, (x * img_player_right.get_width(), y * img_player_right.get_height()))                                               
                elif player_pos[2] == 'oeste':
                    screen.blit(img_player_left, (x * img_player_left.get_width(), y * img_player_left.get_height()))                                                                                                           
                else:
                    screen.blit(img_tomb, (x * img_tomb.get_width(), y * img_tomb.get_height()))                                                                                                           
            x  += 1
        y +=  1

    t = sys_font.render("Pontuação: " + str(pontuacao), False, (255,255,255))
    screen.blit(t, t.get_rect(top = height + 5, left=40))

    t = sys_font.render(last_action, False, (255,255,255))
    screen.blit(t, t.get_rect(top = height + 5, left=width/2-40))
    
    t = sys_font.render("Energia: " + str(energia), False, (255,255,255))
    screen.blit(t, t.get_rect(top = height + 5, left=width-140))

    draw_panel(screen)

    # Sobrepõe tela de fim de jogo se necessário
    if game_over:
        draw_game_over(screen)

def main_loop(screen):  
    global clock
    running = True
    
    while running:
        for e in pygame.event.get(): 
            if e.type == pygame.QUIT:
                running = False
                break
            
            key_pressed(e)
            
        # Calcula tempo transcorrido desde
        # a última atualização 
        dt = clock.tick()
        
        
        # Atualiza posição dos objetos da tela
        update(dt, screen)
        
        # Desenha objetos na tela 
        draw_screen(screen)

        # Pygame atualiza o seu estado
        pygame.display.update() 


update_prolog()

pygame.init()
pygame.display.set_caption('INF1771 Trabalho 2 - Agente Lógico [AUTO]')
screen = pygame.display.set_mode((width + PANEL_W, height+30))
load()

main_loop(screen)
pygame.quit()