# RogueGuard Phase 5 Preprocessing Pipeline

## Scope
This phase builds the reusable preprocessing layer for the engineered and labeled RogueGuard dataset.

Implementation:
- [src/preprocess.py](D:/ocean/src/preprocess.py)

## Pipeline Overview
The preprocessing module performs four core tasks:
- rebuild the engineered + labeled modeling frame
- create a chronological train-test split
- handle missing values
- encode and scale model inputs into a reusable feature matrix

## Split Strategy

### Why chronological split was chosen
Phase 2 showed that 98.23% of `(date, time)` slices are nearly identical across beaches, which means a random split would likely leak very similar weather and sea states into both training and testing.

To reduce this optimism bias, the pipeline uses a forward-looking chronological split instead of a random shuffle.

### Actual split window
- Training data ends on `2020-06-14`
- Test data begins on `2020-06-15`

### Split sizes
- Training rows: 15,816
- Test rows: 3,864
- Training unique dates: 90
- Test unique dates: 23

### Class balance after split
- Training positive rate: 5.05%
- Test positive rate: 7.43%

This indicates the holdout period is somewhat rougher than the earlier training period, which makes evaluation more realistic.

## Missing Value Treatment
- Numeric columns are imputed with the training-set median.
- This is especially important for `watertemp`, where 168 suspicious negative source values were converted to null earlier in the pipeline.
- After preprocessing:
  - remaining nulls in training matrix: 0
  - remaining nulls in test matrix: 0

## Scaling Strategy
- Numeric features are scaled with a robust median/IQR transformation:
  - centered by training median
  - divided by training interquartile range

### Why robust scaling was chosen
The EDA showed meaningful heavy tails in:
- `sigheight`
- `swellheight`
- `period`
- `windspeed`
- `precipitation`

Median/IQR scaling is more stable than mean/std scaling under these outlier-heavy marine conditions.

## Categorical Handling
Two columns are treated as categorical and one-hot encoded:
- `moon_phase`
- `idbeach`

### Why `idbeach` is categorical
Although it is numeric in the source data, it is an identifier rather than an ordered measurement. One-hot encoding prevents the model from interpreting beach IDs as ordinal values.

### Unknown category handling
The pipeline reserves an `__unknown__` bucket for unseen categories at inference time.

## Leakage Prevention
The preprocessing layer excludes direct label-construction helpers so downstream models do not learn the answer key.

### Excluded columns
- `rogue_risk_label`
- `rogue_risk_score`
- `sigheight_flag`
- `swellheight_flag`
- `period_flag`
- `windspeed_flag`
- `threshold_hit_count`
- `date`
- `time`
- `hour`

### Why these are excluded
- label helper columns would create direct target leakage
- raw time fields are redundant after cyclical encoding through:
  - `hour_sin`
  - `hour_cos`
  - `daylight_flag`

## Output Summary
- Final transformed training feature count: 71
- Categorical inputs encoded:
  - `moon_phase`
  - `idbeach`
- Numeric inputs scaled with robust transformation
- Null-free train/test matrices ready for model training

## Reusable API
The main entry point is `prepare_preprocessed_data(...)`, which returns:
- `X_train`
- `X_test`
- `y_train`
- `y_test`
- fitted `RoguePreprocessor`
- metadata about split dates, class balance, excluded fields, and feature count

## Key Findings
- The preprocessing pipeline is now fully reusable for later training and evaluation code.
- The chronological split is better aligned with real forecasting use than a random split.
- Direct label leakage has been explicitly removed.
- The data is now model-ready with no remaining nulls.

## Recommended Next Step
Proceed to Phase 6 and train/compare:
- Random Forest
- XGBoost
- LightGBM if available
