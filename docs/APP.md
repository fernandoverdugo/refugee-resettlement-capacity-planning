# Interactive planning interface

## Purpose

The web interface provides a simple front end for the decision-support API. It is intentionally lightweight so the full application can run from the repository with one server process.

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

Each run sends those assumptions to `POST /v1/plan`.

## Results

The interface displays scenario-level:

- total demand
- served demand
- unmet demand
- service coverage
- allocated FTE-months
- total staffing cost

The current front end is deliberately focused on decision support rather than visual polish. It provides a working end-to-end product surface before deployment and more advanced visualization work.

## Interpretation

The interface does not recommend refugee placement. It explores hypothetical service-resource requirements after demand assumptions have been specified.

Default staffing and cost values are planning assumptions, not measured agency budgets.
