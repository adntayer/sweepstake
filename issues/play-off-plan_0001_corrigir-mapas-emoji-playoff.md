# play-off-plan_0001_corrigir-mapas-emoji-playoff

## Parent

`play-off-plan.md` — Etapa 5 dos Próximos Passos.

## What to Build

Adicionar os slugs `"segunda_fase"` e `"terceiro_lugar"` aos dicionários de emoji de fase de playoff em duas views:

1. **Página do jogador** (`html.py`): o dicionário `playoff_emoji_map` na linha ~690 controla o emoji que aparece no histórico de palpites ao lado de cada partida de playoff. Atualmente só cobre `oitavas`, `quartas`, `semi` e `final`. Falta mapear `segunda_fase` e `terceiro_lugar`.

2. **Dashboard** (`dashboard.py`): o dicionário `playoff_emojis` na linha ~702 controla o emoji exibido no acordeão de fases. Mesma lacuna.

O resto do ecossistema já reconhece todos os slugs de fase (`config.playoff_rounds` inclui `segunda_fase` e `terceiro_lugar`, o pipeline já os processa, etc.) — é puramente uma correção de apresentação visual.

## Acceptance Criteria

* [ ] `html.py` — `playoff_emoji_map` inclui `"segunda_fase"` e `"terceiro_lugar"` com emojis definidos
* [ ] `dashboard.py` — `playoff_emojis` inclui `"segunda_fase"` e `"terceiro_lugar"` com emojis definidos
* [ ] Partidas de `segunda_fase` exibem emoji correto no histórico do jogador (boleiro)
* [ ] Partidas de `terceiro_lugar` exibem emoji correto no histórico do jogador
* [ ] Acordeão do dashboard exibe emoji correto para `segunda_fase` e `terceiro_lugar`
* [ ] Fases sem emoji mapeado continuam funcionando sem quebrar (fallback para string vazia ou bola padrão)

## Blocked By

`None - can start immediately`
