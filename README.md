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

## Agent de questions-réponses (Ollama)

Le Copilot utilise l'endpoint `/api/v1/agents/ask` et combine les extraits RAG avec
les symboles et relations du graphe Neo4j. Les réponses affichent les sources.
Le parcours d'import d'un dépôt construit le graphe puis crée également son index RAG.
L'endpoint `POST /api/v1/agents/search` lance un agent en lecture seule : après une première
recherche RAG/graphe, Ollama choisit jusqu'à trois recherches complémentaires parmi des outils
autorisés, puis synthétise une réponse citée. L'agent ne modifie ni n'exécute le code.
La page MLOps affiche les métriques agrégées des appels Copilot (modèle, durée,
statut, nombre d'extraits et citations). Le texte des questions et réponses n'est
pas stocké dans ces métriques.

Installe et démarre [Ollama](https://ollama.com/), puis télécharge le modèle configuré :

```bash
ollama pull qwen2.5-coder:7b
```

Les paramètres `OLLAMA_BASE_URL`, `OLLAMA_MODEL` et `OLLAMA_TIMEOUT` peuvent être
modifiés dans `.env`. Le backend doit pouvoir joindre Ollama à cette adresse.
Pour activer le Copilot, démarre PostgreSQL/pgvector et Neo4j, puis importe un dépôt
depuis l'interface.

## Frontend React

Le frontend React utilise Vite. Démarre d'abord le backend sur le port `8000`, puis :

```bash
cd frontend
npm install
npm run dev
```

Ouvre http://localhost:5173. Vite relaie `/health` et `/api` vers le backend local.
Pour vérifier la compilation de production : `npm run build`.