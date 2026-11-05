# Interactive planning interface

## Purpose

The web interface provides a lightweight front end for the decision-support API. It is designed for scenario exploration: users can change demand, staffing, budget, and coverage assumptions, see immediate capacity feedback, then run the full constrained optimization.

## Run locally

```bash
python -m pip install -r requirements.txt
uvicorn src.api.app:app --reload
```

Then open the root application page in a browser.

The API documentation remains available at `/docs`.

## Starting points and presets

The interface loads validated defaults from `GET /v1/defaults`.

Users can then choose one of three quick starting points:

- **Baseline** — restores the validated/default planning assumptions.
- **Demand surge** — increases the higher-demand multiplier to 2.0× while retaining the standard staffing and budget assumptions.
- **Budget constrained** — keeps the standard demand structure but lowers the monthly staffing budget to create a visibly constrained planning case.

A **Reset defaults** control restores the data-backed defaults at any time.

Presets are convenience scenarios, not forecasts or policy recommendations.

## Adjustable assumptions

The interface lets users change:

- reference monthly demand
- planning horizon
- lower and higher scenario multipliers
- total FTE
- monthly caseload per FTE
- utilization rate
- monthly cost per FTE
- monthly budget
- state staffing-ceiling multiplier
- minimum service coverage

Exploratory assumptions use synchronized sliders and exact numeric inputs. Dragging a slider updates the numeric field, while typed values update the slider range and display.

Each full run sends the current assumptions to `POST /v1/plan`.

## Live capacity feedback

Before the optimization is run, the interface calculates:

```text
theoretical monthly capacity
= total FTE × monthly cases per FTE × utilization
```

It also estimates the staffing level supported by the entered monthly budget and displays a plain-language capacity-pressure state:

- Balanced
- Approaching capacity
- Capacity constrained
- Severely constrained

This preview is descriptive only. The optimizer still determines the actual state allocation and resulting coverage.

## Executive scenario summary

After optimization, the interface generates a concise planning takeaway for the higher-demand scenario.

The summary reports whether modeled capacity covers demand and, when capacity is insufficient, highlights:

- total unmet demand
- overall service coverage
- months in which the staffing budget is binding
- months in which the FTE limit is binding

This is intended to help nontechnical users identify the planning constraint before reviewing the detailed table.

## Scenario comparison

The lower, baseline, and higher scenarios are displayed in two complementary ways:

- a compact demand-versus-served visual bar for quick comparison
- a detailed scenario table containing total demand, served demand, unmet demand, coverage, FTE-months, cost, and binding-constraint counts

Coverage is also shown with a percentage and semantic color:

- green: high coverage
- amber: approaching capacity
- orange: meaningful shortfall
- red: severe shortfall

The colors are communication aids rather than policy thresholds.

## State-pressure view

`POST /v1/plan` returns an aggregated `state_summary` generated from the same constrained optimization results used for the scenario totals.

The interface shows the highest-pressure states in the higher-demand scenario, ranked by modeled unmet demand.

The state view reports aggregated planning results based on the latest validated state arrival shares. It is **not** a state-level arrival forecast and should not be interpreted as a placement recommendation.

## CSV exports

After a scenario has been run, users can download three CSV files directly from the browser:

- **Assumptions CSV** — the exact planning assumptions plus reference dates and state-share year
- **Scenario CSV** — the lower, baseline, and higher scenario summaries
- **State results CSV** — the full aggregated state planning output for all scenarios

Exports are generated from the same API response currently displayed in the browser. No separate calculation or server-side state is used.

## Interpretation

The interface does not recommend refugee placement. It explores hypothetical service-resource requirements after demand assumptions have been specified.

Default staffing and cost values are planning assumptions, not measured agency budgets. Forecasts, scenarios, color states, and optimization outputs should be treated as decision-support inputs rather than deterministic predictions or policy recommendations.
