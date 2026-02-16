.DEFAULT_GOAL := help

PYTHON ?= python3
PIP ?= pip
FLASK_APP ?= wsgi.py
FLASK ?= flask --app $(FLASK_APP)
DOCKER_COMPOSE ?= docker compose
WEB_SERVICE ?= web
DB_SERVICE ?= db

.PHONY: help \
	venv install env run test test-local hooks-install \
	db-upgrade db-migrate db-downgrade \
	build up up-build up-full down restart docker-ps logs \
	docker-db-upgrade docker-db-migrate docker-db-downgrade docker-test \
	shell db-shell landing-dev email-test docker-email-test \
	prod-up prod-down prod-logs prod-db-upgrade prod-shell prod-email-test

help: ## Mostrar comandos disponibles
	@awk 'BEGIN {FS = ":.*##"; printf "\nUso:\n  make <objetivo>\n\nObjetivos:\n"} /^[a-zA-Z0-9_.-]+:.*##/ {printf "  %-22s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

venv: ## Crear virtualenv en .venv
	$(PYTHON) -m venv .venv

install: ## Instalar dependencias locales
	$(PIP) install -r requirements.txt

env: ## Copiar .env.example a .env si no existe
	@if [ ! -f .env ]; then cp .env.example .env && echo ".env creado"; else echo ".env ya existe"; fi

run: ## Levantar app local (Flask)
	$(FLASK) run

test-local: ## Ejecutar tests locales
	pytest

hooks-install: ## Instalar hooks locales versionados
	bash scripts/install-hooks.sh

db-upgrade: ## Ejecutar migraciones locales (upgrade)
	$(FLASK) db upgrade

db-migrate: ## Crear migracion local (usar MSG="descripcion")
	$(FLASK) db migrate -m "$(MSG)"

db-downgrade: ## Revertir una migracion local (usar REV=-1 por defecto)
	$(FLASK) db downgrade $(or $(REV),-1)

build: ## Build de imagenes Docker
	$(DOCKER_COMPOSE) build

up: ## Levantar Docker sin rebuild
	$(DOCKER_COMPOSE) up -d

up-build: ## Levantar Docker con build
	$(DOCKER_COMPOSE) up --build -d

up-full: ## Levantar stack completo (foreground)
	$(DOCKER_COMPOSE) up --build

down: ## Bajar servicios Docker
	$(DOCKER_COMPOSE) down

restart: ## Reiniciar servicios Docker
	$(DOCKER_COMPOSE) restart

docker-ps: ## Ver estado de contenedores
	$(DOCKER_COMPOSE) ps

logs: ## Ver logs (usar SERVICE=web y TAIL=200)
	$(DOCKER_COMPOSE) logs -f --tail $(or $(TAIL),200) $(SERVICE)

landing-dev: ## Levantar landing estatica en localhost:8080
	$(PYTHON) -m http.server 8080 --directory landing

email-test: ## Enviar correo de prueba local (pide email)
	$(FLASK) send-test-email

docker-db-upgrade: ## Ejecutar migraciones en Docker (upgrade)
	$(DOCKER_COMPOSE) exec $(WEB_SERVICE) $(FLASK) db upgrade

docker-db-migrate: ## Crear migracion en Docker (usar MSG="descripcion")
	$(DOCKER_COMPOSE) exec $(WEB_SERVICE) $(FLASK) db migrate -m "$(MSG)"

docker-db-downgrade: ## Revertir migracion en Docker (usar REV=-1 por defecto)
	$(DOCKER_COMPOSE) exec $(WEB_SERVICE) $(FLASK) db downgrade $(or $(REV),-1)

test: ## Ejecutar tests dentro de Docker
	$(DOCKER_COMPOSE) exec $(WEB_SERVICE) pytest

docker-test: ## Alias para tests dentro de Docker
	$(DOCKER_COMPOSE) exec $(WEB_SERVICE) pytest

docker-email-test: ## Enviar correo de prueba en Docker (pide email)
	$(DOCKER_COMPOSE) exec $(WEB_SERVICE) $(FLASK) send-test-email

shell: ## Abrir shell en contenedor web
	$(DOCKER_COMPOSE) exec $(WEB_SERVICE) sh

db-shell: ## Abrir psql en contenedor db
	$(DOCKER_COMPOSE) exec $(DB_SERVICE) psql -U postgres -d biciservice_cc

# --- Produccion ---

PROD_COMPOSE = $(DOCKER_COMPOSE) -f docker-compose.prod.yml

prod-up: ## Levantar entorno produccion
	$(PROD_COMPOSE) up --build -d

prod-down: ## Bajar entorno produccion
	$(PROD_COMPOSE) down

prod-logs: ## Ver logs produccion (usar SERVICE=web y TAIL=200)
	$(PROD_COMPOSE) logs -f --tail $(or $(TAIL),200) $(SERVICE)

prod-db-upgrade: ## Ejecutar migraciones en produccion
	$(PROD_COMPOSE) exec web $(FLASK) db upgrade

prod-shell: ## Abrir shell en contenedor web produccion
	$(PROD_COMPOSE) exec web sh

prod-email-test: ## Enviar correo de prueba en produccion (pide email)
	$(PROD_COMPOSE) exec web $(FLASK) send-test-email
