# Intelligent Real-Time Cyberbullying Detection System

This project is a deployable local web app that uses TF-IDF feature extraction with Logistic Regression for cyberbullying detection. It does not use a database.

## How it works

The detector trains on labeled tweet data and then predicts new text with a machine learning pipeline:

1. Tweet text is normalized and converted into TF-IDF features.
2. A Logistic Regression classifier predicts whether the tweet is cyberbullying.

## Data files

By default the app reads files from [data/README.md](C:/xampp/htdocs/cyberbullying/data/README.md):

- `data/dataset.csv` required for TF-IDF training and prediction
- `data/hurtlex_EN.tsv` optional legacy file
- `data/target_indicators.txt` optional legacy file

The repository now includes a local training dataset at `data/dataset.csv` so the model can train and cache itself automatically. The HurtLex and target files are still kept in the project as legacy resources, but they are no longer used for prediction.

## Run locally

```powershell
powershell -ExecutionPolicy Bypass -File .\run_dashboard.ps1
```

Then open `http://127.0.0.1:8080`.

## Deployment configuration

You can override the default file locations with environment variables:

- `DATASET_PATH`
- `HOST`
- `PORT`

Example:

```powershell
$env:PORT="8080"
$env:DATASET_PATH="C:\path\to\dataset.csv"
python .\app.py
```

## Train-only summary

```powershell
powershell -ExecutionPolicy Bypass -File .\run_dashboard.ps1 --train-only
```

The first run trains the TF-IDF + Logistic Regression model and saves a cache file in `data/tfidf_logreg_model.json`. Later runs reuse that cache until the dataset changes.
