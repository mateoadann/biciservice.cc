# Service Bicycle CRM — Guia completa de gestion

Esta guia explica paso a paso como levantar, mantener, actualizar y gestionar
la aplicacion tanto en desarrollo (tu maquina local) como en produccion (VPS).

---

## Indice

1. [Arquitectura general](#1-arquitectura-general)
2. [Archivo .env — una sola fuente de configuracion](#2-archivo-env--una-sola-fuente-de-configuracion)
3. [Desarrollo local](#3-desarrollo-local)
4. [Produccion en VPS](#4-produccion-en-vps)
5. [Despliegue inicial (primera vez)](#5-despliegue-inicial-primera-vez)
6. [Actualizaciones (git pull + redeploy)](#6-actualizaciones-git-pull--redeploy)
7. [Migraciones de base de datos](#7-migraciones-de-base-de-datos)
8. [Landing page](#8-landing-page)
9. [Videos con Remotion](#9-videos-con-remotion)
10. [Backups](#10-backups)
11. [Monitoreo y logs](#11-monitoreo-y-logs)
12. [Troubleshooting](#12-troubleshooting)
13. [Referencia de comandos Make](#13-referencia-de-comandos-make)

---

## 1. Arquitectura general

El proyecto tiene dos modos de ejecucion que usan archivos Docker Compose distintos:

```
TU MAQUINA (dev)                    VPS (prod)
─────────────────                   ──────────────────────────────────
docker-compose.yml                  docker-compose.prod.yml

  web (Flask dev server)              npm (Nginx Proxy Manager)
    puerto 5001                         puertos 80, 443, 81
  db (PostgreSQL)                     landing (nginx:alpine)
    puerto 5433                         puerto 80 interno
                                      web (Flask + Gunicorn)
                                        puerto 5000 interno
                                      db (PostgreSQL)
                                        puerto 5432 interno
```

**En desarrollo:** accedes directamente a Flask en `localhost:5001`. No hay proxy,
no hay SSL, no hay landing. Simple y rapido.

**En produccion:** Nginx Proxy Manager (NPM) es el unico punto de entrada. Recibe
todo el trafico en los puertos 80/443, y lo rutea segun el subdominio:
- `tudominio.com` → contenedor `landing` (pagina publica)
- `app.tudominio.com` → contenedor `web` (el CRM)

Ningun otro contenedor expone puertos al exterior.

---

## 2. Archivo .env — una sola fuente de configuracion

Ambos entornos usan un unico archivo `.env` en la raiz del proyecto.
Este archivo esta en `.gitignore`, asi que:

- **Nunca se sube a GitHub** (tus secretos estan seguros)
- **`git pull` nunca lo sobreescribe** (cada entorno tiene el suyo)
- Cuando clonas el repo por primera vez, copias el template:
  ```bash
  cp .env.example .env
  ```

### .env en desarrollo (tu maquina)

```env
SECRET_KEY=cualquier-texto-para-dev
DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/service_bicycle_crm
UPLOAD_FOLDER=/app/app/static/uploads
SESSION_COOKIE_SECURE=false
REMEMBER_COOKIE_SECURE=false
FLASK_DEBUG=1
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=service_bicycle_crm
```

Notas:
- `DATABASE_URL` usa `@db:` porque `db` es el nombre del servicio Docker.
  Si corres Flask sin Docker (directo en tu maquina), cambialo a `@localhost:`.
- `SESSION_COOKIE_SECURE=false` porque no hay HTTPS en local.
- `FLASK_DEBUG=1` activa el modo debug de Flask (errores detallados, reloader).

### .env en produccion (el VPS)

```env
SECRET_KEY=una-clave-larga-y-aleatoria-de-al-menos-32-caracteres
DATABASE_URL=postgresql+psycopg://postgres:tu-password-seguro@db:5432/service_bicycle_crm
UPLOAD_FOLDER=/app/app/static/uploads
SESSION_COOKIE_SECURE=true
REMEMBER_COOKIE_SECURE=true
FLASK_DEBUG=0
POSTGRES_USER=postgres
POSTGRES_PASSWORD=tu-password-seguro
POSTGRES_DB=service_bicycle_crm
```

Diferencias clave:
- `SECRET_KEY`: una cadena larga y aleatoria. Puedes generarla con:
  ```bash
  python3 -c "import secrets; print(secrets.token_hex(32))"
  ```
- `POSTGRES_PASSWORD`: una password real (no "postgres").
- `SESSION_COOKIE_SECURE=true`: las cookies solo se envian por HTTPS.
- `FLASK_DEBUG=0`: nunca dejes debug activo en produccion.

---

## 3. Desarrollo local

### Requisitos previos

- Docker Desktop instalado y corriendo
- Git
- Make (viene con macOS, en Linux: `sudo apt install make`)

### Levantar por primera vez

```bash
# 1. Clonar el repositorio
git clone <tu-repo-url>
cd service_bicycle_crm

# 2. Crear archivo de configuracion
cp .env.example .env
# Edita .env si necesitas cambiar algo (los defaults de dev funcionan)

# 3. Levantar los contenedores
make up-build

# 4. Ejecutar migraciones de base de datos
make docker-db-upgrade

# 5. Crear el super admin
docker compose exec web flask --app wsgi.py create-superadmin
# Te pedira email, nombre y password
```

Ahora accede a `http://localhost:5001` y logueate.

### Flujo de trabajo diario

```bash
# Levantar (si los contenedores estan parados)
make up

# Ver logs en tiempo real
make logs SERVICE=web

# Ejecutar tests
make test

# Abrir shell dentro del contenedor
make shell

# Abrir psql para consultas SQL
make db-shell

# Parar todo
make down
```

### Hot reload

El archivo `docker-compose.yml` monta `./app` como volumen:
```yaml
volumes:
  - ./app:/app/app
```
Esto significa que cuando editas un archivo Python en `app/`, Flask detecta el
cambio y reinicia automaticamente. No necesitas hacer `make down && make up-build`
cada vez que cambias codigo.

**Excepcion:** si cambias `requirements.txt`, `Dockerfile`, o archivos fuera de
`app/`, si necesitas rebuild:
```bash
make up-build
```

### Previsualizar la landing page

```bash
make landing-dev
# Abre http://localhost:8080
```

---

## 4. Produccion en VPS

### Requisitos del VPS

- Ubuntu 22.04+ (o similar)
- Docker y Docker Compose instalados
- Un dominio apuntando al VPS (registros DNS tipo A):
  - `tudominio.com` → IP del VPS
  - `app.tudominio.com` → IP del VPS
- Puerto 80 y 443 abiertos en el firewall

### Instalar Docker en el VPS (si no esta)

```bash
# Conectarte al VPS
ssh usuario@IP-del-VPS

# Instalar Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Cerrar sesion y volver a entrar para que tome efecto

# Verificar
docker --version
docker compose version
```

---

## 5. Despliegue inicial (primera vez)

Estos son los pasos exactos para poner la app en produccion por primera vez.

### Paso 1: Clonar el repositorio en el VPS

```bash
ssh usuario@IP-del-VPS
cd /opt  # o donde prefieras poner la app
git clone <tu-repo-url> service_bicycle_crm
cd service_bicycle_crm
```

### Paso 2: Crear el .env de produccion

```bash
cp .env.example .env
nano .env  # o vi, o el editor que prefieras
```

Cambia los valores a produccion (ver seccion 2 arriba). Lo mas importante:
- `SECRET_KEY` → una cadena aleatoria larga
- `POSTGRES_PASSWORD` → una password real
- `DATABASE_URL` → que use la misma password
- `SESSION_COOKIE_SECURE=true`
- `FLASK_DEBUG=0`

### Paso 3: Levantar los contenedores

```bash
make prod-up
```

Esto levanta 4 contenedores:
- `npm` — Nginx Proxy Manager (el proxy)
- `landing` — pagina publica
- `web` — el CRM (Flask + Gunicorn)
- `db` — PostgreSQL

### Paso 4: Ejecutar migraciones

```bash
make prod-db-upgrade
```

### Paso 5: Crear el super admin

```bash
docker compose -f docker-compose.prod.yml exec web flask --app wsgi.py create-superadmin
```

### Paso 6: Configurar Nginx Proxy Manager

Abre en tu navegador: `http://IP-del-VPS:81`

Credenciales iniciales:
- Email: `admin@example.com`
- Password: `changeme`

NPM te pedira cambiar las credenciales en el primer login. Hazlo.

Ahora configura los proxy hosts:

#### Landing (tudominio.com)

1. Click en "Proxy Hosts" → "Add Proxy Host"
2. Domain Names: `tudominio.com` y `www.tudominio.com`
3. Scheme: `http`
4. Forward Hostname / IP: `landing`
5. Forward Port: `80`
6. Pestana "SSL":
   - Request a new SSL Certificate
   - Marcar "Force SSL"
   - Marcar "HTTP/2 Support"
   - Agregar tu email para Let's Encrypt
   - Guardar

#### CRM (app.tudominio.com)

1. Click en "Proxy Hosts" → "Add Proxy Host"
2. Domain Names: `app.tudominio.com`
3. Scheme: `http`
4. Forward Hostname / IP: `web`
5. Forward Port: `5000`
6. Pestana "SSL":
   - Request a new SSL Certificate
   - Marcar "Force SSL"
   - Marcar "HTTP/2 Support"
   - Agregar tu email para Let's Encrypt
   - Guardar

Listo. Ahora:
- `https://tudominio.com` → muestra la landing page
- `https://app.tudominio.com` → muestra el CRM (login)

### Paso 7: Asegurar el panel de NPM

El panel de NPM queda en el puerto 81. Opciones para protegerlo:
- **Opcion A (recomendada):** cerrar el puerto 81 en el firewall del VPS y
  acceder solo via SSH tunnel:
  ```bash
  ssh -L 8181:localhost:81 usuario@IP-del-VPS
  # Luego abrir http://localhost:8181 en tu navegador local
  ```
- **Opcion B:** dejarlo abierto pero con credenciales fuertes.

---

## 6. Actualizaciones (git pull + redeploy)

Cuando hagas cambios en tu maquina local, commiteaste y pusheaste a GitHub,
y quieras actualizar produccion:

```bash
# En el VPS
ssh usuario@IP-del-VPS
cd /opt/service_bicycle_crm

# 1. Traer los cambios
git pull

# 2. Reconstruir y levantar
make prod-up
# Esto hace "docker compose -f docker-compose.prod.yml up --build -d"
# Reconstruye la imagen solo si cambio algo (Dockerfile, requirements, codigo)

# 3. Si hay migraciones nuevas
make prod-db-upgrade

# 4. Verificar que todo esta corriendo
docker compose -f docker-compose.prod.yml ps
```

**Importante:** `git pull` NUNCA toca tu `.env` porque esta en `.gitignore`.
Tus secretos y configuracion de produccion quedan intactos.

### Que pasa si actualizo requirements.txt?

`make prod-up` detecta el cambio y reconstruye la imagen automaticamente.
No necesitas hacer nada extra.

### Que pasa si actualizo la landing?

La landing se monta como volumen (`./landing:/usr/share/nginx/html:ro`), asi que
`git pull` actualiza los archivos y Nginx los sirve inmediatamente. No necesitas
reiniciar nada.

---

## 7. Migraciones de base de datos

### Crear una nueva migracion (en desarrollo)

Cuando cambias un modelo en `app/models.py`:

```bash
# Dentro de Docker
make docker-db-migrate MSG="add user approval fields"

# Aplicar la migracion
make docker-db-upgrade
```

Esto crea un archivo en `migrations/versions/`. Commitea ese archivo.

### Aplicar migraciones en produccion

```bash
# En el VPS, despues de git pull
make prod-db-upgrade
```

### Revertir una migracion

```bash
# Dev
make docker-db-downgrade

# Prod
docker compose -f docker-compose.prod.yml exec web flask --app wsgi.py db downgrade -1
```

---

## 8. Landing page

La landing es HTML estatico puro en la carpeta `landing/`:

```
landing/
  index.html          # Pagina principal (single-page)
  css/landing.css      # Estilos
  js/landing.js        # Smooth scroll, menu mobile
  img/                 # Logo, favicon, screenshots
  videos/              # Videos MP4 generados con Remotion
```

### Editar la landing

1. Edita los archivos en `landing/`
2. Previsualiza con `make landing-dev` (localhost:8080)
3. Commitea y pushea
4. En el VPS: `git pull` (los cambios se reflejan automaticamente)

### Links al CRM

En `landing/index.html`, los links al CRM usan el atributo `data-path`:
```html
<a class="button app-link" data-path="/auth/register" href="https://app.dominio.com/auth/register">
```

El archivo `landing/js/landing.js` puede construir la URL dinamicamente basandose
en el dominio actual, o puedes hardcodear tu subdominio real.

---

## 9. Videos con Remotion

Remotion genera videos con React. El proyecto vive en `remotion/`.

### Generar videos

```bash
cd remotion
npm install                    # Solo la primera vez
npx remotion studio            # Preview en el navegador
npx remotion render src/index.jsx DashboardDemo out/demo-dashboard.mp4
npx remotion render src/index.jsx ClientesDemo out/demo-clientes.mp4
```

Los MP4 generados se copian a `landing/videos/` y se commitean:
```bash
cp out/*.mp4 ../landing/videos/
cd ..
git add landing/videos/
git commit -m "Update demo videos"
```

---

## 10. Backups

### Backup de la base de datos

```bash
# En el VPS
docker compose -f docker-compose.prod.yml exec db \
  pg_dump -U postgres service_bicycle_crm > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restaurar un backup

```bash
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U postgres service_bicycle_crm < backup_20260215_120000.sql
```

### Backup automatico (cron)

Agrega esto al crontab del VPS (`crontab -e`):
```cron
# Backup diario a las 3:00 AM
0 3 * * * cd /opt/service_bicycle_crm && docker compose -f docker-compose.prod.yml exec -T db pg_dump -U postgres service_bicycle_crm > /opt/backups/db_$(date +\%Y\%m\%d).sql
```

Crea la carpeta de backups:
```bash
sudo mkdir -p /opt/backups
```

### Backup de uploads

Los archivos subidos por usuarios estan en el volumen Docker `uploads`.
Para respaldarlo:
```bash
docker compose -f docker-compose.prod.yml cp web:/app/app/static/uploads ./backup_uploads
```

---

## 11. Monitoreo y logs

### Ver logs en tiempo real

```bash
# Todos los servicios
make prod-logs

# Solo el CRM
make prod-logs SERVICE=web

# Solo la base de datos
make prod-logs SERVICE=db

# Solo Nginx Proxy Manager
make prod-logs SERVICE=npm
```

### Ver estado de los contenedores

```bash
docker compose -f docker-compose.prod.yml ps
```

Deberias ver todos con estado "Up":
```
NAME        IMAGE                             STATUS
npm         jc21/nginx-proxy-manager:latest   Up
landing     nginx:alpine                      Up
web         service_bicycle_crm-web           Up
db          postgres:16-alpine                Up
```

### Reiniciar un servicio especifico

```bash
docker compose -f docker-compose.prod.yml restart web
```

---

## 12. Troubleshooting

### "Connection refused" al acceder al CRM

1. Verificar que los contenedores estan corriendo:
   ```bash
   docker compose -f docker-compose.prod.yml ps
   ```
2. Ver logs del contenedor web:
   ```bash
   make prod-logs SERVICE=web
   ```
3. Verificar que NPM tiene el proxy host configurado correctamente.

### "502 Bad Gateway" en el navegador

NPM no puede conectar con el contenedor destino. Causas comunes:
- El contenedor `web` no esta corriendo
- El hostname en NPM esta mal (debe ser `web`, no `localhost`)
- El puerto en NPM esta mal (debe ser `5000` para el CRM, `80` para la landing)

### Las migraciones fallan

```bash
# Ver el error completo
docker compose -f docker-compose.prod.yml exec web flask --app wsgi.py db upgrade 2>&1

# Si la BD esta corrupta, restaurar backup
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U postgres service_bicycle_crm < backup_reciente.sql
```

### Olvidaste la password del super admin

```bash
make prod-shell
# Dentro del contenedor:
flask --app wsgi.py create-superadmin
# Si ya existe un super admin, te dira "Ya existe un super admin"
# En ese caso, usa psql para resetear la password directamente
```

### El .env no se aplica despues de cambiarlo

Docker Compose lee el `.env` al hacer `up`. Si cambiaste valores, necesitas:
```bash
make prod-down
make prod-up
```

### Espacio en disco lleno

```bash
# Ver uso de espacio por Docker
docker system df

# Limpiar imagenes y contenedores sin uso
docker system prune -f

# Limpiar TODAS las imagenes no usadas (libera mas espacio)
docker image prune -a -f
```

---

## 13. Referencia de comandos Make

### Desarrollo

| Comando | Que hace |
|---------|----------|
| `make up-build` | Levantar dev con rebuild |
| `make up` | Levantar dev sin rebuild |
| `make down` | Parar todo |
| `make restart` | Reiniciar contenedores |
| `make logs SERVICE=web` | Ver logs |
| `make test` | Ejecutar tests |
| `make shell` | Shell en contenedor web |
| `make db-shell` | Consola psql |
| `make docker-db-upgrade` | Aplicar migraciones |
| `make docker-db-migrate MSG="desc"` | Crear migracion |
| `make landing-dev` | Preview landing en :8080 |

### Produccion

| Comando | Que hace |
|---------|----------|
| `make prod-up` | Levantar prod con rebuild |
| `make prod-down` | Parar todo |
| `make prod-logs SERVICE=web` | Ver logs |
| `make prod-db-upgrade` | Aplicar migraciones |
| `make prod-shell` | Shell en contenedor web |
