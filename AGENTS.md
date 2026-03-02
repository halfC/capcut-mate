# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

CapCut Mate is a CapCut/JianYing (剪映) draft automation API built with FastAPI. It has two components:

| Component | Location | Stack | Dev Port |
|-----------|----------|-------|----------|
| Backend API | `/workspace` (root) | Python 3.11+ / FastAPI / uv | 30000 |
| Desktop Client Web UI | `/workspace/desktop-client/web` | React 19 / Vite 7 | 9000 |

No database is required. Drafts are stored as local files under `output/draft/`.

### Running services

- **Backend API**: `uv run main.py` (serves on port 30000, Swagger UI at `/docs`)
- **Web UI dev server**: `cd desktop-client/web && npx vite --port 9000 --host 0.0.0.0`
  - Note: `npm run web:dev` from `desktop-client/` starts Vite on port 5173 by default despite the config specifying 9000; pass `--port 9000` explicitly if needed.
- The Electron desktop client (`npm start` in `desktop-client/`) requires a display and cannot run in headless cloud environments.

### Testing

- Tests use pytest: `uv run python -m pytest tests/ --ignore=tests/test_draft_service.py --ignore=tests/test_middleware.py -q`
- Two test files (`test_draft_service.py`, `test_middleware.py`) have pre-existing import errors and must be skipped.
- Some tests (`test_api_version.py`, `test_font_size_not_set.py`, `test_video_duration_extension.py`) have pre-existing failures due to API signature changes or missing test fixtures.

### Building

- **Web UI build**: `cd desktop-client/web && npx vite build` (outputs to `desktop-client/ui/`)
- There is no separate Python build step; the API runs directly from source.

### API quick test (hello world)

```bash
# Create a draft
curl -X POST http://localhost:30000/openapi/capcut-mate/v1/create_draft \
  -H "Content-Type: application/json" \
  -d '{"width": 1080, "height": 1920}'
```

### Gotchas

- `uv` must be on PATH (`$HOME/.local/bin`). It is installed via `curl -LsSf https://astral.sh/uv/install.sh | sh`.
- The project uses Python 3.12 in the cloud environment (requires >=3.11).
- `pymediainfo` depends on `libmediainfo` system library for full functionality, but the API starts fine without it (only `get_audio_duration` may fail).
- API key auth is enabled by default (`ENABLE_APIKEY=true` env var) but the Swagger UI works without it for local testing.
