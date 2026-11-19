import hmac
import html
import inspect
import os

import streamlit as st

import cenario as C
import sala as S


st.set_page_config(
    page_title="Where's Whiskers?",
    page_icon=os.path.join(C.ASSETS_DIR, "characters", "whiskers.png"),
    layout="wide",
    initial_sidebar_state="auto",
)

DEFAULT_APP_URL = "https://whiskers-game.streamlit.app"
SENHA_PADRAO = "professor"
ATUALIZAR = 2

BOTAO_PONTOS = {
    0: "0",
    25: "25",
    50: "50",
    100: "100",
}

VOCABULARIO = """
<div class='vocab-card'>
    <h3>Place Prepositions</h3>
    <ul>
        <li><b>on</b> (em cima de)</li>
        <li><b>under</b> (embaixo de)</li>
        <li><b>in</b> (dentro de)</li>
        <li><b>next to</b> (ao lado de)</li>
        <li><b>between</b> (entre)</li>
        <li><b>behind</b> (atrás de)</li>
        <li><b>in front of</b> (na frente de)</li>
        <li><b>near</b> (perto de)</li>
        <li><b>above</b> (acima de)</li>
        <li><b>below</b> (abaixo de)</li>
        <li><b>inside</b> (dentro)</li>
        <li><b>outside</b> (fora)</li>
        <li><b>beside</b> (ao lado de)</li>
    </ul>
</div>
"""


def _largura_total(fn):
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        params = {}
    return {"width": "stretch"} if "width" in params else {"use_container_width": True}


WIDE = _largura_total(st.button)
WIDE_FORM = _largura_total(st.form_submit_button)


def segredo(nome):
    try:
        return st.secrets.get(nome)
    except Exception:
        return None


def senha_professor():
    return segredo("TEACHER_PASSWORD") or SENHA_PADRAO


def app_url():
    return (segredo("APP_URL") or DEFAULT_APP_URL).rstrip("/")


def link_sala(codigo):
    return f"{app_url()}/?sala={codigo}"


def esc(texto):
    return html.escape(str(texto))


def ir_para(**params):
    st.query_params.from_dict({k: v for k, v in params.items() if v})
    st.rerun()


def novo_valor(valor):
    if not isinstance(valor, dict) or not valor.get("nonce"):
        return None
    vistos = st.session_state.setdefault("nonces", set())
    if valor["nonce"] in vistos:
        return None
    vistos.add(valor["nonce"])
    return valor


def _num(valor, minimo=-1e5, maximo=1e5):
    return max(minimo, min(float(valor), maximo))


def limpar_cena(cena):
    data = C.game_data()
    if not isinstance(cena, dict) or cena.get("room") not in {r["id"] for r in data["rooms"]}:
        return None
    itens = []
    for it in (cena.get("items") or [])[:200]:
        try:
            key = str(it["key"])
            if key not in data["assets"] or key == C.CAT_KEY:
                continue
            itens.append({
                "id": str(it.get("id", ""))[:16],
                "key": key,
                "x": _num(it["x"]),
                "y": _num(it["y"]),
                "w": _num(it["w"], 5, 3000),
                "rot": _num(it.get("rot", 0)) % 360,
                "flip": bool(it.get("flip")),
                "z": _num(it.get("z", 0)),
            })
        except (KeyError, TypeError, ValueError):
            continue
    return {"room": cena["room"], "items": itens} if itens else None


def limpar_gato(cat):
    try:
        return {
            "x": _num(cat["x"]),
            "y": _num(cat["y"]),
            "w": _num(cat["w"], 5, 3000),
            "rot": _num(cat.get("rot", 0)) % 360,
            "flip": bool(cat.get("flip")),
            "z": _num(cat.get("z", 0)),
        }
    except (KeyError, TypeError, ValueError):
        return None


def nome_da_vez(sala):
    pid = (sala["vez"] or {}).get("pid")
    return sala["jogadores"].get(pid, {}).get("nome")


with open(os.path.join(C.FRONTEND_DIR, "css", "streamlit.css"), encoding="utf-8") as _f:
    st.markdown(f"<style>{_f.read()}</style>", unsafe_allow_html=True)


