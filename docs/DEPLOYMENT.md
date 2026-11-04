# Deployment

## Production architecture

The application is packaged as a single Docker web service:

```text
Browser
   ↓
FastAPI + static planning interface
   ↓
Scenario and optimization modules
   ↓
Committed validated analytical outputs
```

The deployment image does not run ingestion, OCR, model training, or data refresh jobs. Those remain separate reproducible repository workflows.

## Production dependencies

`requirements-app.txt` contains only packages needed by the running application:

- NumPy
- pandas
- SciPy
- FastAPI
- Uvicorn

The full `requirements.txt` remains the development and analytical environment.

## Build locally

```bash
docker build -t refugee-capacity-planner .
```

Run:

```bash
docker run --rm -p 10000:10000 refugee-capacity-planner
```

Open:

```text
http://localhost:10000/
```

Health endpoint:

```text
http://localhost:10000/health
```

Interactive API documentation:

```text
http://localhost:10000/docs
```

## Health check

The Docker image includes a container health check that calls `/health` every 30 seconds.

The deployment blueprint also configures `/health` as the platform health-check path.

## Render blueprint

The repository includes `render.yaml` for a Docker-based Render web service.

The service:

- builds directly from the repository Dockerfile;
- listens on the platform-provided `PORT`;
- automatically deploys from commits;
- uses `/health` for health checks.

No Census API key is required for the deployed planner because the live service reads committed validated analytical outputs. Census refresh workflows remain separate from the application runtime.

## Continuous integration

`.github/workflows/docker-build.yml` builds the production image whenever deployment-relevant files change.

This catches missing files, dependency problems, and Docker build regressions before deployment.

## Deployment boundary

The deployed application is a decision-support demonstration. It does not refresh public datasets at request time and does not make individual refugee-placement decisions.

Productionizing the application for operational use would require authenticated data refreshes, persistent storage, monitoring, access control, and organization-specific staffing and cost data.
