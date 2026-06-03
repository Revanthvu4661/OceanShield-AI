# RogueGuard Phase 3 Feature Engineering Report

## Scope
This phase converts the baseline marine forecast dataset into a reusable feature frame for rogue-wave risk modeling.

Primary implementation:
- [src/features.py](D:/ocean/src/features.py)

## What the Feature Pipeline Does

### 1. Loads only the approved baseline datasets
- `hour_forecast.csv`
- `day_forecast.csv`
- `beach.csv`
- `tide.csv`

### 2. Applies safe joins
- `hour_forecast.iddayforecast -> day_forecast.iddayforecast`
- `day_forecast.idbeach -> beach.idbeach`
- tide aggregated to `iddayforecast` before merge

### 3. Normalizes raw field names
- `preciptation -> precipitation`
- `cloundover -> cloudcover`
- `name -> beach_name`

### 4. Applies one quality correction
- `watertemp < 0` is converted to null to mark physically suspicious values for preprocessing in Phase 5

## Engineered Feature Set

### Time and cycle features
- `hour_sin`
  - Cyclical encoding of hour-of-day.
- `hour_cos`
  - Companion cyclical encoding for daily periodicity.
- `daylight_flag`
  - Simple daylight proxy for daytime surf conditions.

### Thermal and moisture context
- `daily_temp_range`
  - Captures day-level atmospheric spread.
- `temperature_vs_daily_max`
  - Measures how far the current hour sits below the daily high.
- `temperature_vs_daily_min`
  - Measures how far the current hour sits above the daily low.
- `dewpoint_depression`
  - Indicates moisture saturation gap and foggy/humid conditions.
- `precipitation_log`
  - Stabilizes the highly skewed precipitation tail.
- `cloud_humidity_interaction`
  - Combines cloud cover and humidity into a storminess/moisture signal.

### Directional and vectorized marine features
- `wind_vector_x`
  - East-west wind component.
- `wind_vector_y`
  - North-south wind component.
- `swell_vector_x`
  - East-west swell component.
- `swell_vector_y`
  - North-south swell component.
- `directional_misalignment`
  - Normalized angular gap between wind and swell directions.
- `wind_alignment`
  - Cosine-based directional agreement score.

### Wind forcing features
- `gust_factor`
  - Relative gust amplification: `windgust / windspeed`.
- `gust_delta`
  - Absolute gust excess above sustained wind.
- `wind_intensity`
  - Weighted blend of sustained wind and gusts.

### Wave and swell intelligence features
- `wave_energy`
  - `sigheight^2 * period`; stronger long-period wave systems score higher.
- `wave_steepness`
  - `sigheight / period`; proxy for sharper, steeper wave behavior.
- `wave_power_index`
  - `sigheight * swellheight * period`; combined bulk-wave forcing term.
- `swell_ratio`
  - `swellheight / sigheight`; indicates how much of the sea state is swell-driven.
- `swell_energy`
  - `swellheight^2 * period`; long-period swell loading.
- `wave_severity`
  - Weighted raw-risk composite from wave height, swell height, period, and gusts.
- `wave_wind_interaction`
  - Interaction between sea height and wind forcing.
- `marine_risk_index`
  - High-level marine intensity composite blending wave energy, wave power, wind forcing, directional mismatch, tide range, and pressure anomaly.

### Pressure, lunar, and tide context
- `pressure_anomaly`
  - Hourly pressure relative to the same `iddayforecast` mean.
- `pressure_drop_flag`
  - Binary indicator for notable low-pressure deviation.
- `lunar_energy_proxy`
  - Scaled moon illumination signal retained as a weak contextual feature.
- `tide_height_normalized`
  - Tide mean normalized against daily tide range.
- `tide_extreme_imbalance`
  - Difference between high-tide and low-tide counts.

## Weak or Redundant Inputs Removed by Default

### Surrogate identifiers
- `idhourforecast`
- `iddayforecast`

These identify rows but should not drive model behavior.

### Raw date/time strings that are better represented through engineered features
- `date`
- `sunrise`
- `sunset`
- `moonrise`
- `moonset`

### Constant or near-constant geographic text fields
- `city`
- `state`
- `country`

These are effectively constant in this dataset and add no predictive value.

### Weak beach-specific metadata for the baseline model
- `beach_name`
- `latitude`
- `longitude`

Phase 2 showed that 98.23% of `(date, time)` slices are identical across beaches, so these columns are unlikely to add much value in the baseline model and may encourage memorization rather than generalizable risk logic.

### Redundant temperature-family columns
- `temperature`
- `windchill`
- `heatIndex`
- `feelslike`

These were kept indirectly through more meaningful derived representations such as:
- `daily_temp_range`
- `temperature_vs_daily_max`
- `temperature_vs_daily_min`
- `dewpoint_depression`

The raw columns were strongly collinear in EDA and would add noise/redundancy to a baseline model.

## Feature Engineering Output Summary
- Final row count after engineering: 19,680
- Final column count after engineering and default drops: 58
- New engineered features added: 31
- Remaining flagged nulls: `watertemp` has 168 nulls after anomaly handling

## Key Findings
- The most important engineered feature family is wave and swell intensity:
  - `wave_energy`
  - `wave_power_index`
  - `swell_energy`
  - `wave_severity`
  - `marine_risk_index`
- Wind direction and gust structure are now represented more usefully through:
  - vector components
  - alignment features
  - gust amplification
- Pressure and tide remain secondary contextual signals, but they are now expressed in a model-friendly form.
- The feature layer explicitly avoids relying on sparse spot-level tables and low-value geographic text fields.

## Recommended Next Step
Proceed to Phase 4 and create the proxy binary label:
- `0 = Normal`
- `1 = Potential Rogue Risk`

The strongest base variables for label design remain:
- `sigheight`
- `swellheight`
- `period`
- `windspeed`
