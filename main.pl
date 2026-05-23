:-dynamic posicao/3.
:-dynamic memory/3.
:-dynamic visitado/2.
:-dynamic certeza/2.
:-dynamic energia/1.
:-dynamic pontuacao/1.
:-dynamic tile/3.
:-dynamic map_size/2.
:-dynamic grito/0.          % sinaliza ao Python que um inimigo morreu (consumido após leitura)
:-dynamic saiu_labirinto/0. % sinaliza que o agente voltou para (1,1) e encerrou

:-consult('mapa.pl').

%% Recarrega o mapa limpando tiles e map_size antigos, depois reinicia o jogo
recarrega_mapa(Arquivo) :-
    retractall(tile(_,_,_)),
    retractall(map_size(_,_)),
    consult(Arquivo),
    reset_game.

delete([], _, []).
delete([Elem|Tail], Del, Result) :-
    (   \+ Elem \= Del
    ->  delete(Tail, Del, Result)
    ;   Result = [Elem|Rest],
        delete(Tail, Del, Rest)
    ).
	


reset_game :- retractall(memory(_,_,_)), 
			retractall(visitado(_,_)), 
			retractall(certeza(_,_)),
			retractall(energia(_)),
			retractall(pontuacao(_)),
			retractall(posicao(_,_,_)),
			retractall(grito),
			retractall(saiu_labirinto),
			retractall(plano(_)),
			retractall(objetivo(_,_)),
			assert(energia(100)),
			assert(pontuacao(0)),
			assert(posicao(1,1, norte)).


:-reset_game.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Controle de Status
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%atualiza pontuacao
atualiza_pontuacao(X):- pontuacao(P), retract(pontuacao(P)), NP is P + X, assert(pontuacao(NP)),!.

%atualiza energia
atualiza_energia(N):- energia(E), retract(energia(E)), NE is E + N, 
					(
					 (NE =<0, assert(energia(0)),posicao(X,Y,_),retract(posicao(_,_,_)), assert(posicao(X,Y,morto)),!);
					 (NE >100, assert(energia(100)),!);
					  (NE >0,assert(energia(NE)),!)
					 ).

%verifica situacao da nova posicao e atualiza energia e pontos

% Poço: morte instantânea
verifica_player :- posicao(X,Y,_), tile(X,Y,'P'), atualiza_energia(-100), atualiza_pontuacao(-1000),!.

% Inimigo pequeno (D): dano 20, remove do mapa e emite grito
verifica_player :- posicao(X,Y,_), tile(X,Y,'D'),
    atualiza_energia(-20), atualiza_pontuacao(-20),
    retract(tile(X,Y,'D')), assert(tile(X,Y,'')),
    set_real(X,Y),
    (grito -> true ; assert(grito)),
    !.

% Inimigo grande (d): dano 50, remove do mapa e emite grito
verifica_player :- posicao(X,Y,_), tile(X,Y,'d'),
    atualiza_energia(-50), atualiza_pontuacao(-50),
    retract(tile(X,Y,'d')), assert(tile(X,Y,'')),
    set_real(X,Y),
    (grito -> true ; assert(grito)),
    !.

% Teletransportador: sorteia nova posição e re-verifica (pode cair em poço, inimigo ou outro T)
% Usa teleporte_seguro/3 para evitar loop infinito com contador de passos
verifica_player :- posicao(X,Y,Z), tile(X,Y,'T'),
    teleportar(X,Y,Z),!.
verifica_player :- true.

% teleportar/3 — sorteia posição aleatória diferente do tile atual e aplica verifica_player
% O loop natural do Prolog (retrying) é controlado pelo contador MaxTentativas
teleportar(OX,OY,Dir) :-
    map_size(SX,SY),
    teleportar_loop(OX,OY,Dir,SX,SY,50).

