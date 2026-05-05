# Data Folder

This app is deployment-friendly when its supporting files live in this `data/` folder.

## Default files

- `hurtlex_EN.tsv`: required for predictions
- `target_indicators.txt`: required for predictions
- `dataset.xlsx`: optional, used only to load the original dataset summary

## Notes

- The bundled `hurtlex_EN.tsv` is a small starter lexicon so the app can deploy and run immediately.
- Replace it with your full HurtLex file if you want your research version of the detector.
- You can also point the app to files outside the repo by setting:
  - `HURTLEX_PATH`
  - `TARGETS_PATH`
  - `DATASET_PATH`
