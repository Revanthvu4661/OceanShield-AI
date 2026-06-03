# RogueGuard Phase 1 Dataset Inspection

## Scope
This report inspects the provided CSV files with `hour_forecast.csv` as the primary training dataset candidate for potential rogue-wave risk prediction.

## Dataset Inventory

| Dataset | Rows | Columns | Primary role | Initial usefulness |
| --- | ---: | ---: | --- | --- |
| `hour_forecast.csv` | 19,680 | 20 | Core hourly marine-weather and wave forecast features | High |
| `day_forecast.csv` | 820 | 11 | Daily context keyed by `iddayforecast` and `idbeach` | High |
| `tide.csv` | 3,420 | 5 | Tide events keyed by `iddayforecast` | Medium |
| `beach.csv` | 7 | 7 | Beach master data and coordinates | Medium |
| `spot.csv` | 10 | 5 | Spot-level metadata under beaches | Low-Medium |
| `sea_condition_fact.csv` | 554 | 8 | Spot-level observed surf quality scores | Low for baseline |
| `fact_size.csv` | 503 | 15 | Spot-level surf size descriptors/probabilities | Low for baseline |
| `fact_shape.csv` | 503 | 14 | Spot-level surf shape descriptors/probabilities | Low for baseline |
| `fact_texture.csv` | 504 | 11 | Spot-level texture descriptors/probabilities | Low for baseline |

## Primary Training Dataset: `hour_forecast.csv`

### Shape
- Rows: 19,680
- Columns: 20
- Grain: one row per `iddayforecast` and hour (`time`)
- Confirmed uniqueness of natural hourly key: `iddayforecast + time`

### Column List
`idhourforecast`, `iddayforecast`, `time`, `temperature`, `windspeed`, `winddirdegree`, `preciptation`, `humidity`, `pressure`, `cloundover`, `heatIndex`, `dewpoint`, `windchill`, `windgust`, `feelslike`, `sigheight`, `swellheight`, `swelldir`, `period`, `watertemp`

### Dtypes

| Column | Dtype |
| --- | --- |
| `idhourforecast` | int64 |
| `iddayforecast` | int64 |
| `time` | int64 |
| `temperature` | int64 |
| `windspeed` | int64 |
| `winddirdegree` | int64 |
| `preciptation` | float64 |
| `humidity` | int64 |
| `pressure` | int64 |
| `cloundover` | int64 |
| `heatIndex` | int64 |
| `dewpoint` | int64 |
| `windchill` | int64 |
| `windgust` | int64 |
| `feelslike` | int64 |
| `sigheight` | float64 |
| `swellheight` | float64 |
| `swelldir` | int64 |
| `period` | float64 |
| `watertemp` | int64 |

### Data Quality
- Missing values: none in any column
- Exact duplicate rows: 0
- Surrogate primary key `idhourforecast`: unique
- Join key `iddayforecast`: complete and valid against `day_forecast`

### Basic Statistics

| Feature | Min | 25% | Median | Mean | 75% | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `temperature` | 10 | 18 | 20 | 19.95 | 22 | 29 |
| `windspeed` | 1 | 12 | 17 | 17.42 | 22 | 42 |
| `winddirdegree` | 0 | 104 | 195 | 190.60 | 296 | 360 |
| `preciptation` | 0.0 | 0.0 | 0.0 | 0.29 | 0.1 | 21.1 |
| `humidity` | 25 | 68 | 78 | 76.34 | 87 | 98 |
| `pressure` | 1006 | 1015 | 1017 | 1017.28 | 1020 | 1030 |
| `cloundover` | 0 | 7 | 30 | 38.74 | 68 | 100 |
| `windgust` | 3 | 24 | 32 | 30.90 | 38 | 60 |
| `sigheight` | 0.1 | 0.6 | 0.7 | 0.74 | 0.8 | 1.5 |
| `swellheight` | 0.2 | 0.6 | 0.6 | 0.70 | 0.8 | 1.5 |
| `swelldir` | 10 | 40 | 50 | 64.68 | 90 | 330 |
| `period` | 2.5 | 6.5 | 7.7 | 8.23 | 9.4 | 15.9 |
| `watertemp` | -2 | 20 | 23 | 21.95 | 25 | 26 |