teleportar_loop(_,_,_,_,_,0) :- !.   % esgotou tentativas — fica onde está
teleportar_loop(OX,OY,Dir,SX,SY,N) :-
    random_between(1,SX,NX),
    random_between(1,SY,NY),
    (   (NX =:= OX, NY =:= OY)
    ->  % caiu no mesmo tile do T — tenta de novo
        N1 is N - 1, teleportar_loop(OX,OY,Dir,SX,SY,N1)
    ;   % nova posição válida: move o agente e re-verifica
        retract(posicao(OX,OY,Dir)),
        assert(posicao(NX,NY,Dir)),
        atualiza_obs,
        verifica_player   % pode re-teleportar se cair em outro T (recursão natural)
    ).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Comandos
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%virar direita
virar_direita :- posicao(X,Y, norte), retract(posicao(_,_,_)), assert(posicao(X, Y, leste)),atualiza_pontuacao(-1),!.
virar_direita :- posicao(X,Y, oeste), retract(posicao(_,_,_)), assert(posicao(X, Y, norte)),atualiza_pontuacao(-1),!.
virar_direita :- posicao(X,Y, sul), retract(posicao(_,_,_)), assert(posicao(X, Y, oeste)),atualiza_pontuacao(-1),!.
virar_direita :- posicao(X,Y, leste), retract(posicao(_,_,_)), assert(posicao(X, Y, sul)),atualiza_pontuacao(-1),!.

%virar esquerda
virar_esquerda :- posicao(X,Y, norte), retract(posicao(_,_,_)), assert(posicao(X, Y, oeste)),atualiza_pontuacao(-1),!.
virar_esquerda :- posicao(X,Y, oeste), retract(posicao(_,_,_)), assert(posicao(X, Y, sul)),atualiza_pontuacao(-1),!.
virar_esquerda :- posicao(X,Y, sul), retract(posicao(_,_,_)), assert(posicao(X, Y, leste)),atualiza_pontuacao(-1),!.
virar_esquerda :- posicao(X,Y, leste), retract(posicao(_,_,_)), assert(posicao(X, Y, norte)),atualiza_pontuacao(-1),!.

%andar
andar :- posicao(X,Y,P), P = norte, map_size(_,MAX_Y), Y < MAX_Y, YY is Y + 1, 
         retract(posicao(X,Y,_)), assert(posicao(X, YY, P)), 
		 %((retract(certeza(X,YY)), assert(certeza(X,YY))); assert(certeza(X,YY))),
		 set_real(X,YY),
		 ((retract(visitado(X,Y)), assert(visitado(X,Y))); assert(visitado(X,Y))),atualiza_pontuacao(-1),!.
		 
andar :- posicao(X,Y,P), P = sul,  Y > 1, YY is Y - 1, 
         retract(posicao(X,Y,_)), assert(posicao(X, YY, P)), 
		 %((retract(certeza(X,YY)), assert(certeza(X,YY))); assert(certeza(X,YY))),
		 set_real(X,YY),
		 ((retract(visitado(X,Y)), assert(visitado(X,Y))); assert(visitado(X,Y))),atualiza_pontuacao(-1),!.

andar :- posicao(X,Y,P), P = leste, map_size(MAX_X,_), X < MAX_X, XX is X + 1, 
         retract(posicao(X,Y,_)), assert(posicao(XX, Y, P)), 
		 %((retract(certeza(XX,Y)), assert(certeza(XX,Y))); assert(certeza(XX,Y))),
		 set_real(XX,Y),
		 ((retract(visitado(X,Y)), assert(visitado(X,Y))); assert(visitado(X,Y))),atualiza_pontuacao(-1),!.

andar :- posicao(X,Y,P), P = oeste,  X > 1, XX is X - 1, 
         retract(posicao(X,Y,_)), assert(posicao(XX, Y, P)), 
		 %((retract(certeza(XX,Y)), assert(certeza(XX,Y))); assert(certeza(XX,Y))),
		 set_real(XX,Y),
		 ((retract(visitado(X,Y)), assert(visitado(X,Y))); assert(visitado(X,Y))),atualiza_pontuacao(-1),!.
		 
