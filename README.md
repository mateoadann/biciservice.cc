<p align="center">
  <img src="app/static/css/favicon_bike1.png" alt="biciservice.cc" width="96" />
</p>

<h1 align="center">biciservice.cc</h1>

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

## Soporte mobile (mobile-first)
- Breakpoints principales:
  - Base: `360px-430px` (sin media query, prioridad mobile)
  - Tablet: `>=641px`
  - Desktop: `>=981px`
- Objetivos UX:
  - sin scroll horizontal en pantallas clave
  - botones e inputs con tap target amplio
  - tablas grandes con patron mobile tipo card en listados clave
  - formularios con tipos de input y autocomplete para teclado movil

## PWA (modo app en navegador)
- Manifest: `GET /manifest.webmanifest`
- Service worker: `GET /sw.js`
- Icono iOS: `GET /apple-touch-icon.png`
- Registro del service worker: `app/static/js/pwa-register.js`

### Alcance de cache y seguridad
- Se cachean solo assets estaticos (`/static/*`, manifest, offline page).
- Navegacion a rutas sensibles/autenticadas usa red (sin cache persistente de HTML privado).
- Rutas auth y privadas no se guardan en cache offline para evitar contenido stale o sensible.

## Como probar mobile y PWA en dev
1. Levantar app:
   - Docker: `make up-build`
   - Local: `make run`
2. Abrir DevTools y probar viewports:
   - iPhone 13 (`390x844`)
   - Pixel 7 (`412x915`)
3. Verificar:
   - login, dashboard, jobs, clients, bicycles, services
   - sin overflow horizontal
   - acciones principales visibles y clickeables

### Install / Add to Home Screen
- Android (Chrome): menu del navegador -> `Install app` o `Agregar a pantalla principal`.
- iOS (Safari): compartir -> `Agregar a pantalla de inicio`.
- Nota: service worker requiere contexto seguro (`https`) o `localhost`.

## Guia rapida de estilos/componentes
- Layout principal: `app/templates/base.html` + `app/static/css/app.css`.
- Tablas responsive: usar `table-mobile-cards` + `data-label` por `td`.
- Formularios: usar `form-grid`/`form-actions` y mostrar `field-error` por campo.
- Botones y acciones: mantener clases `button`, `button-ghost`, `button-danger`.
- Confirmaciones destructivas: formularios con `js-confirm` y `data-confirm-*`.

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
- `APP_BASE_URL`: URL publica de la app (ej. `https://app.tudominio.com`)
- `MAIL_FROM`: remitente de correos (ej. `no-reply@tudominio.com`)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`: credenciales SMTP
- `SMTP_USE_TLS` / `SMTP_USE_SSL`: seguridad del transporte SMTP
- `MAIL_TIMEOUT_SECONDS`: timeout de conexion SMTP
- `ADMIN_NOTIFICATION_EMAIL`: email para avisos de nuevos registros pendientes

## Correo de confirmacion en produccion
El sistema ya envia correos de confirmacion, aprobacion y reset de contrasena via SMTP.

Pasos sugeridos:
1. Configurar proveedor SMTP (Gmail para pruebas o proveedor transaccional para prod).
2. Cargar variables SMTP en `.env`.
3. Levantar servicios y validar envio con un correo de prueba.

Nota Gmail: activar verificacion en 2 pasos y usar `App Password` en `SMTP_PASSWORD`.

Comandos de prueba:
- Local: `make email-test`
- Docker dev: `make docker-email-test`
- Docker prod: `make prod-email-test`

Los comandos piden por consola el email destino para validar el envio.

## Flujo sugerido para trabajar
1. `make up-build`
2. `make docker-db-upgrade`
3. desarrollar cambios
4. `make test`
5. `git push`

## Notas
- El registro crea el primer taller y lo asocia al usuario.
- Los uploads se guardan en `app/static/uploads/<workshop_id>`.
