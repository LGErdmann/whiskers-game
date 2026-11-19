"""
Estado compartilhado das salas de jogo.

Todas as sessões do Streamlit rodam no mesmo processo, então um objeto
guardado com st.cache_resource é visto por professor e alunos ao mesmo
tempo. As salas ficam em memória: se o app reiniciar, elas somem.
"""

import copy
import random
import secrets
import threading
import time

import streamlit as st

PONTOS = (0, 25, 50, 100)
CODIGO_LETRAS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
VALIDADE_SALA = 24 * 3600
MAX_NOME = 20
FASES_PADRAO = 3
MAX_FASES = 20

PROMPT_PADRAO = "Where's Whiskers? Put the cat in the right place!"


class _Salas:
    def __init__(self):
        self.lock = threading.RLock()
        self.salas = {}


@st.cache_resource
def _store():
    return _Salas()


def _novo_codigo(existentes):
    while True:
        codigo = "".join(random.choice(CODIGO_LETRAS) for _ in range(5))
        if codigo not in existentes:
            return codigo


def _limpar_antigas(store):
    agora = time.time()
    for codigo in [c for c, s in store.salas.items() if agora - s["criada"] > VALIDADE_SALA]:
        del store.salas[codigo]


def _ranking(sala):
    """Lista de ids ordenada por pontos (empate: quem entrou primeiro)."""
    return sorted(
        sala["ordem"],
        key=lambda pid: (-sala["jogadores"][pid]["pontos"], sala["ordem"].index(pid)),
    )


def ranking(sala):
    return _ranking(sala)


# ------------------------------------------------------------
# Leitura
# ------------------------------------------------------------

def obter(codigo):
    """Cópia da sala (ou None) para desenhar a tela sem segurar o lock."""
    if not codigo:
        return None
    store = _store()
    with store.lock:
        sala = store.salas.get(codigo.upper())
        return copy.deepcopy(sala) if sala else None


def professor_valido(codigo, token):
    sala = obter(codigo)
    return bool(sala and token and secrets.compare_digest(sala["token_prof"], token))


# ------------------------------------------------------------
# Professor
# ------------------------------------------------------------

def criar_sala():
    store = _store()
    with store.lock:
        _limpar_antigas(store)
        codigo = _novo_codigo(store.salas)
        token = secrets.token_urlsafe(16)
        store.salas[codigo] = {
            "codigo": codigo,
            "token_prof": token,
            "criada": time.time(),
            "status": "lobby",          # lobby -> jogando -> intervalo -> jogando ... -> fim
            "fases_total": FASES_PADRAO,
            "fase": 0,                  # fase atual (0 = ainda não começou)
            "jogaram": [],              # pids que já tiveram a vez nesta fase
            "cena_rev_fase": 0,         # rev da cena usada na fase atual
            "cena": None,               # {"room", "items", "rev"}
            "prompt": PROMPT_PADRAO,
            "jogadores": {},            # pid -> {"nome", "pontos", "historico"}
            "ordem": [],                # pids na ordem de entrada
            "vez": None,                # {"pid", "id"}
            "resposta": None,           # {"pid", "vez_id", "cat"}
            "ultimo": None,             # {"pid", "nome", "pontos", "vez_id"}
            "rank_antes": {},           # pid -> posição antes da última pontuação
            "contador_vez": 0,
            "rodada_fim": 0,
        }
        return codigo, token


def _mutar(codigo, fn):
    store = _store()
    with store.lock:
        sala = store.salas.get(codigo)
        if sala is None:
            return None
        return fn(sala)


def publicar_cena(codigo, cena):
    def fn(sala):
        rev = (sala["cena"] or {}).get("rev", 0) + 1
        sala["cena"] = {"room": cena["room"], "items": cena["items"], "rev": rev}
        if sala["status"] == "jogando":
            # Ajuste no meio da fase continua sendo o cenário desta fase
            sala["cena_rev_fase"] = rev
        # Uma cena nova invalida a resposta que estava em avaliação
        sala["resposta"] = None
        return True
    return _mutar(codigo, fn)


def definir_prompt(codigo, texto):
    def fn(sala):
        sala["prompt"] = (texto or "").strip()[:200] or PROMPT_PADRAO
    return _mutar(codigo, fn)


def _dar_vez(sala, pid):
    if pid not in sala["jogadores"]:
        sala["vez"] = None
        return
    sala["contador_vez"] += 1
    sala["vez"] = {"pid": pid, "id": sala["contador_vez"]}
    sala["resposta"] = None


def faltam(sala):
    """Alunos que ainda não jogaram nesta fase, na ordem de entrada."""
    return [pid for pid in sala["ordem"] if pid not in sala["jogaram"]]


def _fim(sala):
    sala["status"] = "fim"
    sala["vez"] = None
    sala["resposta"] = None
    sala["rodada_fim"] += 1


