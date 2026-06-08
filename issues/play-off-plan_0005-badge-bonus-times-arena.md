# play-off-plan_0005_badge-bonus-times-arena

## Parent

`play-off-plan.md` — Visão 5 (Arena): "Destacar os Bônus Times de cada jogador com badge visual na sua seção do estádio."

## What to Build

Na função `_build_arena()` em `html.py`, a Arena atualmente exibe um gráfico de comparação entre jogadores com pontos diários e acumulados. Cada jogador é selecionável por dropdown.

Para cada jogador, adicionar um badge visual indicando seus Bônus Times:
- Carregar `playoffs_scored.csv` do gold.
- Agrupar por jogador: somar pontos de bônus e número de acertos.
- No JSON embedado de cada jogador (`player_json`), incluir um campo `bonus` com `{ total_points, correct_picks, total_picks }`.
- No JavaScript da Arena, exibir o badge abaixo do nome do jogador no painel de informações.

Se o jogador não tem dados de bônus, não exibir badge.

O badge deve ser visualmente distinto (ex: fundo dourado sutil, ícone de troféu).

## Acceptance Criteria

* [ ] Arena carrega `playoffs_scored.csv` e inclui dados de bônus no JSON embedado por jogador
* [ ] Badge "🏆 Bônus" aparece no painel do jogador quando ele tem dados de bônus
* [ ] Badge mostra pontos totais de bônus e acertos (ex: `+42 pts (15/20 ✅)`)
* [ ] Se o jogador não tem bônus, não exibe badge
* [ ] Não quebra se `playoffs_scored.csv` não existir
* [ ] Visual consistente com tema escuro e mobile-first

## Blocked By

`None - can start immediately`
