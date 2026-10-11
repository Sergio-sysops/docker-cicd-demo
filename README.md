# Docker + CI/CD demo

![CI/CD](https://github.com/Sergio-sysops/docker-cicd-demo/actions/workflows/ci-cd.yml/badge.svg)

A small Python API packaged the way I deliver client projects: an optimized Docker image, a full stack with Docker Compose, and a GitHub Actions pipeline that **tests, builds, publishes and deploys** on every push to `main`.

```
git push ──► tests (pytest + PostgreSQL) ──► build image ──► push to ghcr.io ──► SSH deploy to VPS ──► health check
```

## What is inside

| File | What it does |
|---|---|
| `Dockerfile` | Multi-stage build, slim base, **non-root user**, health check, Gunicorn |
| `docker-compose.yml` | App + PostgreSQL (persistent volume, health check) + Nginx reverse proxy |
| `docker-compose.prod.yml` | Production override: pulls the image built by CI instead of building on the server |
| `nginx/default.conf` | Reverse proxy with basic security headers |
| `.github/workflows/ci-cd.yml` | Test → build and push to GHCR → deploy over SSH → health check |
| `app/` | Flask notes API with a visit counter stored in PostgreSQL, plus tests |

## Run it locally

Requirements: Docker with the Compose plugin.

```bash
cp .env.example .env          # change POSTGRES_PASSWORD
docker compose up -d --build
curl http://localhost:8080/health
curl -X POST -H 'Content-Type: application/json' \
     -d '{"text":"hello"}' http://localhost:8080/api/notes
```

Open http://localhost:8080 to see the visit counter. Stop with `docker compose down` (add `-v` to delete the database).

### Run the tests

The tests need a PostgreSQL database. The easiest way is a throwaway container:

```bash
docker run -d --name test-db -p 5432:5432 -e POSTGRES_USER=app \
  -e POSTGRES_PASSWORD=app -e POSTGRES_DB=app postgres:17-alpine
cd app && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
DATABASE_URL=postgresql://app:app@localhost:5432/app .venv/bin/pytest -v
docker rm -f test-db
```

## Pipeline

1. **test**: starts a PostgreSQL service container and runs `pytest`.
2. **build**: builds the image with layer caching and pushes it to `ghcr.io/<owner>/docker-cicd-demo` with the tags `latest` and the commit SHA. Pull requests only build, they never push.
3. **deploy** (optional): connects to the server over SSH, pulls the new image, restarts the stack and checks `/health`. If the check fails, the job fails.

### Enabling deployment to your VPS

On the server (Docker installed): clone the repo, create `.env`, and create a deploy user with an SSH key that is only used by GitHub Actions.

In GitHub, go to **Settings → Secrets and variables → Actions** and add:

| Type | Name | Example |
|---|---|---|
| Secret | `DEPLOY_SSH_KEY` | private key of the deploy user |
| Variable | `DEPLOY_HOST` | `203.0.113.10` |
| Variable | `DEPLOY_USER` | `deploy` |
| Variable | `DEPLOY_PATH` | `/home/deploy/docker-cicd-demo` |
| Variable | `DEPLOY_HTTP_PORT` | `8080` (optional) |

If `DEPLOY_HOST` is not set, the deploy job is skipped and the rest of the pipeline still runs. In front of it, put Nginx or Caddy with a Let's Encrypt certificate for HTTPS.

## License

MIT
