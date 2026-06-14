import pandas as pd
df = pd.read_csv('src/championships/2026_world_cup/data/gold/first_round/arquetipos_classification.csv')
print('=== Arquetipo distribution ===')
print(df['arquetipo'].value_counts().to_string())
print()
print('=== Tier distribution ===')
print(df['tier_label'].value_counts().to_string())
print()
print('=== Score range ===')
print(f'Score min: {df["score"].min()}, max: {df["score"].max()}, mean: {df["score"].mean():.1f}')
print()
print('=== Mean score per archetype ===')
print(df.groupby('arquetipo')['score'].describe().to_string())
print()
indef = df[df['arquetipo'] == 'Indefinido']
print(f'Indefinidos: {len(indef)}')
if len(indef) > 0:
    print(indef[['boleiro', 'score']].to_string())
print()
print('=== Sample rows (first 5) ===')
cols = ['boleiro','arquetipo','arquetipo_emoji','score','tier_label'] + [c for c in df.columns if c.endswith('_z')]
print(df[cols].head(10).to_string())
print()
print('=== Z-score ranges ===')
for c in [c for c in df.columns if c.endswith('_z')]:
    print(f'{c}: min={df[c].min()}, max={df[c].max()}, mean={df[c].mean():.1f}')