def hero(subtitulo=""):
    st.markdown(
        "<div class='hero'><h1>Where's Whiskers?</h1>"
        + (f"<p>{subtitulo}</p>" if subtitulo else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def caixa_pin(codigo):
    st.markdown(
        f"<div class='pin-box'><div class='label'>PIN da sala</div>"
        f"<div class='pin'>{esc(codigo)}</div></div>",
        unsafe_allow_html=True,
    )


def faixa_fase(sala):
    total_alunos = len(sala["ordem"])
    jogaram = len([p for p in sala["jogaram"] if p in sala["jogadores"]])
    st.markdown(
        f"<div class='fase'><span class='fase-nome'>Fase {sala['fase']} de {sala['fases_total']}</span>"
        f"<span>{jogaram}/{total_alunos} jogaram</span></div>",
        unsafe_allow_html=True,
    )


def faixa_prompt(sala):
    st.markdown(f"<div class='prompt'>{esc(sala['prompt'])}</div>", unsafe_allow_html=True)


def faixa_resultado(sala, pid=None):
    ultimo = sala.get("ultimo")
    if not ultimo:
        return
    pts = ultimo["pontos"]
    quem = "Você" if ultimo["pid"] == pid else esc(ultimo["nome"])
    if pts == 0:
        texto = f"{quem} não pontuou desta vez"
    else:
        texto = f"{quem} ganhou +{pts} pontos!"
    st.markdown(f"<div class='result r{pts}'>{texto}</div>", unsafe_allow_html=True)


def placar_html(sala, pid=None):
    ranking = S.ranking(sala)
    if not ranking:
        corpo = "<div class='lb-empty'>Ninguém entrou ainda…</div>"
    else:
        antes = sala.get("rank_antes") or {}
        ultimo = sala.get("ultimo") or {}
        vez = (sala.get("vez") or {}).get("pid")
        linhas = []
        for i, jid in enumerate(ranking):
            j = sala["jogadores"][jid]
            mov = antes.get(jid, i) - i if antes else 0
            classes = ["lb-row"]
            if i < 3:
                classes.append(f"top{i + 1}")
            if jid == pid:
                classes.append("me")
            seta = ""
            if mov > 0:
                classes.append("up")
                seta = f"<span class='lb-move up'>▲{mov}</span>"
            elif mov < 0:
                classes.append("down")
                seta = f"<span class='lb-move down'>▼{-mov}</span>"
            delta = ""
            if ultimo.get("pid") == jid and ultimo.get("pontos"):
                delta = f"<span class='lb-delta'>+{ultimo['pontos']}</span>"
            posicao = f"{i + 1}º"
            alvo = " (vez)" if jid == vez and sala["status"] == "jogando" else ""
            linhas.append(
                f"<div class='{' '.join(classes)}'>"
                f"<span class='lb-pos'>{posicao}</span>"
                f"<span class='lb-name'>{esc(j['nome'])}{alvo}</span>"
                f"{seta}{delta}"
                f"<span class='lb-score'>{j['pontos']}</span></div>"
            )
        corpo = "".join(linhas)
    return f"<div class='lb'><div class='lb-title'>Placar</div>{corpo}</div>"


def podio(sala, pid=None):
    ranking = S.ranking(sala)
    if not ranking:
        st.info("Ninguém jogou nesta partida.")
        return

    lugares = []
    for lugar in (2, 1, 3):
        if lugar <= len(ranking):
            j = sala["jogadores"][ranking[lugar - 1]]
            coroa = ""
            lugares.append(
                f"<div class='place p{lugar}'>"
                f"<div class='pname'>{coroa}{esc(j['nome'])}</div>"
                f"<div class='pscore'>{j['pontos']} pts</div>"
                f"<div class='block'>{lugar}º</div></div>"
            )
    st.markdown(
        "<div class='podium-title'>Fim de jogo!</div>"
        f"<div class='podium'>{''.join(lugares)}</div>",
        unsafe_allow_html=True,
    )

    if pid in sala["jogadores"]:
        pos = ranking.index(pid) + 1
        pts = sala["jogadores"][pid]["pontos"]
        msg = "Parabéns!" if pos <= 3 else "Boa partida!"
        st.markdown(
            f"<div class='turn'>Você ficou em {pos}º lugar com {pts} pontos. {msg}</div>",
            unsafe_allow_html=True,
        )

    chave = f"baloes_{sala['codigo']}_{sala['rodada_fim']}"
    if not st.session_state.get(chave):
        st.session_state[chave] = True
        st.balloons()


@st.fragment(run_every=ATUALIZAR)
def painel_placar(codigo, pid=None):
    sala = S.obter(codigo)
    if sala is None:
        st.rerun(scope="app")
    if pid is not None and chave_aluno(sala, pid) != st.session_state.get("chave_aluno"):
        st.rerun(scope="app")
    st.markdown(placar_html(sala, pid), unsafe_allow_html=True)


def pagina_inicial():
    hero("Coloque o gato no lugar certo e suba no placar!")
    st.write("")
    aluno, professor = st.columns(2, gap="large")

    with aluno:
        st.subheader("Sou aluno")
        with st.form("entrar_aluno"):
            codigo = st.text_input("PIN da sala", max_chars=5, placeholder="ABCDE")
            nome = st.text_input("Seu nome", max_chars=S.MAX_NOME)
            if st.form_submit_button("Entrar", type="primary", **WIDE_FORM):
                codigo = codigo.strip().upper()
                if not S.obter(codigo):
                    st.error("Sala não encontrada. Confira o PIN.")
                elif not nome.strip():
                    st.error("Digite seu nome.")
                else:
                    pid = S.entrar(codigo, nome)
                    ir_para(sala=codigo, aluno=pid)

    with professor:
        st.subheader("Sou professor")
        if not st.session_state.get("professor_logado"):
            login_professor()
            return

        sala_criada = st.session_state.get("sala_criada")
        if sala_criada and S.obter(sala_criada[0]):
            codigo, token = sala_criada
            qr_com_link(codigo)
            st.button(
                "Abrir painel da sala", type="primary", **WIDE,
                on_click=ir_para_painel, args=(codigo, token),
            )
        else:
            st.write("Login feito. Gere uma sala para os alunos entrarem.")
            if st.button("Gerar sala", type="primary", **WIDE):
                st.session_state["sala_criada"] = S.criar_sala()
                st.rerun()
        if st.button("Sair", **WIDE):
            st.session_state.pop("professor_logado", None)
            st.session_state.pop("sala_criada", None)
            st.rerun()


def login_professor():
    with st.form("login_professor"):
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar como professor", type="primary", **WIDE_FORM):
            if hmac.compare_digest(senha.encode(), senha_professor().encode()):
                st.session_state["professor_logado"] = True
                st.rerun()
            else:
                st.error("Senha incorreta.")
    if senha_professor() == SENHA_PADRAO:
        st.caption(
            "Atenção: usando a senha padrão. Defina `TEACHER_PASSWORD` nos *secrets* "
            "do Streamlit Cloud para proteger o acesso de professor."
        )


def ir_para_painel(codigo, token):
    st.query_params.from_dict({"sala": codigo, "prof": token})


def qr_com_link(codigo):
    url = link_sala(codigo)
    caixa_pin(codigo)
    _, meio, _ = st.columns([1, 2, 1])
    meio.image(C.qr_png(url))
    st.markdown(
        f"<div class='join-url'><a href='{esc(url)}' target='_blank'>{esc(url)}</a></div>",
        unsafe_allow_html=True,
    )


def pagina_sala_inexistente():
    hero()
    st.error("Esta sala não existe mais (ela pode ter expirado ou o app reiniciou).")
    if st.button("Voltar ao início"):
        ir_para()


def pagina_entrada(sala, removido=False):
    hero("Digite seu nome para entrar na partida")
    _, meio, _ = st.columns([1, 2, 1])
    with meio:
        caixa_pin(sala["codigo"])
        if removido:
            st.warning("Você não está mais nesta sala. Entre de novo.")
        with st.form("entrar_nome"):
            nome = st.text_input("Seu nome", max_chars=S.MAX_NOME)
            if st.form_submit_button("Entrar no jogo", type="primary", **WIDE_FORM):
                if not nome.strip():
                    st.error("Digite seu nome.")
                else:
                    pid = S.entrar(sala["codigo"], nome)
                    ir_para(sala=sala["codigo"], aluno=pid)


def vez_ativa(sala, pid):
    vez = sala["vez"] or {}
    return bool(
        sala["status"] == "jogando"
        and sala["cena"]
        and vez.get("pid") == pid
        and sala["resposta"] is None
    )


def chave_aluno(sala, pid):
    if sala is None:
        return None
    ativa = vez_ativa(sala, pid)
    return (
        pid in sala["jogadores"],
        ativa,
        (sala["vez"] or {}).get("id") if ativa else None,
        sala["cena"]["rev"] if ativa else None,
        sala["prompt"] if ativa else None,
    )


@st.fragment(run_every=ATUALIZAR)
def visao_aluno(codigo, pid):
    sala = S.obter(codigo)
    if sala is None or pid not in sala["jogadores"]:
        st.rerun(scope="app")
    nome = sala["jogadores"][pid]["nome"]

    if sala["status"] == "lobby":
        st.markdown(
            f"<div class='lobby-wait'><div class='big'>Você entrou, {esc(nome)}!</div>"
            f"<div>Aguardando o professor começar…</div></div>",
            unsafe_allow_html=True,
        )
        return

    if sala["status"] == "fim":
        podio(sala, pid)
        return

    if sala["status"] == "intervalo":
        pos = S.ranking(sala).index(pid) + 1
        st.markdown(
            f"<div class='lobby-wait'><div class='big'>Fase {sala['fase']} concluída!</div>"
            f"<div>Você está em <b>{pos}º lugar</b>. Aguarde a próxima fase…</div></div>",
            unsafe_allow_html=True,
        )
        return

    faixa_fase(sala)
    faixa_prompt(sala)

    ultimo = sala.get("ultimo") or {}
    if ultimo.get("pid") == pid:
        faixa_resultado(sala, pid)
        if ultimo.get("pontos") == 100:
            chave = f"festa_{ultimo['vez_id']}"
            if not st.session_state.get(chave):
                st.session_state[chave] = True
                st.balloons()

    if not sala["cena"]:
        st.info("O professor está montando a cena…")
        return

    da_vez = nome_da_vez(sala)
    resposta = sala["resposta"]
    if resposta and resposta["pid"] == pid:
        texto = "Resposta enviada! Aguarde o professor."
    elif resposta:
        texto = f"{esc(da_vez)} respondeu. Aguardando o professor…"
    elif da_vez:
        texto = f"Vez de {esc(da_vez)}"
    else:
        texto = "Aguardando o professor…"
    st.markdown(f"<div class='turn'>{texto}</div>", unsafe_allow_html=True)

    st.image(C.scene_image(sala["cena"], resposta["cat"] if resposta else None))


def pagina_aluno(codigo, pid):
    sala = S.obter(codigo)
    me = sala["jogadores"][pid]

    st.markdown(
        f"<div class='topbar'><span><b>Where's Whiskers?</b></span>"
        f"<span>PIN <b>{esc(codigo)}</b></span>"
        f"<span><b>{esc(me['nome'])}</b></span></div>",
        unsafe_allow_html=True,
    )

    principal, lateral = st.columns([3, 1.1], gap="medium")

    with principal:
        if vez_ativa(sala, pid):
            vez_id = sala["vez"]["id"]
            faixa_prompt(sala)
            st.markdown(
                "<div class='turn mine'>Sua vez!</div>",
                unsafe_allow_html=True,
            )
            valor = novo_valor(C.player_board(sala["cena"], vez_id, key=f"player_{vez_id}"))
            if valor and valor.get("action") == "answer":
                cat = limpar_gato(valor.get("cat"))
                if cat and S.responder(codigo, pid, vez_id, cat):
                    st.rerun()
        else:
            visao_aluno(codigo, pid)

        with st.expander("Place prepositions"):
            st.markdown(VOCABULARIO, unsafe_allow_html=True)

    st.session_state["chave_aluno"] = chave_aluno(S.obter(codigo), pid)

    with lateral:
        painel_placar(codigo, pid)


def mais_opcoes(sala):
    codigo = sala["codigo"]
    with st.expander("Mais opções"):
        if sala["status"] == "jogando":
            with st.form("form_prompt", border=False):
                texto = st.text_input("Instrução para a turma", value=sala["prompt"], key=f"prompt_{codigo}")
                if st.form_submit_button("Mudar instrução"):
                    S.definir_prompt(codigo, texto)

            restantes = S.faltam(sala)
            if len(restantes) > 1:
                escolha_col, dar_col = st.columns([3, 1], vertical_alignment="bottom")
                escolhido = escolha_col.selectbox(
                    "Escolher quem joga agora", restantes,
                    format_func=lambda j: sala["jogadores"][j]["nome"],
                    key="escolha_vez",
                )
                dar_col.button("Dar a vez", on_click=S.dar_vez, args=(codigo, escolhido), **WIDE)

        if sala["ordem"]:
            remover_col, botao_col = st.columns([3, 1], vertical_alignment="bottom")
            removido = remover_col.selectbox(
                "Remover aluno da sala", sala["ordem"],
                format_func=lambda j: sala["jogadores"][j]["nome"],
                key="escolha_remover",
            )
            botao_col.button("Remover", on_click=S.remover_jogador, args=(codigo, removido), **WIDE)

        if sala["status"] in ("jogando", "intervalo"):
            st.button("Encerrar o jogo e mostrar o pódio", on_click=S.encerrar, args=(codigo,))


def professor_lobby(sala):
    codigo = sala["codigo"]
    qr_com_link(codigo)
    n = len(sala["ordem"])
    st.markdown(f"<div class='count'>{n} aluno{'s' if n != 1 else ''}</div>", unsafe_allow_html=True)

    nomes = "".join(f"<span class='chip'>{esc(sala['jogadores'][j]['nome'])}</span>" for j in sala["ordem"])
    st.markdown(
        f"<div class='chips'>{nomes or '<i>Aguardando alunos…</i>'}</div>",
        unsafe_allow_html=True,
    )
    st.write("")

    if not sala["cena"]:
        st.info("Monte o cenário da fase 1 na aba **Montar cena** e clique em **Publicar para a turma**.")

    fases_col, comecar_col = st.columns([1, 2], vertical_alignment="bottom")
    fases = fases_col.number_input(
        "Fases", min_value=1, max_value=S.MAX_FASES,
        value=sala["fases_total"], step=1, key=f"fases_{codigo}",
    )
    if fases != sala["fases_total"]:
        S.definir_fases(codigo, fases)
    comecar_col.button(
        "Começar jogo", type="primary", **WIDE,
        disabled=not (sala["cena"] and sala["ordem"]),
        on_click=S.comecar, args=(codigo,),
    )
    mais_opcoes(sala)


def professor_jogando(sala):
    codigo = sala["codigo"]
    faixa_fase(sala)
    faixa_prompt(sala)
    faixa_resultado(sala)

    if not sala["ordem"]:
        st.info("Nenhum aluno na sala. Compartilhe o QR code ou o PIN.")
        mais_opcoes(sala)
        return

    da_vez = nome_da_vez(sala)
    resposta = sala["resposta"]

    vez_col, pular_col = st.columns([3, 1], vertical_alignment="center")
    if da_vez:
        status = "respondeu" if resposta else "está jogando…"
        vez_col.markdown(f"<div class='turn'>Vez de <b>{esc(da_vez)}</b>: {status}</div>", unsafe_allow_html=True)
    pular_col.button("Pular aluno", on_click=S.pular, args=(codigo,), **WIDE, disabled=not da_vez)

    if sala["cena"]:
        st.image(C.scene_image(sala["cena"], resposta["cat"] if resposta else None))

    with st.container(key="pontos"):
        for coluna, pts in zip(st.columns(len(S.PONTOS)), S.PONTOS):
            coluna.button(
                BOTAO_PONTOS[pts], key=f"pts_{pts}", **WIDE,
                disabled=resposta is None,
                on_click=S.pontuar, args=(codigo, pts),
            )
    mais_opcoes(sala)


def professor_intervalo(sala):
    codigo = sala["codigo"]
    proxima = sala["fase"] + 1
    cenario_novo = sala["cena"] and sala["cena"]["rev"] != sala["cena_rev_fase"]

    if cenario_novo:
        texto = f"Cenário da fase {proxima} publicado. Pode começar!"
    else:
        texto = f"Monte o cenário da fase {proxima} na aba <b>Montar cena</b> e publique."
    st.markdown(
        f"<div class='lobby-wait'><div class='big'>Fase {sala['fase']} concluída!</div>"
        f"<div>{texto}</div></div>",
        unsafe_allow_html=True,
    )
    st.write("")
    if cenario_novo:
        st.image(C.scene_image(sala["cena"]), width=420)

    st.button(
        f"Começar fase {proxima} de {sala['fases_total']}", type="primary", **WIDE,
        disabled=not cenario_novo, on_click=S.comecar, args=(codigo,),
    )
    mais_opcoes(sala)


def professor_fim(sala):
    podio(sala)
    st.button(
        "Nova partida (zera os pontos)", type="primary", **WIDE,
        on_click=S.jogar_de_novo, args=(sala["codigo"],),
    )


@st.fragment(run_every=ATUALIZAR)
def painel_professor(codigo):
    sala = S.obter(codigo)
    if sala is None:
        st.rerun(scope="app")
    if sala["status"] == "lobby":
        professor_lobby(sala)
    elif sala["status"] == "jogando":
        professor_jogando(sala)
    elif sala["status"] == "intervalo":
        professor_intervalo(sala)
    else:
        professor_fim(sala)


def pagina_professor(codigo, token):
    url = link_sala(codigo)

    with st.sidebar:
        st.markdown("<h1 class='main-title'>Where's Whiskers?</h1>", unsafe_allow_html=True)
        caixa_pin(codigo)
        st.image(C.qr_png(url))
        st.code(url, language=None)
        with st.expander("Seu link de professor"):
            st.caption("Guarde para voltar a esta sala. Não compartilhe!")
            st.code(f"{app_url()}/?sala={codigo}&prof={token}", language=None)
        with st.expander("Place prepositions"):
            st.markdown(VOCABULARIO, unsafe_allow_html=True)
        if st.button("Sair", **WIDE):
            ir_para()

    principal, lateral = st.columns([3, 1.1], gap="medium")

    with principal:
        aba_jogo, aba_cena = st.tabs(["Jogo", "Montar cena"])

        with aba_cena:
            valor = novo_valor(C.editor_board())
            if valor and valor.get("action") == "publish":
                cena = limpar_cena(valor.get("scene"))
                if cena:
                    S.publicar_cena(codigo, cena)
                    st.toast("Cena publicada para a turma!")
            st.caption("O Whiskers fica de fora: quem posiciona são os alunos.")

        with aba_jogo:
            painel_professor(codigo)

    with lateral:
        painel_placar(codigo)


params = st.query_params
codigo_url = (params.get("sala") or "").strip().upper()

if not C.game_data()["rooms"]:
    st.error("No maps found. Add a folder with a background.png inside assets/.")
elif not codigo_url:
    pagina_inicial()
else:
    sala_atual = S.obter(codigo_url)
    token_prof = params.get("prof")
    aluno_id = params.get("aluno")
    if sala_atual is None:
        pagina_sala_inexistente()
    elif token_prof and S.professor_valido(codigo_url, token_prof):
        pagina_professor(codigo_url, token_prof)
    elif aluno_id and aluno_id in sala_atual["jogadores"]:
        pagina_aluno(codigo_url, aluno_id)
    else:
        pagina_entrada(sala_atual, removido=bool(aluno_id))
