# DevKnowledgeHub

Plateforme d'intelligence logicielle : code, documentation et tickets réunis dans un même
espace, avec recherche RAG, graphe de connaissances (GraphRAG), détecteurs ML et monitoring.

## Fonctionnalités

- **Ingestion de projets** : dépôt Git ou archive ZIP, analyse multi-langages (Python, Java,
  JavaScript, TypeScript, TSX), construction du graphe Neo4j et indexation pgvector.
- **GraphRAG** : recherche vectorielle + expansion dans le graphe (symboles, appels, imports,
  documentation, tickets, findings).
- **Copilot et agents spécialisés** : huit agents en lecture seule (Copilot, chercheur,
  architecte, documentaliste, impact, triage, revue qualité, plan de tests), avec citations,
  traces et exécution suivie dans MLOps.
- **Documentation et tickets** : collecte des README/docs, import et classification des
  tickets (`BUG`, `FEATURE`, `TECHNICAL_DEBT`).
- **Détecteurs** : vulnérabilités, code smells, clones de code, type de projet. Les findings
  sont persistés et exposés dans l'interface.
- **MLOps** : suivi des exécutions de l'agent, latence RAG, qualité des détecteurs, feedback
  utilisateur. Le texte des questions et des réponses n'est pas stocké dans les métriques.

## Architecture

```text
frontend (React/Vite) ──> backend (FastAPI) ──> PostgreSQL + pgvector (documents, RAG, métadonnées)
                                      ├──────> Neo4j (code, appels, docs, tickets, findings)
                                      ├──────> Ollama (génération)
                                      └──────> modèles ML (joblib / détecteurs statiques)
```

Choix documenté : pgvector sert de base vectorielle au lieu d'une base séparée
(`docs/architecture/adr/0001-choix-pgvector.md`). Les services lourds peuvent être
externalisés si le volume augmente.

## Agents spécialisés

Le catalogue est exposé par `GET /api/v1/agents/catalog` et exécuté via
`POST /api/v1/agents/specialist`. Tous les agents sont en lecture seule : aucun n'exécute
de code, ne modifie un fichier ou ne crée de ticket.

| Agent | Rôle | Sources |
| --- | --- | --- |
| `copilot` | Réponse hybride avec citations vérifiées | RAG + graphe |
| `researcher` | Boucle de recherche bornée à trois actions | RAG + graphe |
| `architecture` | Modules, fichiers et symboles centraux | RAG + graphe |
| `documentation` | Réponses limitées à la documentation indexée | RAG |
| `impact` | Appelants directs et transitifs d'un symbole | graphe + RAG |
| `triage` | Catégorie, priorité et fichiers probables d'un ticket | heuristique + RAG + graphe |
| `review` | Synthèse des vulnérabilités, smells et doublons | findings + RAG |
| `test_plan` | Scénarios de tests sans exécution | RAG + graphe |

Chaque exécution enregistre le nom de l'agent, le modèle, la durée, le nombre de preuves
et les citations dans `agent_runs`. La page **MLOps** affiche ces métriques par agent, ce
qui permet de comparer plusieurs stratégies de recherche.

## Démarrage local

Prérequis : Docker, Python 3.11+, Node.js 22+, Ollama.

```bash
cp .env.example .env          # mots de passe PostgreSQL / Neo4j
docker compose up -d          # PostgreSQL (pgvector) + Neo4j
ollama pull qwen2.5-coder:1.5b  # 7b possible si GPU (plus lent sur CPU)
```

Backend :

```bash
cd backend
python -m venv .venv
# Windows : .venv\Scripts\activate
# Linux/macOS : source .venv/bin/activate
pip install -r requirements.txt
python dev.py
```

Frontend :

```bash
cd frontend
npm install
npm run dev
```

- Interface : http://localhost:5173
- API / Swagger : http://localhost:8000/docs
- Santé : http://localhost:8000/health
- Neo4j Browser : http://localhost:7474

PostgreSQL est exposé sur le port **5433** par le `docker-compose.yml` de développement
(`POSTGRES_PORT=5433` dans `.env`). Si le port diffère, ajuste `.env`.

Dans l'interface, ouvre **Dépôts**, colle une URL Git puis lance **Importer et indexer**.
L'ingestion analyse le code, collecte la documentation, classe les tickets, indexe le RAG,
construit le graphe et exécute les détecteurs. Le projet est ensuite consultable dans
Architecture, Code Intelligence, Documentation, Tickets et Incidents.

## Déploiement Docker (production)

```bash
cp .env.example .env          # définir des secrets robustes
docker compose -f docker-compose.prod.yml up -d --build
```

