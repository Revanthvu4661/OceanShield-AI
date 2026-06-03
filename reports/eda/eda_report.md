# RogueGuard Phase 2 Exploratory Data Analysis

## Scope
Phase 2 explores the baseline modeling candidate set centered on `hour_forecast.csv`, enriched with:
- `day_forecast.csv`
- `beach.csv`
- daily tide aggregates from `tide.csv`

Excluded from this phase:
- `spot.csv`
- `sea_condition_fact.csv`
- `fact_size.csv`
- `fact_shape.csv`
- `fact_texture.csv`

These exclusions follow Phase 1 due to sparse spot-level coverage and grain mismatch against the hourly beach-level forecast table.

## EDA Dataset Used
- Rows: 19,680
- Columns after safe joins/aggregates: 44
- Join policy:
  - `hour_forecast.iddayforecast -> day_forecast.iddayforecast`
  - `day_forecast.idbeach -> beach.idbeach`
  - tide aggregated by `iddayforecast`

## Generated Artifacts
- [correlation_heatmap.svg](D:/ocean/reports/eda/correlation_heatmap.svg)
- [feature_histograms.svg](D:/ocean/reports/eda/feature_histograms.svg)
- [outlier_boxplots.svg](D:/ocean/reports/eda/outlier_boxplots.svg)
- [relationship_analysis.svg](D:/ocean/reports/eda/relationship_analysis.svg)
- [outlier_summary.csv](D:/ocean/reports/eda/outlier_summary.csv)
- [beach_summary.csv](D:/ocean/reports/eda/beach_summary.csv)
- [eda_summary.json](D:/ocean/reports/eda/eda_summary.json)

## Correlation Findings

### Strongest EDA-level predictors
To rank candidate predictors before formal label creation, I used an exploratory continuous `risk_proxy_score` built from standardized:
- `sigheight`
- `swellheight`
- `period`
- `windspeed`
- `windgust`
- `tide_height_range`

This is only an EDA ranking device, not the final Phase 4 label.

### Top correlations with `risk_proxy_score`

| Feature | Correlation |
| --- | ---: |
| `swellheight` | 0.8640 |
| `sigheight` | 0.8050 |
| `windspeed` | 0.6987 |
| `windgust` | 0.5587 |
| `period` | 0.4716 |
| `moon_illumination` | 0.3457 |
| `swelldir` | 0.2326 |
| `maxtemp` | -0.2296 |
| `feelslike` | -0.2052 |
| `windchill` | -0.2034 |

### Top relationships around core wave variables

#### `sigheight`
| Feature | Correlation with `sigheight` |
| --- | ---: |
| `swellheight` | 0.5677 |
| `windspeed` | 0.5039 |
| `windgust` | 0.3649 |
| `moon_illumination` | 0.2447 |
| `watertemp` | -0.2372 |

#### `swellheight`
| Feature | Correlation with `swellheight` |
| --- | ---: |
| `sigheight` | 0.5677 |
| `windspeed` | 0.5502 |
| `windgust` | 0.4074 |
| `period` | 0.3393 |
| `moon_illumination` | 0.3007 |

#### `period`
| Feature | Correlation with `period` |
| --- | ---: |
| `swelldir` | 0.5783 |
| `mintemp` | -0.4281 |
| `dewpoint` | -0.4019 |
| `moon_illumination` | 0.3436 |
| `swellheight` | 0.3393 |

## Distribution Findings
- `windspeed`, `windgust`, `sigheight`, `swellheight`, and `period` show sensible marine forecast spread and should be retained for feature engineering.
- `precipitation` is strongly right-skewed with many zeros and a small set of sharp spikes.
- `pressure` is comparatively tight and stable, which suggests it may work better through derived anomaly features than as a raw standalone driver.
- `watertemp` has a narrow central mass but includes suspicious negative values, supporting anomaly treatment in preprocessing.

## Outlier Analysis

| Feature | Outlier count | Outlier % | Note |
| --- | ---: | ---: | --- |
| `precipitation` | 3,317 | 16.85% | Highly skewed event-driven feature |
| `sigheight` | 1,617 | 8.22% | Important extreme-sea signal, should not be clipped blindly |
| `swellheight` | 1,302 | 6.62% | Important risk-related tail behavior |
| `period` | 679 | 3.45% | Long-period events likely informative |
| `pressure` | 336 | 1.71% | Mild tails |
| `windspeed` | 231 | 1.17% | High-wind episodes worth preserving |
| `watertemp` | 168 | 0.85% | Includes suspicious physical anomalies |
| `windgust` | 14 | 0.07% | Limited extreme tail |

### Outlier interpretation
- The tails in `sigheight`, `swellheight`, `period`, `windspeed`, and `windgust` are likely the most valuable part of the risk signal.
- These should be handled with robust preprocessing, not naïve truncation.
- `watertemp` needs quality screening because negative values are likely sensor or encoding artifacts rather than real ocean temperatures.

## Feature Relationship Analysis
- `swellheight -> sigheight` shows a clear positive relationship and appears to be one of the strongest marine drivers.
- `period -> sigheight` is positive but weaker and likely nonlinear in how it contributes to risk.
- `windspeed -> sigheight` is materially positive, reinforcing wind forcing as a core candidate predictor family.
- `windgust -> risk_proxy_score` is also positively related, suggesting gustiness can add incremental signal beyond sustained wind speed.

## Tide Usefulness
- Tide information can be joined cleanly after aggregation by `iddayforecast`.
- Tide-derived statistics such as:
  - `tide_height_mean`
  - `tide_height_max`
  - `tide_height_range`
  - `high_tide_count`
  - `low_tide_count`
  are structurally valid enrichment candidates.
- In this early EDA pass, tide features showed weaker direct linear relationships than wave and wind variables, so they appear to be secondary rather than primary predictors.

## Important Structural Findings

### 1. Forecasts are almost identical across beaches
- 98.23% of `(date, time)` slices have identical forecast feature values across all beaches.
- Only 2,736 distinct hourly feature combinations exist after dropping IDs and beach/date labels, versus 19,680 total rows.
- This means the current dataset is overwhelmingly temporal and environmental, with very limited beach-specific differentiation.

### 2. Beach metadata may add only light value
- Because hourly forecast values are nearly shared across beaches, static coordinates and beach identifiers are likely to provide only modest incremental signal unless later engineered carefully.

### 3. Duplicate daily natural keys remain a modeling caution
- The Phase 1 duplicate issue in `day_forecast` still matters conceptually.
- For this EDA, all joins were performed with the surrogate key `iddayforecast`, which avoids ambiguous merges.

## Strongest Predictor Candidates Going Into Phase 3
Ranked by combined EDA evidence, the strongest candidates are:
1. `swellheight`
2. `sigheight`
3. `windspeed`
4. `windgust`
5. `period`
6. `swelldir`
7. tide range features as secondary context
8. pressure-derived anomaly features as a likely engineered feature rather than raw input

## Recommended Next Step
Proceed to Phase 3 and engineer marine-intelligence features around:
- wave energy and wave severity
- swell-to-significant-height interactions
- wind forcing and gust amplification
- pressure anomaly or pressure trend proxies
- tide range context
- directional consistency / directional mismatch features