%pegar	
pegar :- posicao(X,Y,_), tile(X,Y,'O'), retract(tile(X,Y,'O')), assert(tile(X,Y,'')), atualiza_pontuacao(-1), atualiza_pontuacao(1000), set_real(X,Y),!. 
pegar :- posicao(X,Y,_), tile(X,Y,'U'), retract(tile(X,Y,'U')), assert(tile(X,Y,'')), atualiza_pontuacao(-1), atualiza_energia(20), set_real(X,Y),!. 
pegar :- atualiza_pontuacao(-1),!.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Funcoes Auxiliares de navegação e observação
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
		 
%Define as 4 adjacencias		 
adjacente(X, Y) :- posicao(PX, Y, _), map_size(MAX_X,_),PX < MAX_X, X is PX + 1.  
adjacente(X, Y) :- posicao(PX, Y, _), PX > 1, X is PX - 1.  
adjacente(X, Y) :- posicao(X, PY, _), map_size(_,MAX_Y),PY < MAX_Y, Y is PY + 1.  
adjacente(X, Y) :- posicao(X, PY, _), PY > 1, Y is PY - 1.  

%cria lista com a adjacencias
adjacentes(L) :- findall(Z,(adjacente(X,Y),tile(X,Y,Z)),L).

%define observacoes locais
observacao_loc(brilho,L) :- member('O',L).
observacao_loc(reflexo,L) :- member('U',L).

%define observacoes adjacentes
observacao_adj(brisa,L) :- member('P',L).
observacao_adj(palmas,L) :- member('T',L).
observacao_adj(passos,L) :- member('D',L).
observacao_adj(passos,L) :- member('d',L).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Tratamento de KB e observações
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%consulta e processa observações
% Após atualizar memória e certezas básicas, dispara as regras de inferência de 1ª ordem
atualiza_obs:-
    adj_cand_obs(LP), observacoes(LO), iter_pos_list(LP,LO),
    observacao_certeza, observacao_vazia,
    aplica_inferencias,
    aplica_inferencia_negativa.

%adjacencias candidatas p/ a observacao (aquelas não visitadas)
adj_cand_obs(L) :- findall((X,Y), (adjacente(X, Y), \+visitado(X,Y)), L).

%cria lista de observacoes
observacoes(X) :- adjacentes(L), findall(Y, observacao_adj(Y,L), X).

%itera posicoes da lista para adicionar observacoes
iter_pos_list([], _) :- !.
iter_pos_list([H|T], LO) :- H=(X,Y), 
							((corrige_observacoes_antigas(X, Y, LO),!);
							adiciona_observacoes(X, Y, LO)),
							iter_pos_list(T, LO).							 

%Corrige observacoes antigas na memoria que ficaram com apenas uma adjacencia
corrige_observacoes_antigas(X, Y, []):- \+certeza(X,Y), memory(X,Y,[]).
corrige_observacoes_antigas(X, Y, LO):-
	\+certeza(X,Y), \+ memory(X,Y,[]), memory(X, Y, LM), intersection(LO, LM, L), 
	retract(memory(X, Y, LM)), assert(memory(X, Y, L)).

%Adiciona observacoes na memoria
adiciona_observacoes(X, Y, _) :- certeza(X,Y),!.
adiciona_observacoes(X, Y, LO) :- \+certeza(X,Y), \+ memory(X,Y,_), assert(memory(X, Y, LO)).

%Quando há apenas uma observação e uma unica posição incerta, deduz que a observação está na casa incerta
%e marca como certeza
%observacao_certeza:- findall((X,Y), (adjacente(X, Y), 
%						((\+visitado(X,Y), \+certeza(X,Y));(certeza(X,Y),memory(X,Y,ZZ),ZZ\=[])),
%						memory(X,Y,Z), Z\=[]), L), ((length(L,1),L=[(XX,YY)], assert(certeza(XX,YY)),!);true).
						
observacao_certeza:- observacao_certeza('brisa'),
						observacao_certeza('palmas'),
						observacao_certeza('passos').
						
observacao_certeza(Z):- findall((X,Y), (adjacente(X, Y), 
						((\+visitado(X,Y), \+certeza(X,Y));(certeza(X,Y),memory(X,Y,[Z]))),
						memory(X,Y,[Z])), L), ((length(L,1),L=[(XX,YY)], assert(certeza(XX,YY)),!);true).						

