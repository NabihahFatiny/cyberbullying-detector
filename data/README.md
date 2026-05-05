# Data Folder

This app is deployment-friendly when its supporting files live in this `data/` folder.

## Default files

- `dataset.csv`: required for TF-IDF + Logistic Regression training
- `hurtlex_EN.tsv`: optional legacy file
- `target_indicators.txt`: optional legacy file

## Notes

- The app trains a local model and caches it as `tfidf_logreg_model.json` after the first run.
- You can point the app to a different dataset outside the repo by setting `DATASET_PATH`.
- The HurtLex and target files are kept only as legacy project resources.
