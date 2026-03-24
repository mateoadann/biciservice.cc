# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proyecto

SaaS CRM para talleres de bicicletas. Flask + PostgreSQL + Jinja2 templates. Idioma principal: espanol (sin acentos en textos nuevos, mantener ASCII).

## Comandos

```bash
# Desarrollo local
make run                          # Flask dev server (puerto 5000)
make test-local                   # pytest local
make db-upgrade                   # Ejecutar migraciones
make db-migrate MSG="descripcion" # Crear nueva migracion
make db-downgrade                 # Revertir ultima migracion

# Docker dev (flujo principal)
make up-build                     # Build + levantar (puerto 5001)
make docker-db-upgrade            # Migraciones en contenedor
make test                         # Tests dentro de Docker
make down                         # Bajar servicios
make shell                        # Shell en contenedor web
make db-shell                     # psql en contenedor db
make logs SERVICE=web             # Ver logs (TAIL=200 por defecto)

# Docker produccion
make prod-up                      # Build + levantar prod (NPM + landing + web + db)
make prod-down                    # Bajar produccion
make prod-logs                    # Logs prod (usar SERVICE=web)
make prod-db-upgrade              # Migraciones en prod
make prod-shell                   # Shell en contenedor web prod

# Landing
make landing-dev                  # Preview landing en localhost:8080

# Email
make email-test                   # Correo de prueba local
make docker-email-test            # Correo de prueba en Docker dev
make prod-email-test              # Correo de prueba en prod

# Hooks
make hooks-install                # Instalar pre-push hook versionado

# Test individual
pytest tests/test_auth.py -v
pytest tests/test_auth.py::test_nombre -v
```

## Arquitectura

### App factory y entry point
- `wsgi.py` → `create_app()` en `app/__init__.py`
- `app/__init__.py`: registra blueprints, security headers (CSP, HSTS, X-Frame), filtros Jinja, context processors para tema y stores

### Blueprints
- `auth` (`app/auth/`): login, register, 2FA, reset password, confirmacion email
- `main` (`app/main/`): toda la logica de negocio

### Rutas modularizadas
Cada modulo en `app/main/routes/`: `dashboard.py`, `clients.py`, `bicycles.py`, `jobs.py`, `inventory.py`, `stores.py`, `users.py`, `settings.py`, `admin.py`, `onboarding.py`

### Capa de servicios
`app/services/`: `audit_service.py`, `client_service.py`, `job_service.py`, `inventory_service.py`, `pdf_service.py` (ReportLab). Encapsulan reglas de negocio y auditoria. Preferir cambios aqui antes de agregar capas nuevas.

### Formularios
`app/main/forms.py`: WTForms con `LocalizedDecimalField` para formato europeo (coma decimal). CSRF activo; usar `form.hidden_tag()` siempre.

### Helpers
`app/main/helpers.py`: uploads (validacion con Pillow, SVG basico), autorizacion por rol (`owner_or_redirect`, `super_admin_or_redirect`, `get_workshop_or_redirect`), paginacion, choices para selects.

### Multi-tenancy
- `Workshop` es la unidad de tenant; todo se filtra por `workshop_id`
- `Store` es sub-scope dentro del workshop
- `before_request` hook en `app/__init__.py` setea `g.active_workshop` y `g.active_store`
- Context processor `inject_theme()` provee colores, logo y stores a todos los templates

### Modelos clave (`app/models.py`)
User (roles: `owner`, `staff`, `super_admin`, campo `is_approved`) → Workshop (M2M via `user_workshops`) → Store, Client → Bicycle → Job → JobItem + JobPart. AuditLog registra cada operacion CRUD.

### Docker dev/prod
- Dev: `docker-compose.yml` + `Dockerfile` (Flask dev server, puerto 5001, hot reload via volumen `./app`)
- Prod: `docker-compose.prod.yml` + `Dockerfile.prod` (Gunicorn, 4 workers)
- Prod usa Nginx Proxy Manager (NPM) como reverse proxy — config via panel web en :81
- `landing/` servida por nginx:alpine en prod; `make landing-dev` en dev
- `remotion/` genera videos MP4 localmente (React → MP4, se commitean en `landing/videos/`)

