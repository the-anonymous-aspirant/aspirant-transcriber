# Changelog

## 1.0.0 (2026-03-10)

Extracted from [aspirant-online](https://github.com/the-anonymous-aspirant/aspirant-online) monorepo as a standalone service.

### What was extracted
- `transcriber/app/` -- FastAPI application (routes, models, schemas, tasks, transcription)
- `transcriber/tests/` -- pytest test suite
- `transcriber/requirements.txt` -- Python dependencies
- `Dockerfile-Transcriber` -- adapted as root `Dockerfile`

### What was added
- Standalone `Dockerfile` (paths updated for repo root)
- `.gitignore`
- `CLAUDE.md` (service documentation for AI-assisted development)
- `README.md`
- `docs/` directory with spec, architecture, operations, and decisions
- `.github/workflows/ci.yml` (CI pipeline with test and build-and-push jobs)
