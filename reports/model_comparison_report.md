# RogueGuard Phase 6 Model Training

## Scope
This phase trains and compares the requested classification models for potential rogue-wave risk prediction.

Implementation:
- [src/train.py](D:/ocean/src/train.py)

## Models Trained
- Random Forest
- XGBoost
- LightGBM

## Training Setup
- Input pipeline: [src/preprocess.py](D:/ocean/src/preprocess.py)
- Split strategy: chronological holdout
- Training period end: `2020-06-14`
- Test period start: `2020-06-15`
- Training rows: 15,816
- Test rows: 3,864
- Training positive rate: 5.05%
- Test positive rate: 7.43%

### Imbalance handling
- Random Forest used `class_weight="balanced_subsample"`
- XGBoost used `scale_pos_weight = 18.82`
- LightGBM used `class_weight="balanced"`

## Model Comparison

| Model | Accuracy | Precision | Recall | F1 | ROC AUC | Positive Predictions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| XGBoost | 0.9928 | 0.9744 | 0.9268 | 0.9500 | 0.9992 | 273 |
| LightGBM | 0.9801 | 0.8947 | 0.8293 | 0.8608 | 0.9961 | 266 |
| Random Forest | 0.9565 | 1.0000 | 0.4146 | 0.5862 | 0.9937 | 119 |

## Best Model
Selected best model: `XGBoost`

### Why XGBoost won
- Highest `ROC AUC`: `0.9992`
- Highest `F1`: `0.9500`
- Strong precision-recall balance:
  - Precision: `0.9744`
  - Recall: `0.9268`

This makes it the most balanced option for identifying potential rogue-risk periods without heavily sacrificing either false positives or false negatives.

## Model Behavior Notes

### Random Forest
- Very high precision (`1.0000`) but weak recall (`0.4146`)
- This indicates an overly conservative classifier that misses too many positive-risk periods

### LightGBM
- Strong all-around performance
- Slightly worse than XGBoost on both recall and F1
- Good candidate backup model because it remains highly competitive

### XGBoost
- Best overall separation and strongest minority-class recovery
- Most appropriate default choice for Phase 7 evaluation/export

## Important Interpretation Caveat
These metrics are strong in part because the target is a proxy label created from core marine variables that remain in the feature set:
- `sigheight`
- `swellheight`
- `period`
- `windspeed`

That does not make the comparison invalid, but it does mean:
- the model is learning a proxy severity rule rather than a verified rogue-wave event record
- reported performance reflects success at reproducing the engineered risk label, not confirmed real-world rogue-wave occurrence

## Recommended Next Step
Proceed to Phase 7 and perform:
- confusion matrix
- ROC curve
- precision-recall curve
- SHAP explainability
- feature importance
- model export to:
  - `models/rogue_model.pkl`
  - `models/metadata.json`