- Interface : http://localhost:8080 (`FRONTEND_PORT`)
- API : http://localhost:8000 (`BACKEND_PORT`)
- Nginx sert le frontend et relaie `/api` et `/health` vers le backend.
- PostgreSQL et Neo4j ne sont pas exposés sur l'hôte ; ils restent sur le réseau interne.
- Les dépôts ingérés sont conservés dans le volume `dkh_data`.
- Ollama n'est pas inclus : définis `OLLAMA_DOCKER_BASE_URL` (par défaut
  `http://host.docker.internal:11434`) vers une instance accessible depuis les conteneurs.
  `OLLAMA_BASE_URL` reste réservé au backend lancé hors Docker.
- Healthchecks : PostgreSQL, Neo4j, backend (vérifie Postgres et Neo4j) et frontend.

Pour arrêter sans perdre les données : `docker compose -f docker-compose.prod.yml down`.
Pour tout supprimer, ajoute `-v` (volumes compris).

## Tests et qualité

```bash
# Backend
cd backend
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\ruff.exe check app tests

# ML
cd ml
..\backend\.venv\Scripts\python.exe -m pytest tests -q
..\backend\.venv\Scripts\ruff.exe check src tests

# Frontend
cd frontend
npm run build
```

Sous Linux/macOS, remplace les chemins `.venv\Scripts\...` par `.venv/bin/...`.

## Pipeline ML

Les modèles et détecteurs sont dans `ml/src/dkh_ml/models/` :

| Composant | Rôle |
| --- | --- |
| `ticket_classifier` | Classification `BUG` / `FEATURE` / `TECHNICAL_DEBT` (TF-IDF + régression logistique) |
| `project_classifier` | Type de projet : application, library, service, full-stack |
| `vulnerability_detector` | Règles statiques + classifieur de risque |
| `code_smell` | Détection multi-langages des smells (méthode longue, nesting, etc.) |
| `clone_detector` | Similarité structurelle + tokens |
| `code_embeddings` | Embeddings de code légers pour la similarité |

Entraînement et évaluation (exemple PowerShell) :

```powershell
cd ml
$env:PYTHONPATH="src"
..\backend\.venv\Scripts\python.exe -m dkh_ml.models.ticket_classifier.train `
  --data tests/fixtures/tickets.jsonl --model models/ticket_classifier.joblib `
  --metrics reports/ticket_metrics.json
```

Les rapports sont écrits dans `ml/reports/`. Le pipeline DVC est décrit dans `ml/dvc.yaml`
(5 stages) et les hyperparamètres dans `ml/params.yaml`. Pour l'utiliser :

```bash
pip install -r requirements-dev.txt   # dvc, mlflow, scikit-learn, etc.
dvc repro
```

Les stages utilisent `PYTHONPATH=src` ; le package `ml` n'a pas besoin d'être installé.
MLflow est optionnel : `--mlflow` active le logging si `mlflow` est installé.

## API principale

- `GET /health`
- `POST /api/v1/projects`, `GET /api/v1/projects`
- `POST /api/v1/projects/{name}/ingest`, `POST .../ingest/zip`
- `GET /api/v1/projects/{name}`, `/status`, `/documents`, `/issues`, `/findings`,
  `/architecture`, `/graph`, `/files/{path}`
- `POST /api/v1/projects/{name}/ask`, `/feedback`
- `GET /api/v1/graph/{repo}/stats|symbols|calls|dependencies|impact`
- `GET/POST /api/v1/mlops/agent-runs|monitoring|models|quality|metrics`
- `GET /api/v1/agents/catalog`, `POST /api/v1/agents/ask|search|specialist`,
  `POST /api/v1/rag/index|search`

## Limites connues

- Embeddings par défaut : `hash` (rapide, sans dépendance) ; activer
  `sentence-transformers` pour une recherche sémantique réelle
  (`pip install -r backend/requirements-ml.txt`, puis `EMBEDDING_BACKEND`).
- Les détecteurs de vulnérabilités et de code smells sont statiques/heuristiques : ils
  signalent des candidats, pas des preuves. Les seuils sont dans les modules concernés.
- Le classifieur de tickets est entraîné sur un petit jeu de fixtures : les métriques
  servent de démonstration, pas de garantie en production.
- L'agent de recherche est volontairement borné (pas d'exécution de code, pas d'écriture).
- Le clone de dépôts et le stockage ZIP sont limités (taille, nombre de fichiers, chemins
  contrôlés) mais l'ingestion reste synchrone côté worker FastAPI.
- PostgreSQL/pgvector et Neo4j sont des services uniques : pas de haute disponibilité.

## Structure

```text
backend/       API FastAPI, parsing, graphe, RAG, détecteurs, MLOps
frontend/      React + Vite (pages Dépôts, Architecture, Code, Docs, Tickets, Incidents, MLOps)
ml/            modèles, entraînement, évaluation, DVC, rapports
infra/         init PostgreSQL, emplacements Kubernetes/Terraform
docs/          architecture, guides, ADR
pipelines/     orchestration
monitoring/    dashboards et configuration d'observabilité
evaluation/    jeux d'évaluation
tests/         tests transverses
```