## Reglas de negocio

- Estados de Job: `open` → `in_progress` → `ready` → `closed`
- No borrar bicicleta con jobs `in_progress`, ni job `in_progress`, ni cliente con bicicletas, ni service con jobs asociados
- No eliminar usuario propio ni dejar workshop sin owners
- Job code: 4 caracteres unicos (A-Z, 0-9)
- Precios: filtro `currency` con separador de miles y coma decimal
- Marcas de bicicleta: solo desde lista predefinida; en CSV import, marcas fuera → "Otra"
- Registro: usuario queda con `is_approved=False` hasta que super_admin apruebe desde panel admin
- Login bloqueado si `is_approved=False` (muestra mensaje informativo)
- Super admin puede aprobar, rechazar (soft-delete: `is_active=False`) o eliminar usuarios pendientes

## Seguridad

- Rate limit en login: 5 intentos / 300s por IP:email, lockout 15min tras 5 fallos
- 2FA con `pyotp` (TOTP)
- Uploads validados por extension y contenido (Pillow para imagenes, validacion basica SVG)
- No usar `imghdr` (eliminado en Python 3.13)
- Password: min 8 chars, requiere mayuscula + minuscula + digito

## Migraciones

- Cada cambio de modelo requiere nueva migracion en `migrations/versions/`
- Si se agregan campos NOT NULL, poblar valores default antes de `nullable=False`
- Mantener `down_revision` correcto

## Frontend

- Templates Jinja2 en `app/templates/`, CSS propio en `app/static/css/app.css`
- Dark mode: toggle `#themeToggle` con localStorage, switch en Settings
- Borrar: forms con `class="js-confirm"` y atributos `data-confirm-*`
- Tablas: filtros client-side con `data-search` y JS embebido; tablas responsive con `table-mobile-cards` + `data-label` por `td`
- Tema personalizable por workshop (colores en `:root` via `base.html`)
- Formularios: usar `form-grid`/`form-actions` y `field-error` por campo
- Botones: clases `button`, `button-ghost`, `button-danger`
- Mobile-first: base 360-430px (sin media query), tablet >=641px, desktop >=981px

### PWA
- Manifest: `/manifest.webmanifest`, service worker: `/sw.js`, registro: `app/static/js/pwa-register.js`
- En desarrollo (`FLASK_DEBUG=1`) el service worker se desactiva automaticamente
- En produccion usar `ASSET_VERSION` unico por release (no usar `dev`)
- Cache solo de assets estaticos; rutas auth/privadas no se cachean

## Variables de entorno

- Un solo `.env` para dev y prod (en `.gitignore`, cada entorno tiene su copia)
- Ambos compose files usan `env_file: .env`; `.env.example` es el template documentado
- `SECRET_KEY`, `DATABASE_URL` (postgresql+psycopg://...), `UPLOAD_FOLDER`
- `SESSION_COOKIE_SECURE`, `REMEMBER_COOKIE_SECURE`: "true" en produccion
- `APP_BASE_URL`: URL publica de la app
- `MAIL_FROM`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_TLS`/`SMTP_USE_SSL`: config SMTP para emails
- `ADMIN_NOTIFICATION_EMAIL`: email para avisos de nuevos registros pendientes
- `ASSET_VERSION`: version para cache-busting de assets en produccion

## Testing

- pytest con SQLite in-memory (fixtures en `tests/conftest.py`)
- CSRF deshabilitado en modo test
- `pytest.ini`: solo define `pythonpath = .`
- Pre-push hook ejecuta tests automaticamente (instalar con `make hooks-install`)
- GitHub Actions: workflow de tests en cada push y PR (`.github/workflows/tests.yml`)
