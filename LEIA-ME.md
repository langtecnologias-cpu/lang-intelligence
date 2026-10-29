# LANG Intelligence — publicação automática

Este repositório guarda as artes e publica sozinho no Instagram @langintelligence (post, story e reels por dia, durante 30 dias).

- `calendario.csv` — o que sai em cada dia e horário (id, data, horário, tipo, arquivos, frase, legenda). Tipos: `imagem` (feed), `story`, `reel`.
- `posts/`, `stories/`, `reels/` — as mídias (o GitHub Pages as deixa públicas e o Instagram busca por lá).
- `publicar.py` — script que publica pela API oficial da Meta (Instagram API com login do Instagram).
- `.github/workflows/postar.yml` — três partidas por dia (07h07, 12h23 e 16h51 de Brasília); cada uma fica ~5h25 conferindo o calendário a cada 2 minutos.
- `postado.csv` — registro do que já foi publicado (criado sozinho pelo robô; nunca sobrescrever).

## Segredos (Settings > Secrets and variables > Actions)
| Onde | Nome | Valor |
|---|---|---|
| Secrets | `IG_TOKEN` | token de acesso de longa duração da conta @langintelligence |
| Secrets | `IG_USER_ID` | id numérico da conta @langintelligence |
| Variables | `BASE_URL` | `https://USUARIO.github.io/lang-intelligence` (sem barra no fim) |

## Testar (Actions > postar-no-instagram > Run workflow)
1. `verificar` — confirma que o token e o id funcionam. Não publica nada.
2. `simular` — lista o que publicaria agora. Não publica nada.
3. `publicar` com `id` = P01 — publica o post do dia 1 de verdade (teste real, só com aval).

## Se algo der errado
- "Arquivo não acessível": o GitHub Pages ainda não publicou (espere 2 min) ou o arquivo não foi enviado.
- Erro de token: gere outro no painel do app da Meta e troque o segredo `IG_TOKEN`.
- Aviso amarelo "token DIFERENTE": troque o segredo `IG_TOKEN` pelo novo valor.
