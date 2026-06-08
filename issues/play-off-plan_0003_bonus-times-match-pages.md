# play-off-plan_0003_bonus-times-match-pages

## Parent

`play-off-plan.md` — Visão 1 (Página de cada jogo): "Exibir ao lado de cada jogador quantos Bônus Times ele possui naquela fase e se acertou."

## What to Build

Na função `_build_match()` em `html.py`, cada linha de predição de um jogador atualmente mostra: avatar, nome, palpite previsto, critério e pontos. Precisa também exibir, quando aplicável, um indicador dos **Bônus Times** que aquele jogador possui na fase da partida.

O comportamento deve ser:
- Carregar o CSV `playoffs_scored.csv` do gold (que contém `boleiro`, `phase`, `team_picked`, `correct`, `points` por fase).
- Para cada jogador na partida, verificar se ele tem registros de bônus na fase atual.
- Se sim, exibir ao lado do nome algo como `🏆 Bônus: 3/5 acertos (+12 pts)`.
- Se não tiver bônus na fase, não exibir nada.

Isso deve funcionar mesmo quando a fase ainda não foi pontuada (times não definidos), mostrando apenas o número de picks sem pontuação.

## Acceptance Criteria

* [ ] Match page carrega `playoffs_scored.csv` se existir
* [ ] Cada jogador exibe indicador de Bônus Times na fase quando aplicável
* [ ] Indicador mostra número de acertos e pontos (ex: `3/5 ✅ +12 pts`)
* [ ] Se a fase ainda não foi jogada, exibe `5 picks 🕐` sem pontuação
* [ ] Se o jogador não tem bônus naquela fase, não exibe nada (nem linha extra)
* [ ] Não quebra se `playoffs_scored.csv` não existir (fases sem resultados)

## Blocked By

`None - can start immediately`
