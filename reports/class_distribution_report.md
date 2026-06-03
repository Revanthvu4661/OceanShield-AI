# RogueGuard Phase 4 Proxy Label Creation

## Scope
This phase creates a binary proxy target for potential rogue-wave risk.

Implementation:
- [src/labeling.py](D:/ocean/src/labeling.py)

Label definition:
- `0 = Normal`
- `1 = Potential Rogue Risk`

## Labeling Strategy
Because the dataset does not contain a direct rogue-wave event label, the target is defined as a proxy based on the joint behavior of the four strongest wave-risk drivers requested for this phase:
- `sigheight`
- `swellheight`
- `period`
- `windspeed`

The label is intentionally conservative. It is designed to identify hours where multiple high-sea-state stressors co-occur, rather than flagging every moderately elevated condition.

## Threshold Selection

### Chosen thresholds
- `sigheight >= 1.1`
- `swellheight >= 1.0`
- `period >= 12.0`
- `windspeed >= 27.0`

### Why these cutoffs were chosen
These values sit near the upper tail of the observed distribution:

| Variable | Approximate percentile | Interpretation |
| --- | ---: | --- |
| `sigheight = 1.1` | 90th | unusually high significant wave height |
| `swellheight = 1.0` | 90th | elevated swell loading |
| `period = 12.0` | 90th | longer-period swell events |
| `windspeed = 27.0` | 90th | strong wind forcing |

This makes the label data-driven and consistent with the actual dataset rather than relying on arbitrary external cutoffs.

## Final Proxy Rule

An hourly record is labeled `1` when either of the following is true:

1. `threshold_hit_count >= 3`
   - At least 3 of the 4 core marine variables exceed their upper-tail thresholds.

2. Reinforced dual-condition case:
   - at least 2 thresholds are exceeded
   - and at least one of the wave anchors is active:
     - `sigheight_flag = 1` or `swellheight_flag = 1`
   - and the weighted risk score is at least `1.0`

### Weighted risk score

`rogue_risk_score =`
- `0.35 * (sigheight / 1.1)`
- `+ 0.25 * (swellheight / 1.0)`
- `+ 0.20 * (period / 12.0)`
- `+ 0.20 * (windspeed / 27.0)`

This score gives the largest emphasis to significant wave height and swell height, while still preserving the importance of long swell period and strong wind forcing.

## Class Distribution

| Class | Count | Share |
| --- | ---: | ---: |
| `0 = Normal` | 18,595 | 94.49% |
| `1 = Potential Rogue Risk` | 1,085 | 5.51% |

## Threshold-Hit Breakdown

| Threshold hits | Rows | Positive rows | Interpretation |
| --- | ---: | ---: | --- |
| 0 | 13,964 | 0 | calm / ordinary conditions |
| 1 | 3,189 | 0 | isolated elevation, not enough for rogue-risk proxy |
| 2 | 1,554 | 112 | only the most severe dual-condition cases are promoted |
| 3 | 868 | 868 | automatically labeled high-risk proxy |
| 4 | 105 | 105 | strongest co-occurrence regime |

## Separation Between Classes

### Mean values by class

| Feature | Normal | Potential Rogue Risk |
| --- | ---: | ---: |
| `sigheight` | 0.713 | 1.194 |
| `swellheight` | 0.680 | 1.112 |
| `period` | 8.133 | 9.900 |
| `windspeed` | 16.606 | 31.445 |
| `windgust` | 30.002 | 46.323 |
| `wave_energy` | 4.570 | 14.178 |
| `marine_risk_index` | 5.555 | 12.225 |

### Weighted score quantiles by class

| Class | 25% | 50% | 75% | 90% |
| --- | ---: | ---: | ---: | ---: |
| `0 = Normal` | 0.555 | 0.641 | 0.744 | 0.866 |
| `1 = Potential Rogue Risk` | 1.002 | 1.045 | 1.102 | 1.168 |

This shows useful separation:
- most normal rows stay below the score threshold of `1.0`
- most positive rows sit at or above `1.0`

## Why This Proxy Is Reasonable
- It uses the four domain-relevant inputs requested for rogue-risk labeling.
- It focuses on co-occurrence of elevated wave and wind conditions instead of any single variable alone.
- It avoids over-labeling by requiring either three strong signals or a reinforced dual-condition pattern.
- It preserves a trainable minority class of about 5.5%, which is imbalanced but still practical for supervised learning.

## Limitations
- This is a proxy risk label, not a verified rogue-wave event record.
- The label is learned from forecast-condition severity, so it represents elevated potential rather than confirmed occurrence.
- Because beach-level forecasts are highly similar across locations, the label mainly reflects temporal marine-state intensity rather than local coastal nuance.

## Recommended Next Step
Proceed to Phase 5 and build the preprocessing pipeline:
- missing value handling
- scaling
- train-test split
- reusable transformation pipeline for the labeled feature set
