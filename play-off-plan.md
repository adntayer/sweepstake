# Plano: Play-Off (Segunda Fase) — Visões e Pipeline

## Conceito

A segunda fase do campeonato (mata-mata) é dividida em 4 rodadas:
- **Oitavas** (8 jogos)
- **Quartas** (4 jogos)
- **Semi** (2 jogos)
- **Final** (1 jogo)

Cada jogador envia **um Excel por fase** com palpites de placar para os jogos daquela fase,
**além do bônus de times** que já existe no Excel da 1ª fase.

---

## Estrutura de Dados

### Raw (entrada)
```
data/raw/playoffs/
  oitavas_Gabão.xlsx
  oitavas_André Tayer.xlsx
  quartas_Gabão.xlsx
  quartas_André Tayer.xlsx
  semi_Gabão.xlsx
  final_Gabão.xlsx
  ...
```

Cada Excel tem o mesmo formato da 1ª fase (9 colunas):
`date, hour, home_team, home_pen, home_goals, x, away_goals, away_pen, away_team`

### Bronze
```
bronze/playoffs/
  group_phase_oitavas_Gabão.csv
  group_phase_quartas_Gabão.csv
  ...
```

### Silver
```
silver/playoffs/
  group_phase_oitavas_Gabão.csv
  ...
```
(mergeado com resultados reais do `games.csv`)

### Gold
```
gold/playoffs/
  group_phase_oitavas_Gabão.csv      (por jogador)
  group_phase_quartas_Gabão.csv
  ...
  oitavas_all.csv                     (agregado)
  oitavas_valido_all.csv
  quartas_all.csv
  quartas_valido_all.csv
  semi_all.csv
  semi_valido_all.csv
  final_all.csv
  final_valido_all.csv
```

---

## Visões (HTML)

### 1. Página de cada jogo
`jogos/oitavas/2025-06-28_16h_palmeiras-vs-botafogo.html`
- Mesmo layout da 1ª fase: score card, distribuição de votos, acertos por critério, lista de palpites

### 2. Página de cada jogador (`boleiros/{Nome}.html`)
- Se houver palpites de play-off, aparecem no histórico com indicador da fase (ex: 🏆 Oitavas)
- Estatísticas totais incluem pontos de play-off + bônus + 1ª fase

### 3. Dashboard (`index.html`)
- Acordeão "Oitavas (8)", "Quartas (4)", etc. com links para os jogos
- "Último Resultado" pega o jogo mais recente (incluindo play-offs)
- "Próximos Jogos" inclui jogos de play-off futuros

### 4. Ranking
- O ranking considera **apenas 1ª fase** (valido_all) por enquanto
- Play-off pode ser integrado futuramente no ranking geral

### 5. Bônus (times)
- Continua sendo computado separadamente (`playoffs_scored.csv`)
- Aparece no Raio-X geral e na página do jogador

---

## Pipeline

### raw → bronze (nova etapa)
```
raw/playoffs/{phase}_{boleiro}.xlsx
  → parse_playoff_stage() → bronze/playoffs/group_phase_{phase}_{boleiro}.csv
```

### bronze → silver (nova etapa)
```
bronze/playoffs/group_phase_{phase}_{boleiro}.csv
  + games.csv (filtrado por round = phase)
  → merge_with_results() → silver/playoffs/group_phase_{phase}_{boleiro}.csv
```

### silver → gold (nova etapa)
```
silver/playoffs/group_phase_{phase}_{boleiro}.csv
  → apply_scoring() → gold/playoffs/group_phase_{phase}_{boleiro}.csv
  → concat all boleiros → gold/playoffs/{phase}_all.csv
  → filtrar valido=1 → gold/playoffs/{phase}_valido_all.csv
```

### HTML reports
```
gold/playoffs/{phase}_valido_all.csv
  → _build_match() → jogos/{phase}/{match}.html
```

---

## Efeito nas Visões Atuais

| Componente | Antes | Depois |
|-----------|-------|--------|
| index.html → acordeão | Oitavas (0), Quartas (0) | Oitavas (8), Quartas (4) etc. |
| Página do jogador | Só 1ª fase no histórico | 1ª fase + Play-offs + Bônus |
| Último Resultado | Último jogo da 1ª fase | Último jogo geral (inclui final) |
| Arena | Só 1ª fase | Só 1ª fase (play-off não incluso) |
| Ranking | Só 1ª fase | Só 1ª fase (play-off separado) |
| Bônus Times | `playoffs_scored.csv` | Mesmo, inalterado |

---

## Adicionar Resultados Sem Quebrar

- `games.csv` já contém todos os 64 jogos com resultados reais
- Se faltar um jogo, basta adicionar linha no `games.csv` e rodar o pipeline
- Merge usa `how="left"` → jogos sem resultado ficam `NaN` e não são pontuados
- Pipeline é **determinística e idempotente**: rodar de novo sempre produz o mesmo resultado

---

## Próximos Passos (Implementação)

1. `config.py` — novos métodos de path para playoffs
2. `loader.py` — `parse_playoff_stage()`
3. `pipeline.py` — estender raw→bronze, bronze→silver, silver→gold
4. `html.py` — gerar páginas de jogos de playoff + integrar no perfil do jogador
5. `dashboard.py` — incluir playoffs no upcoming e acordeão
