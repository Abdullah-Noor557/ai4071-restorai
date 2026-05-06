# RestorAI - Furniture Restoration Multi-Agent System

> **Author**: Abdullah Noor (2022029)
> **Course**: AI407L - AI Lab
> **Domain**: Furniture restoration & multi-agent systems

End-to-end AI agent that walks a user from "I have an old water-damaged
dresser" to a complete restoration plan, shopping list, and safety
constraints. Built across the AI407L lab series (Lab 2 -> OEL):

| Layer        | Technology                                     | Submission |
|--------------|------------------------------------------------|------------|
| Knowledge    | ChromaDB + OpenAI embeddings (RAG)             | Lab 2      |
| Reasoning    | LangGraph ReAct loop + Pydantic-validated tools | Lab 3     |
| Persistence  | LangGraph SQLite checkpointer (HITL ready)     | Lab 5 / Mid-exam |
| API          | FastAPI + Server-Sent Events streaming         | Lab 4      |
| Deployment   | Multi-stage Docker + docker-compose            | OEL        |
| CI / Quality | GitHub Actions evaluation gate                 | OEL        |

---

## 1. Repository layout

```
.
├── app/                      # Maintained Python package
│   ├── agent/                #   LangGraph state machine + tools (Lab 3)
│   ├── api/                  #   FastAPI service (Lab 4)
│   ├── eval/                 #   Headless evaluation harness (OEL)
│   └── ingestion/            #   Knowledge-base loader (Lab 2)
│
├── data/
│   ├── restoration_guides/   #   Source documents for the RAG pipeline
│   └── checkpoints.sqlite    #   (runtime, gitignored) - chat history
├── chroma_db/                #   (runtime, gitignored) - vector index
│
├── lab4_api/                 # Lab 4 submission package
│   ├── README.md             #   - what / how / why
│   ├── schema.py             #   - Pydantic models (re-export)
│   ├── main.py               #   - FastAPI app  (re-export)
│   ├── smoke_test.py         #   - end-to-end test client
│   ├── test_api.py           #   - minimal demo client
│   └── api_test_results.txt  #   - captured run output + curl appendix
│
├── oel_deployment/           # OEL Task 1 submission package
│   ├── REPORT.md             #   - written justification
│   ├── Dockerfile            #   - copy of /Dockerfile
│   ├── docker-compose.yml    #   - copy of /docker-compose.yml
│   ├── dockerignore.txt      #   - copy of /.dockerignore
│   └── env.example.txt       #   - copy of /.env.example
│
├── oel_quality_gates/        # OEL Task 2 submission package
│   ├── REPORT.md             #   - written justification
│   ├── run_eval.py           #   - copy of /run_eval.py
│   ├── eval_thresholds.json  #   - copy of /eval_thresholds.json
│   ├── workflow_main.yml     #   - copy of /.github/workflows/main.yml
│   └── breaking_change_demo/ #   - red/green eval_results.json + diff
│
├── tests/                    # Fast, hermetic tests (no LLM, no network)
│   └── test_schema.py
│
├── archive/                  # Earlier-lab artefacts kept for context
│   ├── lab2/                 #   (Lab 2 docs)
│   ├── lab3/                 #   (original Lab 3 folder)
│   └── mid_exam_submission/  #   (Mid-exam folder, untouched)
│
├── .github/workflows/main.yml # Real CI workflow
├── Dockerfile                 # Real image build
├── docker-compose.yml         # Real two-service stack
├── .dockerignore
├── .gitignore
├── .env.example               # Template for runtime secrets
├── eval_thresholds.json       # Versioned quality thresholds (OEL)
├── ingest_data.py             # Lab 2 ingestion (kept at root for back-compat)
├── requirements.txt           # Pinned dependency set
├── run_eval.py                # CI entry-point for the quality gate
└── README.md                  # this file
```

---

## 2. Quick start (local development)

```powershell
# 1. Create a virtual environment and install deps
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Provide secrets
Copy-Item .env.example .env       # then edit .env and paste your real keys
$env:OPENAI_API_KEY = "sk-..."     # or load .env via your shell tooling

# 3. Build the knowledge base (one-time)
python ingest_data.py

# 4. Start the API
$env:CHECKPOINT_DB_PATH = "$PWD\data\checkpoints.sqlite"
python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000

# 5. In another terminal: smoke-test it
python lab4_api/smoke_test.py
```

The interactive Swagger UI is at <http://localhost:8000/docs>.

---

## 3. Quick start (Docker / production)

```bash
cp .env.example .env       # add your real OPENAI_API_KEY
docker compose up --build  # ~ 2 min cold build, < 30 s warm rebuilds
curl http://localhost:8000/health
# -> {"status":"ok","checkpointer":"ok","knowledge_base":"ok",...}
```

`docker compose down` stops the stack; `docker compose down -v` also drops
volumes (use only when you want a full reset). Conversation history and
the vector index survive normal restarts because they live on named
volumes (see `oel_deployment/REPORT.md` section 3).

---

## 4. Running the quality gate

```bash
export OPENAI_API_KEY=sk-...
python run_eval.py        # exit 0 = pass, 1 = fail, 2 = bootstrap error
```

The CI runs the same command on every push to `main`; see
`.github/workflows/main.yml` and `oel_quality_gates/REPORT.md`.

---

## 5. Submission map

| Lab / Task                              | Where to look                                  |
|-----------------------------------------|------------------------------------------------|
| Lab 4 - API Layer                       | `lab4_api/` and `app/api/`                     |
| OEL - Industrial Packaging & Deployment | `oel_deployment/` and `Dockerfile` / `docker-compose.yml` |
| OEL - Automated Quality Gates           | `oel_quality_gates/` and `.github/workflows/main.yml` |
| Lab 3 - Reasoning Loop (prereq)         | `app/agent/` (refactored from `archive/lab3/`) |
| Lab 5 - Persistence (prereq)            | `app/api/main.py::lifespan` (AsyncSqliteSaver) |
| Mid-exam - HITL                         | `archive/mid_exam_submission/`                 |
| Lab 2 - Knowledge ingestion (prereq)    | `ingest_data.py` + `data/restoration_guides/`  |

Each submission folder contains its own `REPORT.md` / `README.md` with
the rubric mapping for that specific deliverable.

---

## 6. Useful commands

```bash
# Run only the fast hermetic tests (CI-safe)
pytest tests/

# Open the FastAPI docs
# http://localhost:8000/docs

# Inspect the SqliteSaver checkpoint store
python -c "import sqlite3,pprint; c=sqlite3.connect('data/checkpoints.sqlite'); pprint.pprint(c.execute('select thread_id,count(*) from checkpoints group by thread_id').fetchall())"

# Re-build the knowledge base inside the running container
docker compose exec agent python -m app.ingestion.ingest_data
```
