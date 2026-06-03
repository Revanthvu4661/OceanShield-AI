# RogueGuard Final ML Report

## Best Model
- Model: XGBoost
- Accuracy: 0.9928
- Precision: 0.9744
- Recall: 0.9268
- F1: 0.9500
- ROC AUC: 0.9992
- PR AUC: 0.9904

## Confusion Matrix
- TN: 3570
- FP: 7
- FN: 21
- TP: 266

## Top Feature Rankings
### Model Importance
```
              feature  importance
        wave_severity    0.518908
             swelldir    0.121944
    marine_risk_index    0.058268
       low_tide_count    0.045793
          wave_energy    0.023485
     daily_temp_range    0.020574
wave_wind_interaction    0.019113
        precipitation    0.018729
          swellheight    0.018604
       wave_steepness    0.016802
```

### SHAP Importance
```
              feature  mean_abs_shap
        wave_severity       2.346465
          swellheight       1.650008
    marine_risk_index       1.599079
            windspeed       1.011950
            sigheight       0.982941
          wave_energy       0.941235
             humidity       0.503964
     wave_power_index       0.364047
wave_wind_interaction       0.361063
               period       0.328430
```

## Inference Example
- Example index: 3205
- Predicted probability: 0.9999
- Predicted label: 1
- True label: 1

## Handoff Notes
- This system predicts potential rogue-wave risk from a proxy severity label, not verified rogue-wave events.
- Production inference must preserve the feature engineering, categorical encoding, and robust scaling used in training.
- Any future frontend/backend integration should load `models/rogue_model.pkl` and the metadata in `models/metadata.json`.
- Future data collection should prioritize verified incident labels and site-specific measurements to reduce proxy-target bias.