%Quando posição não tem observações
observacao_vazia:- adj_cand_obs(LP), observacao_vazia(LP).
observacao_vazia([]) :- !.
observacao_vazia([H|T]) :- H=(X,Y), ((memory(X,Y,[]), \+certeza(X,Y),assert(certeza(X,Y)),!);true), observacao_vazia(T).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Regras de Inferência em Lógica de 1ª Ordem
%%
%% Princípio: o agente percebe sensores nas casas
%% que visita e infere, com certeza ou suspeita,
%% o conteúdo das casas adjacentes não visitadas.
%%
%% Regra 1 (Poço confirmado):
%%   Para todo (X,Y) não visitado:
%%   SE todos os vizinhos visitados de (X,Y) têm brisa
%%   E há pelo menos 1 vizinho com brisa
%%   ENTÃO (X,Y) contém poço com certeza.
%%
%% Regra 2 (Poço descartado):
%%   SE existe vizinho visitado de (X,Y) SEM brisa
%%   ENTÃO (X,Y) NÃO contém poço → tile seguro.
%%
%% Regra 3 (Inimigo confirmado):
%%   Análogo à Regra 1, usando sensor 'passos'.
%%
%% Regra 4 (Teletransportador confirmado):
%%   Análogo à Regra 1, usando sensor 'palmas'.
%%
%% Regra 5 (Única célula suspeita):
%%   SE existe exatamente 1 célula não visitada adjacente
%%   a uma célula com sensor S
%%   ENTÃO essa célula contém o elemento gerador de S.
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%% Vizinhos visitados de (X,Y) dentro do mapa
vizinhos_visitados(X, Y, Lista) :-
    map_size(MAX_X, MAX_Y),
    findall((VX,VY),
        ( (VX is X+1, VY is Y  , VX =< MAX_X) ;
          (VX is X-1, VY is Y  , VX >= 1     ) ;
          (VX is X,   VY is Y+1, VY =< MAX_Y ) ;
          (VX is X,   VY is Y-1, VY >= 1     ) ),
        Todos),
    include(visitado_pred, Todos, Lista).

visitado_pred((VX,VY)) :- visitado(VX,VY).

%% Regra 1 — Poço confirmado por eliminação:
%% (X,Y) tem poço SE todo vizinho visitado tem brisa
%% E há ao menos 1 vizinho visitado (base de evidência)
infere_poco(X, Y) :-
    \+ visitado(X, Y),
    \+ certeza(X, Y),
    vizinhos_visitados(X, Y, Vizs),
    Vizs \= [],
    forall(member((VX,VY), Vizs),
           (memory(VX,VY,Mem), member(brisa, Mem))).

%% Regra 2 — Poço descartado:
%% (X,Y) é seguro SE existe vizinho visitado sem brisa
infere_seguro_poco(X, Y) :-
    \+ visitado(X, Y),
    vizinhos_visitados(X, Y, Vizs),
    member((VX,VY), Vizs),
    memory(VX, VY, Mem),
    \+ member(brisa, Mem).

%% Regra 3 — Inimigo confirmado:
infere_inimigo(X, Y) :-
    \+ visitado(X, Y),
    \+ certeza(X, Y),
    vizinhos_visitados(X, Y, Vizs),
    Vizs \= [],
    forall(member((VX,VY), Vizs),
           (memory(VX,VY,Mem), member(passos, Mem))).

%% Regra 4 — Teletransportador confirmado:
infere_teleporte(X, Y) :-
    \+ visitado(X, Y),
    \+ certeza(X, Y),
    vizinhos_visitados(X, Y, Vizs),
    Vizs \= [],
    forall(member((VX,VY), Vizs),
           (memory(VX,VY,Mem), member(palmas, Mem))).

%% Regra 5 — Única suspeita adjacente a um sensor:
%% Se há exatamente 1 célula não visitada e não-certa
%% adjacente à posição atual e o sensor S está ativo,
%% essa célula é marcada como certa.
infere_unica_suspeita(Sensor) :-
    posicao(PX, PY, _),
    memory(PX, PY, Mem),
    member(Sensor, Mem),
    findall((AX,AY),
        (adjacente(AX,AY), \+ visitado(AX,AY), \+ certeza(AX,AY)),
        [Unica]),           % exatamente 1 candidato
    Unica = (UX, UY),
    assert(certeza(UX, UY)).

