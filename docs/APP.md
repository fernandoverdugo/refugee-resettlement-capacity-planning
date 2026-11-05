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

## Results

The interface displays scenario-level:

- total demand
- served demand
- unmet demand
- service coverage
- allocated FTE-months
- total staffing cost
- budget-binding months
- FTE-binding months

Coverage is displayed with both a percentage and a progress bar. Semantic color is used to make capacity pressure easier to scan:

- green: high coverage
- amber: approaching capacity
- orange: meaningful shortfall
- red: severe shortfall

Binding-constraint counts also receive visual emphasis when a constraint binds repeatedly.

## Interpretation

The interface does not recommend refugee placement. It explores hypothetical service-resource requirements after demand assumptions have been specified.

Default staffing and cost values are planning assumptions, not measured agency budgets. Color states are communication aids, not policy thresholds.
