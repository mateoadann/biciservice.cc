# AGENTS.md

Guia para agentes automatizados trabajando en este repositorio. Mantener cambios pequenos, coherentes y en linea con el estilo actual.

## Resumen del proyecto
- Flask app con blueprints `auth` y `main`.
- Rutas de `main` estan separadas por modulo en `app/main/routes/`.
- UI en templates Jinja + CSS propio en `app/static/css/app.css`.
- Base de datos Postgres via SQLAlchemy + Flask-Migrate.
- Incluye auditoria (`AuditLog`), onboarding por CSV, 2FA y confirmacion por email.
- Idioma principal: espanol (sin acentos en textos nuevos, para mantener ASCII).

## Comandos utiles
- Migraciones: `flask --app wsgi.py db upgrade`
- Ejecutar app: `flask --app wsgi.py run`
- Docker: `docker compose up --build`
- Docker migraciones: `docker compose exec web flask --app wsgi.py db upgrade`
- Tests: `pytest`

## Variables de entorno
- `SECRET_KEY`: clave de sesion.
- `DATABASE_URL`: Postgres (psycopg).
- `UPLOAD_FOLDER`: ruta para uploads (default `app/static/uploads`).
- `SESSION_COOKIE_SECURE`, `REMEMBER_COOKIE_SECURE`: usar "true" en prod.

## Arquitectura y carpetas
- `app/__init__.py`: create_app, seguridad headers, filtros Jinja, tema.
- `app/models.py`: modelos y relaciones.
- `app/main/routes/`: CRUD y logica de negocio principal por modulo.
- `app/auth/routes.py`: login/register/confirmacion/reset/2FA.
- `app/main/forms.py`: formularios y validaciones (incluye LocalizedDecimalField).
- `app/main/helpers.py`: helpers de sesiones, uploads, choices, validaciones.
- `app/services/`: reglas de negocio y auditoria (client/job/inventory).
- `app/templates/`: vistas Jinja.
- `app/static/css/app.css`: estilos y dark mode.
- `app/static/templates/`: templates de importacion CSV/XLSX.
- `migrations/`: historial Alembic.

## Reglas de negocio actuales
- Estados de trabajo: `open`, `in_progress`, `ready`, `closed`.
- No se puede borrar una bicicleta si tiene trabajos `in_progress`.
- No se puede borrar un trabajo `in_progress`.
- No se puede borrar un cliente si tiene bicicletas asociadas.
- No se puede borrar un service si tiene trabajos asociados.
- El trabajo tiene `code` unico de 4 caracteres (A-Z y numeros).
- Precios se formatean con separador de miles y coma decimal via filtro `currency`.
- Marca de bicicleta se elige solo desde lista (sin texto libre); en import CSV, marcas fuera de lista pasan a "Otra".
- Usuarios: no se puede eliminar el propio usuario ni dejar el taller sin owners.

## UI y UX
- Mensajes y labels en espanol.
- Formularios de borrar usan `class="js-confirm"` y `data-confirm-*`.
- El modo oscuro se controla con `#themeToggle` y localStorage.
- El switch de modo oscuro esta en Personalizacion (`app/templates/main/settings.html`).
- Tablas tienen filtros/inputs con `data-search` y JS embebido en template.

## Seguridad y uploads
- CSRF activo; usar `form.hidden_tag()` en formularios.
- Uploads validados por extension y contenido (Pillow, SVG basico) en `app/main/helpers.py`.
- 2FA con `pyotp` y lockout/rate limit en login.
- Nunca usar `imghdr` (no existe en Python 3.13).

## Migrations
- Cada cambio de modelo requiere migracion nueva en `migrations/versions/`.
- Mantener `down_revision` correcto.
- Si se agregan campos no nulos, poblar valores antes de `nullable=False`.

## Contribuciones esperadas
- Mantener HTML simple y consistente con clases existentes.
- Evitar dependencias nuevas salvo necesidad clara.
- No tocar archivos binarios en `app/static/css/` salvo instruccion.
- Preferir cambios en `app/main/routes/`, `app/main/forms.py` y `app/services/` antes de agregar nuevas capas.

## Validacion rapida
- Verificar que los flashes se muestren en espanol.
- Revisar dark mode para contraste en `.status`, `.chip` y `.button-ghost`.
- Si se cambia el tema, revisar `:root` en `base.html`.
