# AGENTS.md
Guide for coding agents working in `service_bicycle_crm`.
Use this as the repo-specific operating manual.

## Project Snapshot
- Backend: Flask + SQLAlchemy + Flask-Migrate + Flask-WTF + Flask-Login.
- DB: PostgreSQL in runtime, SQLite in tests.
- Tests: `pytest` with fixtures in `tests/conftest.py`.
- Frontend: Jinja templates, custom CSS, light JS.
- Tenant model: `Workshop` (tenant) + `Store` (sub-scope).
- UI language: Spanish.
- New UI text policy: Spanish without accents (ASCII-friendly).
- Public landing: `landing/` (static).
- Reverse proxy/static server: `nginx/`.
- Demo videos: `remotion/` renders MP4 into `landing/videos/`.

## Rule Files Check (Cursor/Copilot)
- `.cursor/rules/`: not present.
- `.cursorrules`: not present.
- `.github/copilot-instructions.md`: not present.
- If added later, treat them as mandatory additive rules.

## Key Paths
- `app/__init__.py`: app factory, ProxyFix, security headers, context processors.
- `app/models.py`: SQLAlchemy models and relationships.
- `app/auth/`: auth and 2FA flows.
- `app/main/routes/`: domain routes split by module.
- `app/main/forms.py`: WTForms and decimal parsing behavior.
- `app/main/helpers.py`: tenant guards, uploads, pagination helpers.
- `app/services/`: business logic and audit logic.
- `app/templates/` and `app/static/css/app.css`: UI templates and styling.
- `migrations/versions/`: Alembic revisions.
- `tests/`: pytest suite.
- `landing/`, `nginx/`, `remotion/`: marketing and infra extras.

## Build / Run / Test Commands
### Local setup
- Create venv: `make venv`
- Install deps: `make install`
- Create env file if missing: `make env`
- Run app locally: `make run`
### Docker runtime
- Build images: `make build`
- Start detached: `make up`
- Start with rebuild: `make up-build`
- Start full stack foreground: `make up-full`
- Stop stack: `make down`
- Restart stack: `make restart`
- Container status: `make docker-ps`
- Logs: `make logs SERVICE=web TAIL=200`
### Database / migrations
- Local upgrade: `make db-upgrade`
- Local create migration: `make db-migrate MSG="descripcion"`
- Local downgrade: `make db-downgrade REV=-1`
- Docker upgrade: `make docker-db-upgrade`
- Docker create migration: `make docker-db-migrate MSG="descripcion"`
- Docker downgrade: `make docker-db-downgrade REV=-1`
### Tests (full)
- Local: `make test-local`
- Docker: `make test`
- Docker alias: `make docker-test`
### Tests (single test, important)
- Single file: `pytest tests/test_auth.py -v`
- Single test: `pytest tests/test_auth.py::test_login_page_loads -v`
- Pattern filter: `pytest -k login -v`
- Stop early: `pytest -x -v`
- Single test in Docker: `docker compose exec web pytest tests/test_auth.py::test_login_page_loads -v`
### Lint / static checks
- No formal linter config is currently enforced.
- Pre-push minimum check: `python3 -m compileall app`
- Install repo pre-push hook: `make hooks-install`
### Landing / Nginx / Remotion
- Preview landing: `make landing-dev` (serves `landing/` on `:8080`).
- Validate nginx config: `make nginx-test`
- Reload nginx config: `make nginx-reload`
- Build demo videos: `cd remotion && npm install && npm run build`

## Code Style Guidelines
### General
- Prefer small, focused changes.
- Preserve architecture unless refactor is clearly needed.
- Prefer extending existing helpers/services before creating new layers.
- Avoid adding dependencies without strong justification.
### Imports
- Order imports: standard library, third-party, local app imports.
- Keep import groups separated by one blank line.
- Use explicit imports; avoid wildcard imports.
### Formatting
- Follow PEP 8 with 4-space indentation.
- Keep route/form/service functions readable and straightforward.
- Favor early returns for guards and error branches.
- Avoid unrelated reformatting in touched files.
### Types and numbers
- Add type hints in new/edited backend logic when practical.
- Prefer `X | None` syntax for optional types in new code.
- Use `Decimal` for money values; avoid float for prices.
- Keep decimal parsing behavior consistent with existing helpers/forms.
### Naming
- `snake_case` for variables/functions/modules.
- `PascalCase` for classes/forms/services.
- Keep route handler names explicit (`jobs_create`, `users_edit`, etc.).
- Keep naming consistent with existing domain terms.
### Flask route patterns
- Use `@login_required` on protected routes.
- Resolve workshop/store access early via helper guards.
- Return redirects immediately after failed guard checks.
- Keep heavy business logic in `app/services/`.
### Forms and validation
- Put validation in WTForms validators when possible.
- Keep user-facing validation/flash messages in Spanish.
- Ensure forms include CSRF via `form.hidden_tag()`.
### Database usage
- Scope tenant data by `workshop_id` and `store_id` where relevant.
- Keep transaction boundaries clear; commit once per logical operation.
- Reuse existing relationship/query patterns.
- Write audit logs on create/update/delete flows where expected.
### Error handling
- Validate inputs early and return explicit feedback.
- Do not expose internal exceptions to end users.
- Use consistent flash categories: `error`, `success`.
- Keep redirects deterministic after errors.
### Security
- Keep rate limit, lockout, and 2FA protections intact.
- Do not weaken CSRF protection.
- Reuse upload validation helpers (Pillow/SVG checks).
- Do not use deprecated `imghdr`.
### Templates / frontend
- Keep Jinja logic minimal; compute in Python where practical.
- Preserve existing CSS class patterns and layout structure.
- Keep confirm-delete forms using `js-confirm` and `data-confirm-*`.
- Respect existing theme and dark-mode behavior.

## Testing Conventions
- Reuse fixtures from `tests/conftest.py`.
- Keep tests isolated and behavior-focused.
- Assert status codes and key response behavior/content.
- Prefer descriptive `test_*` names.
- Use `login` fixture for auth flows when suitable.

## Migration Rules
- Every model change must include an Alembic migration.
- Keep `down_revision` accurate.
- For NOT NULL additions, backfill before enforcing non-null.
- Run relevant tests after migration updates.

## Final Checklist for Agents
- Run focused tests for changed functionality.
- Run broader suite when feasible (`make test-local` or Docker equivalent).
- Run `python3 -m compileall app` for syntax sanity.
- Validate nginx/landing/remotion changes with matching commands.
- Keep new UI text Spanish and ASCII-friendly by default.
- Summarize what changed, what was verified, and follow-up items.
