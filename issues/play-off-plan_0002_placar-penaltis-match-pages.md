# play-off-plan_0002_placar-penaltis-match-pages

## Parent

`play-off-plan.md` — Visão 1 (Página de cada jogo).

## What to Build

Na função `_build_match()` em `html.py`, o score card atualmente exibe apenas `home_goals x away_goals`. Para jogos de playoff que terminam empatados e vão para pênaltis, o `games.csv` contém as colunas `home_pen` e `away_pen` com o placar da disputa de pênaltis.

Quando essas colunas não forem nulas, o score card deve exibir o placar dos pênaltis abaixo do placar do tempo regulamentar (formato sugerido: `(X - Y nos pênaltis)`).

O dado já está presente no CSV, o pipeline já o carrega para o gold — é apenas uma mudança de renderização no HTML.

## Acceptance Criteria

* [ ] Score card exibe o placar regulamentar normalmente
* [ ] Quando `home_pen` e `away_pen` não são nulos, exibe `(X - Y nos pênaltis)` abaixo do placar
* [ ] Quando `home_pen`/`away_pen` são nulos (jogos sem pênaltis ou ainda não realizados), nada muda
* [ ] Visual consistente com o tema escuro existente (mobile-first, sem quebrar layout)

## Blocked By

`None - can start immediately`
