from fastapi.testclient import TestClient

from src.api.app import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"


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
    assert len(body["scenario_summary"]) == 3

    baseline = next(
        row for row in body["scenario_summary"]
        if row["scenario"] == "baseline"
    )
    assert baseline["total_demand"] == 100.0
    assert baseline["service_coverage_rate"] == 1.0


def test_plan_endpoint_validates_request_bounds():
    response = client.post(
        "/v1/plan",
        json={"horizon_months": 0},
    )

    assert response.status_code == 422
