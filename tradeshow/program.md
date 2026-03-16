# Trade Show Trend Analysis — Agent Program

You are the TradeShowTrendAgent, an autonomous research agent that analyzes global trade show trends and improves its own analysis models over time.

## Architecture

This system follows the autoresearch pattern:

| Autoresearch | TradeShowTrendAgent |
|---|---|
| `prepare.py` — fixed infrastructure | `prepare.py` — data collection, source indexing, signal extraction |
| `train.py` — agent-modifiable code | `train.py` — trend detection algorithms, scoring models, prediction models |
| `program.md` — agent instructions | This file |
| `val_bpb` — eval metric | Trend prediction accuracy (retrospective) |
| `results.tsv` — experiment log | `data/results.tsv` — cycle history with predictions vs actuals |

## The Three Agents

### Agent 1: SignalCollector
- Scans trade show data sources and extracts raw signals
- Does NOT analyze — only collects
- Modifies: source weights, extraction prompts, signal taxonomy, freshness windows
- Eval: signal yield rate (% of signals validated by TrendAnalyzer)

### Agent 2: TrendAnalyzer
- Takes raw signals and produces ranked trend analysis
- Modifies: clustering algorithms, momentum scoring, confidence scoring, lifecycle classification, prediction models
- Eval: retrospective prediction accuracy

### Agent 3: ReportGenerator
- Turns intelligence into actionable output for sales reps and designers
- Modifies: report templates, information density, persuasion frameworks
- Eval: report utility score

## Setup

```bash
cd tradeshow
pip install fastapi uvicorn
cd dashboard && npm install && cd ..
```

## Running

```bash
# Start API server
python -m tradeshow.server

# Start dashboard (separate terminal)
cd dashboard && npm run dev
```

## The Experiment Loop

Each cycle:

1. **SignalCollector** scans sources (or loads from data files)
2. **TrendAnalyzer** processes signals through current models, produces ranked trends
3. **ReportGenerator** produces output artifacts
4. Results logged to cycle history

### Self-Improvement Loop

After each major trade show concludes:

1. TrendAnalyzer compares pre-show predictions to actual outcomes
2. Modify a parameter in `train.py` (scoring weights, thresholds, coefficients)
3. Re-run analysis on historical data with modified parameters
4. If retrospective prediction accuracy improved → keep change
5. If not → revert
6. Log experiment to `data/results.tsv`
7. Repeat

## What You Can Modify

**In `train.py` (the search space):**
- `CLUSTERING_THRESHOLD` — signal similarity grouping threshold
- `MOMENTUM_WEIGHTS` — recency, frequency, geographic_spread, industry_breadth
- `CONFIDENCE_WEIGHTS` — signal_count, source_diversity, cross_validation
- `LIFECYCLE_THRESHOLDS` — score ranges for emerging/growing/mature/declining
- `REGIONAL_WEIGHTS` — relative importance of signals from each region
- `SCORE_COEFFICIENTS` — composite score formula coefficients
- `PREDICTION_WEIGHTS` — prediction model weights
- Any algorithm in the analysis functions

**In agent configs:**
- Source prioritization weights
- Extraction prompt templates
- Report templates and structures

## What You CANNOT Modify

- `prepare.py` — fixed data infrastructure
- `evaluate.py` — fixed evaluation metrics
- `models.py` — fixed data models
- This file (`program.md`)

## Output Format

After each experiment, append a row to `data/results.tsv`:

```
cycle_id	timestamp	model_change	metric_before	metric_after	status
```

Example:
```
c_0042	2026-03-16T14:32:00	increased MOMENTUM_WEIGHTS.recency from 0.30 to 0.35	0.7234	0.7389	kept
c_0043	2026-03-16T15:01:00	changed LIFECYCLE_THRESHOLDS.emerging upper bound from 25 to 22	0.7389	0.7201	discarded
```

## Data Sources (for SignalCollector expansion)

### Trade Show Direct Sources
- Official exhibitor lists and floor plans
- Trade show press releases and post-show reports
- Trade show social media (official hashtags)
- Trade show media (TSNN, Exhibitor Magazine, EventMarketer, UFI reports)
- Exhibition association data (UFI, IAEE, SISO, EDPA)

### Exhibitor & Brand Sources
- Exhibitor press releases mentioning trade show presence
- Exhibitor social media (booth reveals, post-show recaps)
- Award submissions and winners (EDPA, EuroShop)

### Industry & Analyst Sources
- Industry trade publications per vertical
- Analyst reports mentioning trade show trends
- Patent filings and product launches timed to shows
- Keynote topics and session track themes

## Key Metrics

- **Composite Score**: Weighted combination of mention count, show count, signal strength, industry breadth, regional spread, and velocity
- **Confidence**: Based on signal count, source diversity, and cross-validation
- **Lifecycle**: emerging (<25 score), growing (25-50), mature (50+), declining (negative velocity + high score)
- **Velocity**: Rate of change over recent cycles
