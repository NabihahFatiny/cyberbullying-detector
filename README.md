# Intelligent Real-Time Cyberbullying Detection System

This project is a local web application built around the thesis pipeline for real-time cyberbullying detection.

## Thesis-aligned pipeline

1. User enters an English tweet or comment.
2. The text is preprocessed with lowercase conversion, URL removal, hashtag removal, emoji removal, punctuation removal, number removal, special-character removal, tokenization, stopword removal, and lemmatization.
3. `data/hurtlex_EN.tsv` and `data/target_indicators.txt` are loaded at runtime.
4. Pseudo-labeling is generated with this rule:
   `Cyberbullying = HurtLex match AND target indicator or @username`
5. Cleaned text is converted to TF-IDF features.
6. A Logistic Regression model predicts the probability score.
7. The interface displays the detection result, risk score, risk level, confidence score, and explanation.

## Required data files

- `data/dataset.csv`
- `data/hurtlex_EN.tsv`
- `data/target_indicators.txt`

## Run locally

```powershell
powershell -ExecutionPolicy Bypass -File .\run_dashboard.ps1
```

Then open `http://127.0.0.1:8080`.

## Train-only mode

```powershell
powershell -ExecutionPolicy Bypass -File .\run_dashboard.ps1 --train-only
```
