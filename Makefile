# Zeya - WhatsApp AI Antenatal Education Chatbot
# Run `make help` to see available commands

.PHONY: help up down restart logs migrate test test-cov build clean reset shell db-shell redis-shell ngrok frontend-dev install-hooks

# Default target
help:
	@echo "Zeya - Available Commands"
	@echo "========================="
	@echo ""
	@echo "Docker:"
	@echo "  make up        - Start all services"
	@echo "  make down      - Stop all services"
	@echo "  make restart   - Restart backend service"
	@echo "  make logs      - View backend logs (follow mode)"
	@echo "  make build     - Rebuild all containers"
	@echo "  make clean     - Stop and remove volumes"
	@echo "  make reset     - Clean reset (removes data)"
	@echo ""
	@echo "Database:"
	@echo "  make migrate   - Run database migrations"
	@echo "  make db-shell  - Open PostgreSQL shell"
	@echo ""
	@echo "Testing:"
	@echo "  make test      - Run all tests"
	@echo "  make test-cov  - Run tests with coverage"
	@echo ""
	@echo "Development:"
	@echo "  make shell     - Open backend shell"
	@echo "  make redis-shell - Open Redis CLI"
	@echo "  make ngrok     - Start ngrok tunnel (port 8001)"
	@echo "  make frontend-dev - Run frontend dev server"
	@echo "  make install-hooks - Install git pre-commit hooks"
	@echo ""
	@echo "URLs:"
	@echo "  Backend API:  http://localhost:8001/docs"
	@echo "  Frontend:     http://localhost:3000"

# ============ Docker Commands ============

up:
	docker-compose up -d
	@echo "✓ Services started"
	@echo "  Backend: http://localhost:8001/docs"
	@echo "  Frontend: http://localhost:3000"

down:
	docker-compose down
	@echo "✓ Services stopped"

restart:
	docker-compose restart backend
	@echo "✓ Backend restarted"

logs:
	docker-compose logs -f backend

build:
	docker-compose build
	@echo "✓ Containers rebuilt"

clean:
	docker-compose down -v
	@echo "✓ Services stopped and volumes removed"

reset: clean up migrate
	@echo "✓ Clean reset complete"

# ============ Database Commands ============

migrate:
	docker-compose exec backend alembic upgrade head
	@echo "✓ Migrations complete"

db-shell:
	docker-compose exec db psql -U postgres -d antenatal_chatbot

# ============ Testing Commands ============

test:
	docker-compose exec backend pytest -v

test-cov:
	docker-compose exec backend pytest --cov=app --cov-report=term-missing

# ============ Development Commands ============

shell:
	docker-compose exec backend /bin/sh

redis-shell:
	docker-compose exec redis redis-cli

ngrok:
	@echo "Starting ngrok tunnel..."
	@echo "Copy the https URL to Meta Developer Console"
	@echo "Webhook URL: <ngrok-url>/api/v1/webhook"
	@echo "Verify Token: zeya_webhook_verify_2026"
	@echo ""
	ngrok http 8001

frontend-dev:
	cd frontend && npm install && npm run dev

install-hooks:
	cp scripts/pre-commit .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit
	@echo "✓ Git hooks installed"
