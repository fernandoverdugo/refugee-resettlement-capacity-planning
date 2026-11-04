from fastapi.testclient import TestClient

from src.api.app import app


client = TestClient(app)


def test_web_app_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "Refugee Resettlement Capacity Planner" in response.text
    assert "How to use this planner" in response.text
    assert "Full-time equivalent" in response.text
    assert "Binding constraint" in response.text


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_defaults_endpoint_uses_validated_data():
    response = client.get("/v1/defaults")
    assert response.status_code == 200
    body = response.json()
    assert body["reference_monthly_demand"] >= 0
    assert body["reference_observation_date"]
    assert body["state_share_fiscal_year"] >= 2024


def test_forecast_benchmark_endpoint():
    response = client.get("/v1/forecast/benchmark")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) > 0
    assert {"model", "horizon", "mae", "rmse"}.issubset(results[0])


def test_scenario_capacity_and_optimization_endpoints():
    for path in ["/v1/scenarios", "/v1/capacity", "/v1/optimization"]:
        response = client.get(path)
        assert response.status_code == 200
        assert len(response.json()["results"]) == 3


def test_plan_endpoint_runs_parameterized_pipeline():
    response = client.post(
        "/v1/plan",
        json={
            "reference_monthly_demand": 100.0,
            "horizon_months": 1,
            "total_fte": 8.0,
            "monthly_budget": 60000.0,
        },
    )
    assert response.status_code == 200
    body = response.json()
    baseline = next(row for row in body["scenario_summary"] if row["scenario"] == "baseline")
    assert baseline["total_demand"] == 100.0
    assert baseline["service_coverage_rate"] == 1.0
    assert "budget_binding_months" in baseline
    assert "fte_binding_months" in baseline


def test_plan_endpoint_uses_data_default_when_reference_omitted():
    defaults = client.get("/v1/defaults").json()
    response = client.post("/v1/plan", json={"horizon_months": 1})
    assert response.status_code == 200
    body = response.json()
    baseline = next(row for row in body["scenario_summary"] if row["scenario"] == "baseline")
    assert body["assumptions"]["reference_monthly_demand"] == defaults["reference_monthly_demand"]
    assert baseline["total_demand"] == defaults["reference_monthly_demand"]


def test_plan_endpoint_returns_422_for_infeasible_coverage():
    response = client.post(
        "/v1/plan",
        json={
            "reference_monthly_demand": 100.0,
            "horizon_months": 1,
            "total_fte": 1.0,
            "monthly_caseload_per_fte": 25.0,
            "utilization_rate": 1.0,
            "monthly_budget": 100000.0,
            "minimum_coverage": 0.9,
        },
    )
    assert response.status_code == 422


def test_plan_endpoint_validates_request_bounds():
    response = client.post("/v1/plan", json={"horizon_months": 0})
    assert response.status_code == 422
