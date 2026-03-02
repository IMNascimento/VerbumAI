.PHONY: install install-dev setup query shell clean help

# ── Configuração ─────────────────────────────────────────────────────────────
PYTHON     = python
VENV       = .venv
VENV_PY    = $(VENV)/bin/python
PIP        = $(VENV)/bin/pip
VERBUM     = $(VENV)/bin/verbum

# ── Targets ──────────────────────────────────────────────────────────────────

help:  ## Mostra esta ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install:  ## Cria venv e instala dependências
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e .
	@echo "\n✅ Instalação concluída. Agora rode: make setup"

install-dev:  ## Instala com dependências de desenvolvimento
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev,api]"
	@echo "\n✅ Instalação dev concluída."

install-api:  ## Instala com servidor FastAPI
	$(PIP) install -e ".[api]"

setup:  ## Baixa a Bíblia e indexa no banco vetorial (rode uma vez)
	$(VERBUM) setup

query:  ## Modo interativo de consulta
	$(VERBUM) query

serve:  ## Sobe a API REST (requer: make install-api)
	$(VENV)/bin/uvicorn verbum.api.server:app --reload --port 8000

clean:  ## Remove banco vetorial e arquivos temporários
	rm -rf data/chroma_db __pycache__ **/__pycache__ *.egg-info
	@echo "🧹 Limpeza concluída."

clean-all: clean  ## Remove também o venv e a Bíblia baixada
	rm -rf $(VENV) data/
	@echo "🧹 Limpeza total concluída."
