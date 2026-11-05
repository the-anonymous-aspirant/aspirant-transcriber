# Changelog

## Unreleased

- Builds of main's image now run one at a time, and `:latest` and `:main` go
  only on a build of main's current head (`scripts/is-main-head.sh`, unit test
  `sh tests/is_main_head_unit.sh`). Two merges landing seconds apart, or a
  re-run of an older build, can no longer leave `:latest` on an older commit
  for auto-pull to deploy. Test runs are not queued. See system_3 #9984, from
  #9966 (the same guard as aspirant-client #409).

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
