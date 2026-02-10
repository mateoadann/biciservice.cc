# Service Bicycle CRM

Plataforma SaaS para gestionar el service de bicicletas en talleres. Permite
personalizar logo, nombre del taller, favicon y paleta de colores.

## Funcionalidades (primera iteracion)
- Auth: register, login, logout
- Branding del taller (logo, favicon, colores)
- Modelos base: talleres, clientes, bicicletas, services, trabajos
- Dashboard estilo ERP, responsive para mobile

## Stack
- Python + Flask
- PostgreSQL
- SQLAlchemy + Flask-Migrate
- Flask-Login + Flask-WTF

## Requisitos
- Python 3.11+ (recomendado)
- PostgreSQL en local

## Configuracion local
1. Crear y activar virtualenv:
   `python3 -m venv .venv`
   `source .venv/bin/activate`
2. Instalar dependencias:
   `pip install -r requirements.txt`
3. Copiar variables de entorno:
   `cp .env.example .env`
4. Crear la base de datos:
   `createdb service_bicycle_crm`
5. Ejecutar migraciones:
   `flask --app wsgi.py db upgrade`
6. Levantar la app:
   `flask --app wsgi.py run`

## Configuracion con Docker
1. Levantar servicios:
   `docker compose up --build`
2. Ejecutar migraciones:
   `docker compose exec web flask --app wsgi.py db upgrade`
3. Abrir la app en el navegador:
   `http://localhost:5000`

## Tests y automatizacion
- Tests locales: `make test-local`
- Tests en Docker: `make test`

### Hook pre-push
El repositorio incluye un hook `pre-push` versionado para ejecutar validaciones antes de subir cambios.

1. Instalar hook:
   `make hooks-install`
2. Flujo:
    - compila modulos Python de `app/`
    - en modo `auto` usa `make test` si el contenedor `web` esta corriendo, y si no intenta `make test-local`

Modo de ejecucion opcional del hook:
- `PRE_PUSH_TEST_MODE=docker git push`
- `PRE_PUSH_TEST_MODE=local git push`

### GitHub Actions
Se ejecuta workflow de tests en cada `push` y `pull_request` desde `.github/workflows/tests.yml`.

## Variables de entorno
- `SECRET_KEY`: clave de sesion
- `DATABASE_URL`: URL de Postgres (`postgresql+psycopg://...`)
- `UPLOAD_FOLDER`: carpeta de uploads

## Notas
- El registro crea el primer taller y lo asocia al usuario.
- Los uploads se guardan en `app/static/uploads/<workshop_id>`.