%% aplica_inferencias/0 — chamado a cada atualiza_obs
%% Marca certezas derivadas por inferência e atualiza memória
aplica_inferencias :-
    map_size(MAX_X, MAX_Y),
    forall(
        (between(1,MAX_X,X), between(1,MAX_Y,Y),
         \+ visitado(X,Y),
         (infere_poco(X,Y) ; infere_inimigo(X,Y) ; infere_teleporte(X,Y))),
        ( (certeza(X,Y) -> true ; assert(certeza(X,Y))) )
    ),
    % Regra 5 para cada sensor presente na posição atual
    (infere_unica_suspeita(brisa)  -> true ; true),
    (infere_unica_suspeita(passos) -> true ; true),
    (infere_unica_suspeita(palmas) -> true ; true).

%% Descarta suspeita de poço quando Regra 2 se aplica:
%% remove brisa da memória inferida de (X,Y) se um vizinho seguro prova que não há poço
aplica_inferencia_negativa :-
    map_size(MAX_X, MAX_Y),
    forall(
        (between(1,MAX_X,X), between(1,MAX_Y,Y),
         \+ visitado(X,Y),
         \+ certeza(X,Y),
         infere_seguro_poco(X,Y),
         memory(X,Y,Mem),
         member(brisa, Mem)),
        ( retract(memory(X,Y,Mem)),
          delete(Mem, brisa, NovoMem),
          assert(memory(X,Y,NovoMem)) )
    ).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Quando posicao é visitada, atualiza memoria de posicao com a informação real do mapa 
set_real(X,Y):- ((retract(certeza(X,Y)), assert(certeza(X,Y)),!); assert(certeza(X,Y))), set_real2(X,Y),!.
set_real2(X,Y):- tile(X,Y,'P'), ((retract(memory(X,Y,_)),assert(memory(X,Y,[brisa])),!);assert(memory(X,Y,[brisa]))),!.
set_real2(X,Y):- tile(X,Y,'O'), ((retract(memory(X,Y,_)),assert(memory(X,Y,[brilho])),!);assert(memory(X,Y,[brilho]))),!.
set_real2(X,Y):- tile(X,Y,'T'), ((retract(memory(X,Y,_)),assert(memory(X,Y,[palmas])),!);assert(memory(X,Y,[palmas]))),!.
set_real2(X,Y):- ((tile(X,Y,'D'),!); tile(X,Y,'d')), ((retract(memory(X,Y,_)),assert(memory(X,Y,[passos])),!);assert(memory(X,Y,[passos]))),!.
set_real2(X,Y):- tile(X,Y,'U'), ((retract(memory(X,Y,_)),assert(memory(X,Y,[reflexo])),!);assert(memory(X,Y,[reflexo]))),!.
set_real2(X,Y):- tile(X,Y,''), ((retract(memory(X,Y,_)),assert(memory(X,Y,[])),!);assert(memory(X,Y,[]))),!.


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Mostra mapa real
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
show_player(X,Y) :- posicao(X,Y, norte), write('^'),!.
show_player(X,Y) :- posicao(X,Y, oeste), write('<'),!.
show_player(X,Y) :- posicao(X,Y, leste), write('>'),!.
show_player(X,Y) :- posicao(X,Y, sul), write('v'),!.
show_player(X,Y) :- posicao(X,Y, morto), write('+'),!.

%show_position(X,Y) :- show_player(X,Y),!.
show_position(X,Y) :- (show_player(X,Y); write(' ')), tile(X,Y,Z), ((Z='', write(' '));write(Z)),!.

