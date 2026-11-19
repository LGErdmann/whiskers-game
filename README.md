# whiskers_game

Where's Whiskers?: jogo em turma para praticar *place prepositions*.

```bash
pip install -r requirements.txt
streamlit run aplicacao.py
```

https://whiskers-game.streamlit.app/

O que mudou em relação à versão anterior, com prints de cada tela: [docs/MUDANCAS.md](docs/MUDANCAS.md).

## Acesso

| Quem | Onde | Login |
|---|---|---|
| **Professor** | Tela inicial do app | Senha: `professor` (padrão) |
| **Aluno** | QR code ou link da sessão | Sem senha: só o **nome** (único na sessão) |

- A senha padrão `professor` vale enquanto `TEACHER_PASSWORD` não estiver definida nos
  *secrets* (veja [Configuração](#configuração-streamlit-cloud--settings--secrets)).
  Em produção, troque-a: qualquer pessoa que souber a senha padrão entra como professor.
- No painel da sala, o professor tem um **link de professor** (menu lateral,
  *Seu link de professor*). Guarde-o para voltar à mesma sala; não compartilhe com os alunos.
- O **QR code** e o link dos alunos sempre apontam para
  `https://whiskers-game.streamlit.app/?sala=PIN`. Para usar outro endereço, defina `APP_URL`
  nos *secrets*.

## Como jogar

1. A tela inicial é só o login do **professor**. Ele entra com a senha e clica em **Gerar sessão**.
   A tela vira o **telão** (PIN, QR code e link), para o projetor. **Abrir painel do professor**
   abre o painel de controle em outra aba ou aparelho.
2. **Alunos** já podem entrar: leem o QR code (ou abrem o link) e colocam o nome.
   Nome repetido recebe "Nome já registrado"; os nomes valem para a sessão toda.
   Os nomes aparecem no telão.
3. O professor escolhe **quantas fases** o jogo terá e, na aba **Montar cena**,
   monta o cenário da fase 1 e clica em **Publicar para a turma**.
4. **Começar jogo**: em cada fase, cada aluno tem um turno, na ordem de entrada.
   O professor escreve a instrução (ex.: *Put Whiskers under the bed*) e o aluno da vez
   arrasta o gato e envia a resposta. No telão, o gato se mexe ao vivo enquanto o aluno arrasta;
   depois que o jogo começa, o QR code fica pequeno no topo para quem chegar atrasado.
5. No painel, o professor dá **0, 25, 50 ou 100 pontos** (o telão não mostra a nota) e a vez
   passa sozinha para o próximo.
   O placar ao lado sobe e desce com setas ▲▼ em tempo real.
6. Depois do turno do último aluno, a fase termina. O professor monta e publica um
   **cenário novo** e clica em **Começar fase N** (o botão só libera com cenário novo).
7. Ao fim da última fase aparece o **pódio** com 1º, 2º e 3º lugar para todos
   (ou antes, com **Encerrar agora**).

## Configuração (Streamlit Cloud → Settings → Secrets)

```toml
TEACHER_PASSWORD = "sua-senha"
APP_URL = "https://whiskers-game.streamlit.app"   # opcional, usado no QR code
```

Sem `TEACHER_PASSWORD`, a senha padrão é `professor`.

## Observações

- As salas ficam na memória do servidor: se o app reiniciar ou "dormir", a sala some
  e é preciso criar outra. Salas expiram após 24 h.
- Cada pasta em `assets/` com um `background.png` vira um mapa; os PNGs de
  `furniture/` e `objects/` aparecem na paleta do professor.
- A cena montada pelo professor fica salva no navegador dele (localStorage).