### Immediate Observations
- `hour_forecast` appears complete and model-ready from a null/duplicate perspective.
- Wave-related predictors already exist in the core file: `sigheight`, `swellheight`, `period`, `swelldir`.
- Wind forcing is also directly represented: `windspeed`, `windgust`, `winddirdegree`.
- `watertemp` contains `-2`, which is physically suspicious and should be treated as a likely anomaly in preprocessing.
- Two column names contain typos from source data: `preciptation` and `cloundover`. These should be normalized in feature/preprocessing code, not altered in raw source files.

## Full Schema Summary

### `beach.csv`
- Shape: 7 x 7
- Columns: `idbeach`, `name`, `city`, `state`, `country`, `latitude`, `longitude`
- Quality: no missing values, no duplicate rows
- Key: `idbeach`

### `day_forecast.csv`
- Shape: 820 x 11
- Columns: `iddayforecast`, `date`, `sunrise`, `sunset`, `moonset`, `moonrise`, `moon_phase`, `moon_illumination`, `maxtemp`, `mintemp`, `idbeach`
- Quality: no missing values, no exact duplicate rows
- Key: `iddayforecast`
- Date range: 2020-02-25 to 2020-08-30

### `tide.csv`
- Shape: 3,420 x 5
- Columns: `idtide`, `iddayforecast`, `time`, `height`, `type`
- Quality: no missing values, no duplicate rows
- Key: `idtide`
- Join integrity: all `iddayforecast` values match `day_forecast`

### `spot.csv`
- Shape: 10 x 5
- Columns: `idspot`, `name`, `spot_dir_degree`, `sand_size`, `idbeach`
- Quality: no missing values, no duplicate rows
- Key: `idspot`
- Note: `name` is not unique; `Centro` appears three times

### `sea_condition_fact.csv`
- Shape: 554 x 8
- Columns: `idseaConditionFact`, `bulk`, `texture`, `shape`, `uniformity`, `score`, `date`, `idspot`
- Quality: no missing values, no duplicate rows
- Key: `idseaConditionFact`
- Coverage note: only 2 spots (`idspot` 380 and 386)
- Date range: 2020-03-05 06:00:00 to 2020-06-15 17:00:00

### `fact_size.csv`
- Shape: 503 x 15
- Columns: `id`, `wind_direction`, `spot`, `wind_speed`, `fact_size`, `date`, `description`, `flat_probability`, `small_probability`, `medium_probability`, `big_probability`, `biggest_probability`, `period`, `swell_direction`, `swell_size`
- Quality: no missing values, no duplicate rows
- Key: `id`
- Coverage note: only 2 spot names (`Canal da Barra`, `Deck Salva Vidas`)

### `fact_shape.csv`
- Shape: 503 x 14
- Columns: `id`, `wind_direction`, `spot`, `wind_speed`, `fact_shape`, `date`, `description`, `wide_probability`, `barrel_probability`, `closing_probability`, `lineup_probability`, `period`, `swell_direction`, `swell_size`
- Quality: no missing values, no duplicate rows
- Key: `id`
- Coverage note: only 2 spot names (`Canal da Barra`, `Deck Salva Vidas`)

### `fact_texture.csv`
- Shape: 504 x 11
- Columns: `id`, `wind_direction`, `spot`, `wind_speed`, `fact_texture`, `date`, `description`, `flat_probability`, `frizzy_probability`, `stirred_probability`, `restless_probability`
- Quality: no missing values, no duplicate rows
- Key: `id`
- Coverage note: 3 spot names, but one (`Camping da Barra`) appears only once

## Relationship Analysis and Data Dictionary

### Join Graph
- `hour_forecast.iddayforecast` -> `day_forecast.iddayforecast`
- `tide.iddayforecast` -> `day_forecast.iddayforecast`
- `day_forecast.idbeach` -> `beach.idbeach`
- `spot.idbeach` -> `beach.idbeach`
- `sea_condition_fact.idspot` -> `spot.idspot`
- `fact_size.spot` -> `spot.name` (text join only, not a safe primary/foreign key)
- `fact_shape.spot` -> `spot.name` (text join only, not a safe primary/foreign key)
- `fact_texture.spot` -> `spot.name` (text join only, not a safe primary/foreign key)

