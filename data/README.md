# Data Folder

The thesis pipeline reads these files directly from this folder by default:

- `dataset.csv` for model training data
- `hurtlex_EN.tsv` for offensive-word lookup
- `target_indicators.txt` for target-indicator lookup

The trained TF-IDF + Logistic Regression cache is stored as `tfidf_logreg_model.json` after training.
