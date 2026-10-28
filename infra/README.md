# DevKnowledgeHub

Plateforme d'intelligence logicielle : code + docs + tickets, avec RAG, GraphRAG et ML.

## Structure

Dossiers : `backend/`, `frontend/`, `ml/`, `pipelines/`, `monitoring/`, `evaluation/`, `infra/`, `docs/`, `tests/`.

## Étape 1 — Démarrage

```bash
cp .env.example .env            # puis modifie les mots de passe
docker compose up -d            # PostgreSQL (pgvector) + Neo4j

cd backend
python -m venv .venv
source .venv/bin/activate       # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python dev.py
```

- API : http://localhost:8000/health
- Docs Swagger : http://localhost:8000/docs
- Neo4j Browser : http://localhost:7474

Tests : `cd backend && pytest`

Alternative directe : `uvicorn app.main:app --reload --reload-dir app`


cd C:\Users\asus\Desktop\devknowledgehub\backend
.\.venv\Scripts\python.exe dev.py

## Frontend React

Le frontend React utilise Vite. Démarre d'abord le backend sur le port `8000`, puis :

```bash
cd frontend
npm install
npm run dev
```

Ouvre http://localhost:5173. Vite relaie `/health` et `/api` vers le backend local.
Pour vérifier la compilation de production : `npm run build`.

## RAG (pgvector)

```bash
curl -X POST localhost:8000/api/v1/rag/index  -H 'content-type: application/json' \
     -d '{"repo_name":"click","git_url":"https://github.com/pallets/click"}'
curl -X POST localhost:8000/api/v1/rag/search -H 'content-type: application/json' \
     -d '{"repo_name":"click","question":"où est géré le décorateur option ?","top_k":5}'
```

Par défaut `EMBEDDING_BACKEND=hash` (sans dépendance). Pour des résultats sémantiques
(questions en français sur du code anglais) : `pip install -r backend/requirements-ml.txt`
puis `EMBEDDING_BACKEND=sentence-transformers` dans `.env`.
Tests d'intégration pgvector : `DKH_TEST_PG=postgresql://user:pwd@localhost:5433/db pytest`.
