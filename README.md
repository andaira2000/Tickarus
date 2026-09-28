# Tickarus

AI-enhanced issue-tracking platform. Tickarus augments a standard ticketing workflow with semantic duplicate detection, LLM-powered root-cause analysis grounded in GitHub commit history, an AI chat assistant, and automatic tagging/prioritisation.

**Live demo:** [tickarus.vercel.app](https://tickarus.vercel.app)

## Demo video

https://github.com/andaira2000/Tickarus/releases/download/demo-v1/Demo.mp4

## Features

| Feature | Description |
|---|---|
| Ticket management | Create, assign, and track tickets through a full lifecycle (`open → in_progress → in_review → resolved / blocked / on_hold → closed`) with priority levels, tags, and comments. |
| Teams | Organize tickets and members by team. |
| AI similarity search | Sentence-transformer (BERT) embeddings surface likely duplicate/related tickets. |
| AI root-cause analysis | An LLM (Anthropic Claude or OpenAI) reasons over ticket context and linked GitHub commit history to suggest probable root causes. |
| AI chat assistant | Conversational assistant scoped to ticket context. |
| Auto-tagging | Automatic tag and priority suggestions for new tickets. |
| GitHub integration | Link repositories and commits to tickets via webhooks. |
| Evaluation framework | Built-in endpoints/services for measuring AI feature quality (accuracy@k, precision/recall, human-vs-AI rating comparisons); see [`overall_evaluation.md`](overall_evaluation.md) for a summary of results. |

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS, Radix UI, TanStack Query, Zustand |
| Backend | FastAPI, Pydantic v2, Mangum (Lambda adapter) |
| Database & Auth | Supabase (Postgres + Auth) |
| AI / ML | Anthropic Claude / OpenAI, `sentence-transformers` (MiniLM embeddings), scikit-learn |
| Integrations | GitHub API (`githubkit`) |
| Infrastructure | Docker, AWS Lambda (container image), AWS ECR, AWS CodeBuild |
| CI/CD | GitHub Actions → CodeBuild → Lambda |

## Project structure

```
Tickarus/
├── backend/
│   ├── app/
│   │   ├── api/routes/        # auth, tickets, teams, comments, tags, ai_chat, github, evaluation
│   │   ├── models/            # Pydantic models (ticket, team, user, comment, tag, ...)
│   │   ├── services/          # business logic: similarity, root-cause, auto-tagging, AI chat, GitHub, evaluation
│   │   ├── db/                # Supabase client setup
│   │   ├── config.py          # environment-driven settings
│   │   ├── main.py            # FastAPI app + lifespan (DB, embeddings, LLM provider)
│   │   └── lambda_handler.py  # AWS Lambda entrypoint (Mangum)
│   ├── migrations/            # SQL migrations
│   ├── Dockerfile             # Lambda container image
│   └── docker-compose.yml     # local dev container
├── frontend/
│   ├── app/                   # Next.js App Router: (auth) login/register, (dashboard) tickets/teams
│   ├── components/            # UI components (shadcn/Radix-based)
│   └── lib/                   # API client, store, shared types
└── overall_evaluation.md      # AI feature evaluation results
```

## Getting started

### Prerequisites

- Node.js 20+
- Python 3.11
- A [Supabase](https://supabase.com) project (URL + anon key + service role key)
- An Anthropic and/or OpenAI API key (optional — falls back to a mock LLM provider if omitted)
- A GitHub personal access token (optional, needed for GitHub integration)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # fill in your own values — see Configuration below
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`, with interactive docs at `http://localhost:8000/docs`.

Alternatively, run it in Docker:

```bash
cd backend
docker compose up --build
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # fill in your own values — see Configuration below
npm run dev
```

The app will be available at `http://localhost:3000`.

## Environment variables

Both apps read configuration from `.env` (backend) / `.env.local` (frontend) files that are **not committed to the repo** — copy the `.env.example` files below and fill in your own values.

**Backend** (`backend/.env`):

| Variable | Description | Default |
|---|---|---|
| `SUPABASE_URL` | Supabase project URL | — |
| `SUPABASE_KEY` | Supabase anon/public key | — |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | — |
| `GITHUB_TOKEN` | GitHub personal access token | — |
| `GITHUB_ORG_NAME` | GitHub organization to integrate with | `tickarus-demo-org` |
| `GITHUB_WEBHOOK_SECRET` | Secret for verifying GitHub webhooks | — |
| `LLM_PROVIDER` | `anthropic`, `openai`, or unset for a mock provider | `anthropic` |
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `ANTHROPIC_MODEL` | Anthropic model name | `claude-3-haiku-20240307` |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `OPENAI_MODEL` | OpenAI model name | `gpt-3.5-turbo` |

**Frontend** (`frontend/.env.local`):

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_URL` | Base URL of the deployed/cloud backend API |
| `NEXT_PUBLIC_LOCALHOST_URL` | Base URL of the local backend API (e.g. `http://localhost:8000`) |
| `NEXT_PUBLIC_USE_CLOUD_API` | `true`/`false` — toggles which of the above the frontend calls |

## Deployment

- **Frontend** — deployed on [Vercel](https://tickarus.vercel.app).
- **Backend** — ships as a Docker image built from `backend/Dockerfile` (AWS Lambda base image) and deployed as a container-image Lambda function behind API Gateway. On every push to `main`, the [`deploy.yml`](.github/workflows/deploy.yml) GitHub Actions workflow assumes an AWS role via OIDC and triggers an AWS CodeBuild project ([`buildspec.yml`](backend/buildspec.yml)), which builds the image, pushes it to ECR, and updates the Lambda function.