show_map :- map_size(_,MAX_Y), show_map(1,MAX_Y),!.
show_map(X,Y) :- Y >= 1, map_size(MAX_X,_), X =< MAX_X, show_position(X,Y), write(' | '), XX is X + 1, show_map(XX, Y),!.
show_map(X,Y) :- Y >= 1, map_size(X,_),YY is Y - 1, write(Y), nl, show_map(1, YY),!.
show_map(_,0) :- energia(E), pontuacao(P), write('E: '), write(E), write('   P: '), write(P),!.



%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Mostra mapa conhecido
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

show_mem_info(X,Y) :- memory(X,Y,Z), 
		((visitado(X,Y), write('.'),!); (\+certeza(X,Y), write('?'),!); (certeza(X,Y), write('!'))),
		((member(brisa, Z), write('P'));write(' ')),
		((member(palmas, Z), write('T'));write(' ')),
		((member(brilho, Z), write('O'));write(' ')),
		((member(passos, Z), write('D'));write(' ')),
		((member(reflexo, Z), write('U'));write(' ')),!.

show_mem_info(X,Y) :- \+memory(X,Y,[]), 
			((visitado(X,Y), write('.'),!); (\+certeza(X,Y), write('?'),!); (certeza(X,Y), write('!'))),
			write('     '),!.		
		
		

show_mem_position(X,Y) :- posicao(X,Y,_), 
		((visitado(X,Y), write('.'),!); (certeza(X,Y), write('!'),!); write(' ')),
		write(' '), show_player(X,Y),
		((memory(X,Y,Z),
		((member(brilho, Z), write('O'));write(' ')),
		((member(passos, Z), write('D'));write(' ')),
		((member(reflexo, Z), write('U'));write(' ')),!);
		(write('   '),!)).

		
show_mem_position(X,Y) :- show_mem_info(X,Y),!.


show_mem :- map_size(_,MAX_Y), show_mem(1,MAX_Y),!.
show_mem(X,Y) :- Y >= 1, map_size(MAX_X,_), X =< MAX_X, show_mem_position(X,Y), write('|'), XX is X + 1, show_mem(XX, Y),!.
show_mem(X,Y) :- Y >= 1, map_size(X,_),YY is Y - 1, write(Y), nl, show_mem(1, YY),!.
show_mem(_,0) :- energia(E), pontuacao(P), write('E: '), write(E), write('   P: '), write(P),!.



%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Plano atual (lista de ações atômicas pendentes)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

:-dynamic plano/1.       % plano([virar_direita, andar, andar, ...])
:-dynamic objetivo/2.    % objetivo(X, Y)  — destino atual do agente

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Predicados de consulta ao A* via Python
%% O Python expõe next_step/6 e full_path/6
%% através da integração pyswip ↔ gmap.py.
%% Aqui usamos uma interface Prolog pura:
%% calcular próximo passo considerando bloqueados.
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%% Tiles perigosos: aqueles com certeza de perigo
%% (poço, inimigo, teletransportador confirmado)
tile_perigoso(X, Y) :-
    certeza(X, Y),
    memory(X, Y, Z),
    ( member(brisa,  Z)
    ; member(palmas, Z)
    ; member(passos, Z)
    ).

%% Tile seguro: visitado OU com certeza de lista vazia na memória
tile_seguro(X, Y) :-
    visitado(X, Y), !.
tile_seguro(X, Y) :-
    certeza(X, Y),
    memory(X, Y, Z),
    \+ member(brisa,  Z),
    \+ member(palmas, Z),
    \+ member(passos, Z).

%% Candidatos a explorar: seguros, não visitados, dentro do mapa
candidato_exploracao(X, Y) :-
    map_size(MAX_X, MAX_Y),
    between(1, MAX_X, X),
    between(1, MAX_Y, Y),
    tile_seguro(X, Y),
    \+ visitado(X, Y).

%% Posições com ouro confirmado (brilho real visto)
tem_ouro(X, Y) :-
    certeza(X, Y),
    memory(X, Y, Z),
    member(brilho, Z).

%% Posições com powerup confirmado
tem_powerup(X, Y) :-
    certeza(X, Y),
    memory(X, Y, Z),
    member(reflexo, Z).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Distância de Manhattan (heurística)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

manhattan(X1, Y1, X2, Y2, D) :-
    D is abs(X1 - X2) + abs(Y1 - Y2).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Alvo mais próximo por Manhattan
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

