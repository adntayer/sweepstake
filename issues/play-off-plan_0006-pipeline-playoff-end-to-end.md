# play-off-plan_0006_pipeline-playoff-end-to-end

## Parent

`play-off-plan.md` — Próximos Passos 1-3; Pipeline e Estrutura de Dados.

## What to Build

Criar dados de exemplo de playoff e executar o pipeline completo para validar que todas as camadas (raw→bronze→silver→gold) funcionam end-to-end.

Isso envolve:

1. **Criar diretório `raw/playoffs/`** com pelo menos um arquivo Excel por fase para um jogador. O formato deve seguir o mesmo schema da 1ª fase (9 colunas: `date, hour, home_team, home_pen, home_goals, x, away_goals, away_pen, away_team`), com palpites para os jogos daquela fase conforme o `games.csv`.

2. **Executar o pipeline** chamando `run_pipeline(config)` (ou as etapas individuais) para processar:
   - raw→bronze: `parse_playoff_stage()` → CSVs em `bronze/playoffs/`
   - bronze→silver: merge com `games.csv` filtrado por round → CSVs em `silver/playoffs/`
   - silver→gold: `apply_scoring()` + agregação → CSVs em `gold/playoffs/`

3. **Verificar a saída:**
   - `gold/playoffs/{phase}_all.csv` existe e contém dados de todos os jogadores
   - `gold/playoffs/{phase}_valido_all.csv` existe (filtrado por valido=1)
   - Estrutura de colunas correta (mesmas colunas da 1ª fase + pontuação)

4. **Gerar reports HTML** (`generate_html_reports()`) para confirmar que as páginas de jogos de playoff são criadas nos diretórios corretos (`jogos/{phase}/`).

5. **Gerar dashboard** (`generate_dashboard()`) para confirmar que o acordeão mostra as fases de playoff com contagem correta de jogos.

Dados de exemplo podem ser gerados programaticamente (palpites mock) ou manualmente a partir do calendário de jogos.

## Acceptance Criteria

* [ ] `raw/playoffs/` existe com pelo menos um Excel por fase (segunda_fase, oitavas, quartas, semi, final) para um jogador
* [ ] Bronze CSVs são gerados em `bronze/playoffs/` com dados parseados corretamente
* [ ] Silver CSVs são gerados em `silver/playoffs/` com merge dos resultados reais
* [ ] Gold CSVs são gerados em `gold/playoffs/` com pontuação aplicada
* [ ] `{phase}_all.csv` e `{phase}_valido_all.csv` existem para cada fase com dados
* [ ] Páginas HTML de jogos são criadas em `jogos/{phase}/{match}.html`
* [ ] Dashboard exibe acordeão com contagem correta de jogos por fase de playoff
* [ ] Pipeline é idempotente: executar de novo produz o mesmo resultado

## Blocked By

`None - can start immediately`
