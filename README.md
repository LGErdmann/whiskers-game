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
| **Professor** | Página inicial → *Sou professor* | Senha: `professor` (padrão) |
| **Aluno** | QR code / link da sala, ou página inicial → *Sou aluno* | Sem senha: **PIN da sala** + **nome** |

- A senha padrão `professor` vale enquanto `TEACHER_PASSWORD` não estiver definida nos
  *secrets* (veja [Configuração](#configuração-streamlit-cloud--settings--secrets)).
  Em produção, troque-a: qualquer pessoa que souber a senha padrão entra como professor.
- No painel da sala, o professor tem um **link de professor** (menu lateral,
  *Seu link de professor*). Guarde-o para voltar à mesma sala; não compartilhe com os alunos.
- O **QR code** e o link dos alunos sempre apontam para
  `https://whiskers-game.streamlit.app/?sala=PIN`. Para usar outro endereço, defina `APP_URL`
  nos *secrets*.

## Como jogar

1. **Professor** entra com a senha e clica em **Gerar sala**. No lugar do login aparecem o
   **PIN**, o **QR code** e, embaixo, o **link** da sala. **Abrir painel da sala** leva ao jogo.
2. **Alunos** já podem entrar: leem o QR code (ou digitam o PIN) e colocam o nome.
   Os nomes aparecem na sala de espera, na tela do professor.
3. O professor escolhe **quantas fases** o jogo terá e, na aba **Montar cena**,
   monta o cenário da fase 1 e clica em **Publicar para a turma**.
4. **Começar jogo**: em cada fase, cada aluno tem um turno, na ordem de entrada.
   O professor escreve a instrução (ex.: *Put Whiskers under the bed*) e o aluno da vez
   arrasta o gato e envia a resposta.
5. O professor dá **0, 25, 50 ou 100 pontos** e a vez passa sozinha para o próximo.
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