def _proximo(sala):
    """Passa a vez para o próximo que não jogou. Se todos jogaram, a fase acaba."""
    restantes = faltam(sala)
    if restantes:
        _dar_vez(sala, restantes[0])
        return
    sala["vez"] = None
    sala["resposta"] = None
    if not sala["ordem"]:
        return  # sala vazia: espera alguém entrar
    if sala["fase"] >= sala["fases_total"]:
        _fim(sala)
    else:
        sala["status"] = "intervalo"


def _iniciar_fase(sala):
    sala["fase"] += 1
    sala["jogaram"] = []
    sala["status"] = "jogando"
    sala["ultimo"] = None
    sala["cena_rev_fase"] = (sala["cena"] or {}).get("rev", 0)
    sala["vez"] = None
    _proximo(sala)


def definir_fases(codigo, total):
    def fn(sala):
        sala["fases_total"] = max(1, min(int(total), MAX_FASES))
    return _mutar(codigo, fn)


def dar_vez(codigo, pid):
    def fn(sala):
        if sala["status"] == "jogando" and pid in faltam(sala):
            _dar_vez(sala, pid)
    return _mutar(codigo, fn)


def pular(codigo):
    """O aluno da vez perde a vez nesta fase (sem pontos)."""
    def fn(sala):
        vez = sala["vez"]
        if sala["status"] != "jogando" or not vez:
            return
        if vez["pid"] not in sala["jogaram"]:
            sala["jogaram"].append(vez["pid"])
        _proximo(sala)
    return _mutar(codigo, fn)


def comecar(codigo):
    """Começa a fase 1 (do lobby) ou a próxima fase (do intervalo)."""
    def fn(sala):
        if not sala["cena"] or sala["status"] not in ("lobby", "intervalo"):
            return
        if sala["status"] == "intervalo" and sala["cena"]["rev"] == sala["cena_rev_fase"]:
            return  # precisa publicar um cenário novo
        _iniciar_fase(sala)
    return _mutar(codigo, fn)


def pontuar(codigo, pontos):
    """Dá os pontos para o aluno da vez e passa para o próximo."""
    def fn(sala):
        vez = sala["vez"]
        if not vez or vez["pid"] not in sala["jogadores"] or pontos not in PONTOS:
            return False
        sala["rank_antes"] = {pid: i for i, pid in enumerate(_ranking(sala))}
        jogador = sala["jogadores"][vez["pid"]]
        jogador["pontos"] += pontos
        jogador["historico"].append(pontos)
        sala["ultimo"] = {
            "pid": vez["pid"],
            "nome": jogador["nome"],
            "pontos": pontos,
            "vez_id": vez["id"],
            "cat": (sala["resposta"] or {}).get("cat"),
            "cena_rev": (sala["cena"] or {}).get("rev"),
        }
        if vez["pid"] not in sala["jogaram"]:
            sala["jogaram"].append(vez["pid"])
        _proximo(sala)
        return True
    return _mutar(codigo, fn)


def remover_jogador(codigo, pid):
    def fn(sala):
        if pid not in sala["jogadores"]:
            return
        era_vez = (sala["vez"] or {}).get("pid") == pid
        del sala["jogadores"][pid]
        sala["ordem"].remove(pid)
        sala["rank_antes"].pop(pid, None)
        if pid in sala["jogaram"]:
            sala["jogaram"].remove(pid)
        if era_vez and sala["status"] == "jogando":
            _proximo(sala)
    return _mutar(codigo, fn)


def encerrar(codigo):
    return _mutar(codigo, _fim)


def jogar_de_novo(codigo):
    def fn(sala):
        for jogador in sala["jogadores"].values():
            jogador["pontos"] = 0
            jogador["historico"] = []
        sala["status"] = "lobby"
        sala["fase"] = 0
        sala["jogaram"] = []
        sala["vez"] = None
        sala["resposta"] = None
        sala["ultimo"] = None
        sala["rank_antes"] = {}
    return _mutar(codigo, fn)


# ------------------------------------------------------------
# Aluno
# ------------------------------------------------------------

def entrar(codigo, nome):
    nome = " ".join((nome or "").split())[:MAX_NOME]
    if not nome:
        return None

    def fn(sala):
        usados = {j["nome"].lower() for j in sala["jogadores"].values()}
        final, n = nome, 2
        while final.lower() in usados:
            final = f"{nome} {n}"
            n += 1
        pid = secrets.token_urlsafe(8)
        sala["jogadores"][pid] = {"nome": final, "pontos": 0, "historico": []}
        sala["ordem"].append(pid)
        # Quem entra no meio da fase joga nela também; se a sala estava vazia, já é a vez dele
        if sala["status"] == "jogando" and sala["vez"] is None:
            _proximo(sala)
        return pid
    return _mutar(codigo, fn)


def responder(codigo, pid, vez_id, cat):
    def fn(sala):
        vez = sala["vez"]
        if sala["status"] != "jogando" or not vez or vez["pid"] != pid or vez["id"] != vez_id:
            return False
        if sala["resposta"] is not None:
            return False
        sala["resposta"] = {"pid": pid, "vez_id": vez_id, "cat": cat}
        return True
    return _mutar(codigo, fn)
