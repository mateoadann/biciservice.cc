<p align="center">
  <img src="app/static/css/favicon_bike1.png" alt="Service Bicycle CRM" width="96" />
</p>

<h1 align="center">Service Bicycle CRM</h1>

<p align="center">Plataforma para la gestion diaria de talleres de bicicletas.</p>

---

## Stack
- Python + Flask
- PostgreSQL
- SQLAlchemy + Flask-Migrate
- Flask-Login + Flask-WTF
- Docker Compose

## Inicio rapido con Docker (recomendado)
1. Copiar variables de entorno:
   `cp .env.example .env`
2. Levantar servicios:
   `docker compose up -d --build`
3. Ejecutar migraciones:
   `docker compose exec web flask --app wsgi.py db upgrade`
4. Abrir la aplicacion:
   `http://localhost:5001`

## Comandos utiles (Docker)
- Levantar con rebuild: `make up-build`
- Levantar sin rebuild: `make up`
- Bajar servicios: `make down`
- Ver logs: `make logs SERVICE=web`
- Migrar DB: `make docker-db-upgrade`
- Crear migracion: `make docker-db-migrate MSG="descripcion"`
- Revertir migracion: `make docker-db-downgrade REV=-1`
- Entrar al contenedor web: `make shell`

## Tests y automatizacion
- Tests en Docker: `make test`
- Alias Docker tests: `make docker-test`
- Tests locales (opcional): `make test-local`

### Hook pre-push
El repositorio incluye un hook `pre-push` versionado para validar antes de hacer push.

1. Instalar hook:
   `make hooks-install`
2. Flujo por defecto (`auto`):
   - compila modulos Python de `app/`
   - si `web` esta corriendo, ejecuta tests en Docker
   - si no, intenta tests locales

Modo de ejecucion opcional del hook:
- `PRE_PUSH_TEST_MODE=docker git push`
- `PRE_PUSH_TEST_MODE=local git push`

### GitHub Actions
Se ejecuta workflow de tests en cada `push` y `pull_request` desde `.github/workflows/tests.yml`.

## Variables de entorno
- `SECRET_KEY`: clave de sesion
- `DATABASE_URL`: URL de Postgres (`postgresql+psycopg://...`)
- `UPLOAD_FOLDER`: carpeta de uploads
- `SESSION_COOKIE_SECURE`: usar `true` en produccion
- `REMEMBER_COOKIE_SECURE`: usar `true` en produccion

## Flujo sugerido para trabajar
1. `make up-build`
2. `make docker-db-upgrade`
3. desarrollar cambios
4. `make test`
5. `git push`

## Notas
- El registro crea el primer taller y lo asocia al usuario.
- Los uploads se guardan en `app/static/uploads/<workshop_id>`.