### Data Dictionary

| Dataset | Primary key | Foreign keys / join keys | Join opportunity | Feature usefulness |
| --- | --- | --- | --- | --- |
| `hour_forecast` | `idhourforecast` | `iddayforecast` | Join to `day_forecast` for beach/date context | Core predictive source |
| `day_forecast` | `iddayforecast` | `idbeach` | Join to `beach`; parent of `hour_forecast` and `tide` | Strong contextual enrichment |
| `beach` | `idbeach` | None | Join from `day_forecast` and `spot` | Useful static geo metadata |
| `tide` | `idtide` | `iddayforecast` | Aggregate by day and merge to hourly rows | Likely useful marine feature source |
| `spot` | `idspot` | `idbeach` | Spot-level mapping only | Low baseline usefulness because `hour_forecast` is beach-level |
| `sea_condition_fact` | `idseaConditionFact` | `idspot` | Possible partial enrichment after heavy aggregation | Risky for baseline due sparse spot coverage |
| `fact_size` | `id` | `spot` (text only) | Weak text-based join through `spot.name` | Likely exclude initially |
| `fact_shape` | `id` | `spot` (text only) | Weak text-based join through `spot.name` | Likely exclude initially |
| `fact_texture` | `id` | `spot` (text only) | Weak text-based join through `spot.name` | Likely exclude initially |

## Key Data Quality Findings

### Clean areas
- All inspected datasets have zero missing values.
- All inspected datasets have zero exact duplicate rows.
- Surrogate keys are present and unique in every table.
- `hour_forecast -> day_forecast`, `tide -> day_forecast`, `day_forecast -> beach`, `spot -> beach`, and `sea_condition_fact -> spot` all have full referential coverage.

### Risks and anomalies
1. `day_forecast` has duplicate natural keys on `(idbeach, date)`.
   - 63 rows are part of repeated beach-date combinations.
   - This means `iddayforecast` must be treated as the only stable daily key.
2. The duplication propagates into `hour_forecast` if users try to define a natural key as `(idbeach, date, time)`.
   - 840 duplicated hourly natural-key rows were found after joining through `day_forecast`.
   - Among duplicated groups, 336 groups are exact repeats and 336 groups have conflicting forecast values.
3. Spot-level fact datasets are coverage-limited and structurally awkward for the baseline model.
   - `sea_condition_fact` covers only 2 spots.
   - `fact_size` and `fact_shape` cover only 2 spots.
   - `fact_texture` covers 3 spots, but one spot has only 1 row.
   - These tables rely on spot names or spot IDs, while `hour_forecast` is beach-level and would require lossy aggregation or ambiguous joins.
4. Some source fields are likely noisy or require domain cleaning.
   - `watertemp = -2` is likely invalid.
   - `time` is stored as integer HHMM rather than a true timestamp.
   - `preciptation` and `cloundover` appear to be misspelled source column names.

## Recommended Dataset Usage for Modeling

### Include in the initial modeling path
- `hour_forecast.csv`
- `day_forecast.csv`
- `tide.csv`
- `beach.csv`

### Exclude from the baseline model for now
- `spot.csv`
- `sea_condition_fact.csv`
- `fact_size.csv`
- `fact_shape.csv`
- `fact_texture.csv`

### Rationale for exclusions
- Coverage is narrow relative to the 19,680 hourly training rows.
- Grain mismatch: spot-level datasets do not align naturally with beach-level hourly forecasts.
- Several joins would require text matching or aggressive aggregation, which increases leakage/noise risk before a baseline model exists.

## Phase 1 Conclusion
- `hour_forecast.csv` is a strong baseline training source with complete numeric marine/weather signals and no missing values.
- `day_forecast`, `tide`, and `beach` are the most defensible enrichment tables for later phases.
- Natural-key duplication around `day_forecast` is the main integrity issue to account for during EDA and feature engineering.
