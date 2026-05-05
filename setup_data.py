import shutil, os
os.makedirs('data', exist_ok=True)
for f in ['hurtlex_EN.tsv', 'target_indicators.txt']:
    if os.path.exists(f) and not os.path.exists(f'data/{f}'):
        shutil.copy(f, f'data/{f}')
        print(f'Copied {f} -> data/{f}')
    elif os.path.exists(f'data/{f}'):
        print(f'data/{f} already exists')
    else:
        print(f'WARNING: {f} not found')