alvo_mais_proximo(Candidatos, TX, TY) :-
    posicao(PX, PY, _),
    findall(D-X-Y,
        (member((X,Y), Candidatos),
         manhattan(PX, PY, X, Y, D)),
        Pares),
    Pares \= [],
    msort(Pares, [_-TX-TY|_]).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Cálculo do próximo passo (BFS/Manhattan)
%% sem chamar Python — usa adjacências seguras
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%% Direção necessária para ir de (X,Y) até (NX,NY)
direcao_para(X, Y, NX, NY, norte) :- NX =:= X, NY is Y + 1.
direcao_para(X, Y, NX, NY, sul)   :- NX =:= X, NY is Y - 1.
direcao_para(X, Y, NX, NY, leste) :- NY =:= Y, NX is X + 1.
direcao_para(X, Y, NX, NY, oeste) :- NY =:= Y, NX is X - 1.

%% Sequência de viradas para alinhar facing → target (caminho mais curto)
viradas(D, D, []) :- !.
viradas(norte, leste,  [virar_direita]) :- !.
viradas(leste,  sul,   [virar_direita]) :- !.
viradas(sul,   oeste,  [virar_direita]) :- !.
viradas(oeste,  norte, [virar_direita]) :- !.
viradas(norte,  sul,   [virar_direita, virar_direita]) :- !.
viradas(leste,  oeste, [virar_direita, virar_direita]) :- !.
viradas(sul,    norte, [virar_esquerda, virar_esquerda]) :- !.
viradas(oeste,  leste, [virar_esquerda, virar_esquerda]) :- !.
viradas(norte, oeste,  [virar_esquerda]) :- !.
viradas(oeste,  sul,   [virar_esquerda]) :- !.
viradas(sul,   leste,  [virar_esquerda]) :- !.
viradas(leste,  norte, [virar_esquerda]) :- !.

%% BFS simples para achar caminho de (SX,SY) até (GX,GY) evitando perigosos
%% Retorna lista de coordenadas [(X1,Y1),(X2,Y2),...,(GX,GY)]
bfs_caminho(SX, SY, GX, GY, Caminho) :-
    bfs([[SX-SY]], GX, GY, [], RevPath),
    reverse(RevPath, Caminho).

bfs([[GX-GY|Resto]|_], GX, GY, _, [GX-GY|Resto]) :- !.
bfs([Atual|Fila], GX, GY, Visitados, Resultado) :-
    Atual = [X-Y|_],
    findall(NX-NY,
        (vizinho_valido(X, Y, NX, NY),
         \+ member(NX-NY, Visitados),
         \+ tile_perigoso(NX, NY)),
        Vizinhos),
    maplist(prepend_caminho(Atual), Vizinhos, NovosCaminhos),
    append(Fila, NovosCaminhos, NovaFila),
    bfs(NovaFila, GX, GY, [X-Y|Visitados], Resultado).

prepend_caminho(Cam, N, [N|Cam]).

vizinho_valido(X, Y, NX, NY) :-
    map_size(MAX_X, MAX_Y),
    (   NX is X+1, NY is Y,   NX =< MAX_X
    ;   NX is X-1, NY is Y,   NX >= 1
    ;   NX is X,   NY is Y+1, NY =< MAX_Y
    ;   NX is X,   NY is Y-1, NY >= 1
    ).

%% Gera lista de ações atômicas a partir de caminho e posição de origem
%% acoes_do_caminho(+Caminho, +CX, +CY, +Facing, -Acoes)
acoes_do_caminho([], _, _, _, []).
acoes_do_caminho([NX-NY|Resto], CX, CY, Facing, Acoes) :-
    direcao_para(CX, CY, NX, NY, Dir),
    viradas(Facing, Dir, Viradas),
    append(Viradas, [andar], PrimeirasAcoes),
    acoes_do_caminho(Resto, NX, NY, Dir, RestAcoes),
    append(PrimeirasAcoes, RestAcoes, Acoes).

