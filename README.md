# Cyberbullying Detector

This project is a deployable local web app for rule-based cyberbullying detection. It does not use a database.

## How it works

The detector marks a comment as cyberbullying only when both are present:

1. An offensive word from the HurtLex-style lexicon.
2. A target indicator such as `you`, `your`, `u`, or `@username`.

## Data files

By default the app reads files from [data/README.md](C:/xampp/htdocs/cyberbullying/data/README.md):

- `data/hurtlex_EN.tsv` required
- `data/target_indicators.txt` required
- `data/dataset.xlsx` optional

The repository already includes starter lexicon and target files so deployment can work immediately. If you want your full research version, replace the starter lexicon with your full HurtLex file and add your dataset as `data/dataset.xlsx`.

## Run locally

```powershell
powershell -ExecutionPolicy Bypass -File .\run_dashboard.ps1
```

Then open `http://127.0.0.1:8080`.

## Deployment configuration

You can override the default file locations with environment variables:

- `HURTLEX_PATH`
- `TARGETS_PATH`
- `DATASET_PATH`
- `HOST`
- `PORT`

Example:

```powershell
$env:PORT="8080"
$env:HURTLEX_PATH="C:\path\to\hurtlex_EN.tsv"
$env:TARGETS_PATH="C:\path\to\target_indicators.txt"
python .\app.py
```

## Train-only summary

```powershell
powershell -ExecutionPolicy Bypass -File .\run_dashboard.ps1 --train-only
```

If `data/dataset.xlsx` is missing, the app still runs and predictions still work. Only the dataset summary is skipped.
