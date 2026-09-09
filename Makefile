.PHONY: install seed ingest test run compose-up compose-up-full compose-up-gpu compose-logs lint

install:
	pip install -e ".[dev]"

seed:
	medassist seed-db

ingest:
	medassist ingest

test:
	pytest -q --cov=medassist --cov-report=term-missing

run:
	streamlit run src/medassist/ui/app_streamlit.py

compose-up:
	docker compose up app ollama

# Stack completa (ollama + model-init cria `medassist` do GGUF + app), Ollama em CPU.
compose-up-full:
	docker compose --profile full up -d --build ollama model-init app

# Idem, mas Ollama na GPU NVIDIA (ver docker-compose.gpu.yml). Fine-tuning segue no Colab.
compose-up-gpu:
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile full up -d --build ollama model-init app

compose-logs:
	docker compose logs -f

lint:
	ruff check src tests