%% Monta e armazena plano para ir a (GX, GY)
planeja_ir(GX, GY) :-
    posicao(SX, SY, Facing),
    ( SX =:= GX, SY =:= GY ->
        Plano = []
    ;
        bfs_caminho(SX, SY, GX, GY, Caminho),
        acoes_do_caminho(Caminho, SX, SY, Facing, Plano)
    ),
    retractall(plano(_)),
    retractall(objetivo(_, _)),
    assert(plano(Plano)),
    assert(objetivo(GX, GY)).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Executa próxima ação do plano guardado
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

executa_plano(Acao) :-
    plano([Acao|Resto]),
    retract(plano(_)),
    assert(plano(Resto)),
    % Invalida plano se objetivo já não faz sentido
    ( Resto = [] -> retractall(objetivo(_,_)) ; true ).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% LÓGICA PRINCIPAL DO AGENTE
%% Prioridades (ordem decrescente):
%%   1. Pegar item na posição atual
%%   2. Executar próximo passo do plano vigente
%%   3. Ir buscar ouro com certeza
%%   4. Ir buscar powerup (se energia baixa)
%%   5. Explorar célula segura não visitada
%%   6. Voltar para (1,1) e encerrar
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%% 1. PEGAR — ouro ou powerup na posição atual
executa_acao(pegar) :-
    posicao(X, Y, _),
    ( tile(X, Y, 'O') ; tile(X, Y, 'U') ),
    !.

%% 2. SEGUIR PLANO — se há plano válido e o objetivo ainda existe
executa_acao(Acao) :-
    plano([Acao|_]),
    Acao \= [],
    objetivo(OX, OY),
    % Garante que o objetivo ainda faz sentido
    ( (tem_ouro(OX, OY) ; tem_powerup(OX, OY) ; \+visitado(OX, OY))
    -> true
    ;  retractall(plano(_)), retractall(objetivo(_,_)), fail
    ),
    !,
    executa_plano(Acao).

%% 3. IR BUSCAR OURO com certeza
executa_acao(Acao) :-
    findall((X,Y), tem_ouro(X, Y), Ouros),
    Ouros \= [],
    alvo_mais_proximo(Ouros, TX, TY),
    planeja_ir(TX, TY),
    plano([Acao|_]),
    !,
    executa_plano(Acao).

%% 4. IR BUSCAR POWERUP (se energia ≤ 50)
executa_acao(Acao) :-
    energia(E),
    E =< 50,
    findall((X,Y), tem_powerup(X,Y), Ups),
    Ups \= [],
    alvo_mais_proximo(Ups, TX, TY),
    planeja_ir(TX, TY),
    plano([Acao|_]),
    !,
    executa_plano(Acao).

%% 5. EXPLORAR — célula segura não visitada mais próxima
executa_acao(Acao) :-
    findall((X,Y), candidato_exploracao(X,Y), Candidatos),
    Candidatos \= [],
    alvo_mais_proximo(Candidatos, TX, TY),
    planeja_ir(TX, TY),
    plano([Acao|_]),
    !,
    executa_plano(Acao).

%% 6. VOLTAR PARA (1,1) — sem mais exploração possível
executa_acao(Acao) :-
    posicao(1, 1, _), !,
    % Registra que o agente chegou em casa (usado pelo Python para detectar fim)
    (saiu_labirinto -> true ; assert(saiu_labirinto)),
    % Ainda há item na entrada? Pega. Senão encerra (andar para não travar o loop)
    ( (tile(1,1,'O') ; tile(1,1,'U')) -> Acao = pegar ; Acao = andar ).

executa_acao(Acao) :-
    planeja_ir(1, 1),
    plano([Acao|_]),
    !,
    executa_plano(Acao).

%% Fallback — se tudo falhar, vira à direita e tenta de novo
executa_acao(virar_direita).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Condição de encerramento consultável pelo Python
%%   jogo_encerrado/0 é verdadeiro quando o agente
%%   voltou para (1,1) após explorar o labirinto.
%%   A morte é detectada pelo Python via posicao(_,_,morto).
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
jogo_encerrado :-
    saiu_labirinto,
    posicao(1, 1, _).