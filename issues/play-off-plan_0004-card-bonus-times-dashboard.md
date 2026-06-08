# play-off-plan_0004_card-bonus-times-dashboard

## Parent

`play-off-plan.md` — Visão 3 (Dashboard): "Card 'Bônus Times' destacando os líderes de acertos nos picks de times e os maiores pontuadores."

## What to Build

Adicionar uma seção/card "🏆 Bônus Times" no dashboard (`index.html`) que destaca:

1. **Maiores pontuadores** — top 3 jogadores que mais somaram pontos com Bônus Times (soma de todas as fases)
2. **Maiores acertadores** — top 3 jogadores com maior taxa de acerto nos picks de times (corretos / total)

O card deve ser gerado na função `generate_dashboard()` em `dashboard.py`, lendo o CSV `playoffs_scored.csv` do gold.

Se não houver dados de bônus (CSV vazio ou inexistente), o card não deve aparecer.

Formato visual: um cartão com grid simples de linhas (posição, nome, pontos/acertos), consistente com o tema escuro existente e responsivo para mobile.

## Acceptance Criteria

* [ ] Dashboard carrega `playoffs_scored.csv` do gold
* [ ] Card "🏆 Bônus Times" aparece quando há dados de bônus
* [ ] Card mostra top 3 maiores pontuadores com nome e pontos
* [ ] Card mostra top 3 maiores acertadores com nome e taxa (ex: `12/16 - 75%`)
* [ ] Se não há dados de bônus, o card não é renderizado (sem quebra)
* [ ] Visual consistente com o tema escuro e mobile-first

## Blocked By

`None - can start immediately`
