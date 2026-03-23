#!/usr/bin/env bash
set -euo pipefail

# ─── Config ───────────────────────────────────────────────────────────────────
APP_DIR="/opt/apps/biciservice.cc"
BACKUP_DIR="/opt/apps/backups/manual"
COMPOSE_FILE="docker-compose.prod.yml"
COMPOSE="docker compose -f ${COMPOSE_FILE}"
DB_SERVICE="db"
WEB_SERVICE="web"
DB_NAME="biciservice_cc"
DB_USER="postgres"
MAX_BACKUPS=10
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ─── State tracking ──────────────────────────────────────────────────────────
PREV_SHA=""
BACKUP_DB_FILE=""
DEPLOY_PHASE="init"

# ─── Rollback function ───────────────────────────────────────────────────────
rollback() {
    echo ">>> ROLLBACK INICIADO"

    # Restaurar codigo
    if [[ -n "${PREV_SHA}" ]]; then
        echo ">>> Restaurando codigo a ${PREV_SHA}..."
        cd "${APP_DIR}"
        git checkout "${PREV_SHA}" 2>/dev/null || git reset --hard "${PREV_SHA}" 2>/dev/null || true
    fi

    # Restaurar base de datos
    if [[ -n "${BACKUP_DB_FILE}" && -f "${BACKUP_DB_FILE}" ]]; then
        echo ">>> Restaurando base de datos desde ${BACKUP_DB_FILE}..."
        ${COMPOSE} exec -T ${DB_SERVICE} psql -U ${DB_USER} -d ${DB_NAME} \
            -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" 2>/dev/null || true
        gunzip -c "${BACKUP_DB_FILE}" | \
            ${COMPOSE} exec -T ${DB_SERVICE} psql -U ${DB_USER} ${DB_NAME} 2>/dev/null || true
    fi

    # Rebuild con codigo anterior
    if [[ -n "${PREV_SHA}" ]]; then
        echo ">>> Rebuilding containers con codigo anterior..."
        ${COMPOSE} up --build -d ${WEB_SERVICE} 2>/dev/null || true
    fi

    echo ">>> ROLLBACK COMPLETADO (verificacion manual recomendada)"
}

# ─── Cleanup/Rollback trap ───────────────────────────────────────────────────
cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        echo ">>> DEPLOY FALLO en fase: ${DEPLOY_PHASE}"
        echo ">>> Intentando rollback..."
        rollback
    fi
}
trap cleanup EXIT

# ─── Phase 1: Preflight ──────────────────────────────────────────────────────
cd "${APP_DIR}"
DEPLOY_PHASE="preflight"
echo ">>> [1/6] Verificaciones previas..."

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ "${CURRENT_BRANCH}" != "main" ]]; then
    echo "ERROR: No estamos en branch main (estamos en ${CURRENT_BRANCH})"
    exit 1
fi

docker compose version > /dev/null 2>&1 || { echo "ERROR: docker compose no disponible"; exit 1; }

${COMPOSE} ps --status running ${DB_SERVICE} 2>/dev/null | grep -q "${DB_SERVICE}" || {
    echo "ERROR: servicio db no esta corriendo"
    exit 1
}

echo ">>> Preflight OK"

# ─── Phase 2: Backup ─────────────────────────────────────────────────────────
DEPLOY_PHASE="backup"
PREV_SHA=$(git rev-parse HEAD)
echo ">>> [2/6] Backup (SHA actual: ${PREV_SHA})..."

mkdir -p "${BACKUP_DIR}"

# Database backup
BACKUP_DB_FILE="${BACKUP_DIR}/db_${TIMESTAMP}.sql.gz"
echo ">>> pg_dump -> ${BACKUP_DB_FILE}"
${COMPOSE} exec -T ${DB_SERVICE} pg_dump -U ${DB_USER} ${DB_NAME} | gzip > "${BACKUP_DB_FILE}"

# Validar que el backup no esta vacio
if [[ ! -s "${BACKUP_DB_FILE}" ]]; then
    echo "ERROR: Backup de base de datos esta vacio!"
    exit 1
fi

# Guardar referencia de codigo
echo "${PREV_SHA}" > "${BACKUP_DIR}/code_ref_${TIMESTAMP}.txt"

BACKUP_SIZE=$(du -h "${BACKUP_DB_FILE}" | cut -f1)
echo ">>> Backup OK (DB: ${BACKUP_SIZE})"

# ─── Phase 3: Pull code ──────────────────────────────────────────────────────
DEPLOY_PHASE="git-pull"
echo ">>> [3/6] Descargando cambios..."

git fetch origin main
git reset --hard origin/main

NEW_SHA=$(git rev-parse HEAD)
echo ">>> ${PREV_SHA:0:7} -> ${NEW_SHA:0:7}"

if [[ "${PREV_SHA}" == "${NEW_SHA}" ]]; then
    echo ">>> Sin cambios para deployar. Saliendo."
    exit 0
fi

# ─── Phase 4: Build ──────────────────────────────────────────────────────────
DEPLOY_PHASE="build"
echo ">>> [4/6] Build y restart de contenedores..."

${COMPOSE} up --build -d ${WEB_SERVICE}

# ─── Phase 5: Migrations ─────────────────────────────────────────────────────
DEPLOY_PHASE="migrate"
echo ">>> [5/6] Ejecutando migraciones..."

# Esperar a que el contenedor este listo
sleep 5

${COMPOSE} exec -T ${WEB_SERVICE} flask --app wsgi.py db upgrade

echo ">>> Migraciones OK"

# ─── Phase 6: Health check ───────────────────────────────────────────────────
DEPLOY_PHASE="healthcheck"
echo ">>> [6/6] Health check..."

MAX_RETRIES=10
RETRY_DELAY=3

for i in $(seq 1 ${MAX_RETRIES}); do
    STATUS=$(${COMPOSE} exec -T ${WEB_SERVICE} python -c \
        "import urllib.request; print(urllib.request.urlopen('http://localhost:5000/health').status)" 2>/dev/null || echo "failed")

    if [[ "${STATUS}" == "200" ]]; then
        echo ">>> Health check OK"
        break
    fi

    if [[ $i -eq ${MAX_RETRIES} ]]; then
        echo "ERROR: Health check fallo despues de ${MAX_RETRIES} intentos"
        exit 1
    fi

    echo ">>> Intento ${i}/${MAX_RETRIES} fallo, reintentando en ${RETRY_DELAY}s..."
    sleep ${RETRY_DELAY}
done

# ─── Cleanup old backups ─────────────────────────────────────────────────────
echo ">>> Rotando backups (manteniendo ultimos ${MAX_BACKUPS})..."
ls -t "${BACKUP_DIR}"/db_*.sql.gz 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | xargs -r rm -f
ls -t "${BACKUP_DIR}"/code_ref_*.txt 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | xargs -r rm -f

echo ""
echo "=========================================="
echo "  DEPLOY EXITOSO"
echo "  ${PREV_SHA:0:7} -> ${NEW_SHA:0:7}"
echo "  $(date)"
echo "=========================================="
