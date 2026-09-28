<h1 align="center">🎫 Tickarus</h1>

<p align="center">
  An <strong>AI-enhanced issue tracker</strong> for software teams.<br>
  It spots duplicates while you type, suggests tags and priority, and explains why a build broke by reading the commits behind it.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Next.js_15-000000?style=for-the-badge&logo=nextdotjs&logoColor=white" alt="Next.js 15">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white" alt="Supabase">
  <img src="https://img.shields.io/badge/Claude_%2F_OpenAI-D97757?style=for-the-badge&logo=anthropic&logoColor=white" alt="Anthropic Claude or OpenAI">
</p>

<p align="center">
  <a href="https://tickarus.vercel.app"><img src="https://img.shields.io/badge/▶-tickarus.vercel.app-7B3FE4?style=flat&labelColor=555555" alt="Live demo on Vercel"></a>
</p>

https://github.com/user-attachments/assets/c4517a44-03dc-48db-a2c4-48304253e8e1

<p align="center"><sub>Write a ticket, see its likely duplicates, ask the AI why it happened. <a href="https://tickarus.vercel.app">Try it yourself →</a></sub></p>

## Try it

Open **New ticket** and start typing a title. After half a second of no typing, Tickarus lists the five most similar tickets from every team, so you can see if the bug has already been reported. Once you've written a few words, it also suggests tags and a priority. Open any ticket and hit **AI analysis** for a probable root cause, or ask the chat assistant about it.

```bash
git clone https://github.com/andaira2000/Tickarus.git
cd Tickarus
```

<p align="center"><sub>FastAPI on <code>:8000</code>, Next.js dashboard on <code>:3000</code>. Setup details are in <a href="#quick-start">Quick Start</a>.</sub></p>

## What it does for you

**When you report a bug:**

- **Has someone already reported this?** As you type, the title and description are embedded with a sentence-transformer model (`all-MiniLM-L6-v2`) and compared against every existing ticket. The closest five appear with a similarity score, their team and their status.
- **How should I label it?** Auto-tagging compares your text with descriptions of common categories (API, database, UI, performance, security…) and suggests the tags that match, plus a priority from `low` to `critical`.
- **Who should see it?** Tickets belong to a team and can be assigned to a member. Anyone can **watch** a ticket to follow it.

**When you work on a bug:**

- **Why is this happening?** **AI analysis** sends the ticket, its latest comments and similar *resolved* tickets to an LLM. You get a probable root cause, a confidence score and a list of next steps. You can rate the answer as helpful or not.
- **I have follow-up questions.** Each ticket has an AI chat. The assistant sees the ticket, its comments and the last 10 messages of the conversation.
- **What's on my plate?** **My tickets** lists what you created or were assigned. The ticket list filters by team, status, priority, assignee, tag, commenter and free-text search.

**When CI breaks:**

- **Nobody noticed the red build.** Point a GitHub `workflow_run` webhook at Tickarus. When a workflow fails, it opens a `high` priority ticket for the repository's team, tags it `ci-failure` and `automated`, and attaches the workflow logs.
- **Which commit did it?** A few seconds later, the AI assistant posts a root-cause comment on that ticket. It has read the failure logs, the recent commits and their changed files, and names the commits most likely to be responsible.

## What it will not do

- **Invent an answer when the LLM is down.** If the LLM call fails or no API key is set, root-cause analysis falls back to keyword pattern matching and labels the result `Pattern-based`, with a lower confidence.
- **Pretend to be certain.** Every analysis shows its confidence as High, Medium or Low. The evaluation found the model tends to be overconfident, so treat it as a starting point.
- **Hide who did what.** Tickets and comments record an *actor*: a person, the CI bot or the AI assistant. Automated work is never attributed to a human.
- **Let AI change your ticket behind your back.** Tag and priority suggestions are only suggestions. You choose which ones to apply.
- **Store passwords.** Sign-up and login go through Supabase Auth, and every API call carries a Supabase JWT.

## Features

| Feature                    | Description                                                                                                                                 |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **Ticket Lifecycle**       | `open → in_progress → in_review → resolved / blocked / on_hold → closed`, with priority, assignee, tags, comments and watchers            |
| **Duplicate Detection**    | MiniLM embeddings + cosine similarity return the top 5 related tickets while the ticket is being written                                    |
| **AI Root-Cause Analysis** | LLM analysis grounded in comments, similar resolved tickets and, for CI failures, GitHub commit history and workflow logs                    |
| **AI Chat Assistant**      | A chat session per ticket, stored in Supabase, with ticket context and conversation history                                                   |
| **Auto-Tagging**           | Semantic tag suggestions (threshold 0.3) and a hybrid semantic + keyword priority suggestion                                                  |
| **CI Failure Tickets**     | A GitHub webhook turns failed workflow runs into tagged, high-priority tickets with an automatic AI analysis comment                         |

<details>
<summary><b>Everything else it does</b></summary>

| Feature                    | Description                                                                                                       |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Teams**                  | Create teams, add members, and give them a `manager` or `member` role                                               |
| **Pluggable LLM**          | `LLM_PROVIDER=anthropic` or `openai`. Without a key, a mock provider keeps the app working                           |
| **AI Usage Metrics**       | Every AI call is logged to `ai_metrics` with its response time, plus clicks on suggestions and ratings of analyses   |
| **Evaluation Endpoints**   | Measure similarity (accuracy@k, precision, recall), tagging (F1, priority accuracy) and performance under load       |
| **Synthetic Test Data**    | `POST /api/evaluation/generate-test-data` seeds tickets for evaluation runs                                          |
| **Interactive API Docs**   | Swagger UI at `/docs` and ReDoc at `/redoc`                                                                          |
| **Serverless Backend**     | The same FastAPI app runs locally with Uvicorn and on AWS Lambda through Mangum                                     |

</details>

## Does the AI actually help?

Tickarus was built as a research project, and each AI feature was measured. The full write-up is in [`overall_evaluation.md`](overall_evaluation.md).

| Question                                     | Result                                                                                 |
| -------------------------------------------- | -------------------------------------------------------------------------------------- |
| Is the real duplicate in the top 3?          | **65.4%** of the time (accuracy@3)                                                     |
| Is the root-cause analysis any good?         | **86.7%** of analyses were within 1 point of a human rating on a 1–5 scale              |
| How does it hold up under load?              | **0% errors** at every level tested. Peak 3.48 req/s at 25 concurrent users. Slows down beyond that |
| Are the auto-tags right?                     | Not yet. Tag F1 is **0.11** and priority accuracy is **40%**. This is the weakest feature |

## Quick Start

You need **Python 3.11**, **Node.js 20+** and a **Supabase** project (URL, anon key, service role key). An **Anthropic** or **OpenAI** API key and a **GitHub** personal access token are optional.

```bash
# 1. Backend
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure it
cp .env.example .env              # fill in your values (see below)

# 3. Start the API (the embedding model downloads on the first run)
uvicorn app.main:app --reload --port 8000     # docs at http://localhost:8000/docs

# 4. Frontend (separate terminal)
cd frontend
npm install
cp .env.local.example .env.local
npm run dev                       # http://localhost:3000
```

Prefer Docker for the backend? Run `docker compose up --build` inside `backend/`.

<details>
<summary><b>Environment variables</b></summary>

**`backend/.env`**

```bash
# Supabase
SUPABASE_URL=
SUPABASE_KEY=                     # anon / public key
SUPABASE_SERVICE_KEY=             # service role key

# GitHub integration (optional)
GITHUB_TOKEN=
GITHUB_ORG_NAME=tickarus-demo-org
GITHUB_WEBHOOK_SECRET=

# LLM provider: anthropic, openai, or empty for the mock provider
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-3-haiku-20240307
OPENAI_API_KEY=
OPENAI_MODEL=gpt-3.5-turbo
```

**`frontend/.env.local`**

```bash
NEXT_PUBLIC_API_URL=                          # deployed backend
NEXT_PUBLIC_LOCALHOST_URL=http://localhost:8000
NEXT_PUBLIC_USE_CLOUD_API=false               # true → use NEXT_PUBLIC_API_URL
```

</details>

## How It Works

**Writing a ticket**

```
User types a title + description
        │  (500 ms debounce)
        ├──────────────────────────────┐
        ▼                              ▼
POST /api/tickets/similar       POST /api/tickets/auto-tag
MiniLM embedding                 Embedding vs. tag descriptions
cosine similarity vs.            + priority (semantic, keyword fallback)
every ticket                           │
        │                              ▼
        ▼                        Suggested tags + priority
Top 5 related tickets            (user picks what to keep)
        │
        ▼
POST /api/tickets  →  Supabase (actor = the human user)
```

**A failed CI run**

```
GitHub workflow_run (conclusion: failure)
        │
        ▼
POST /api/github/webhooks/ci-failure
        │
        ├─▶ Save CI failure + workflow logs
        ├─▶ Create ticket (priority: high, actor: CI bot)
        ├─▶ Tag: ci-failure, automated, <repo>, <language>
        │
        ▼  (background task)
Root-cause analysis
  ticket + comments + similar resolved tickets
  + recent commits, changed files, logs
        │
        ▼
LLM (Claude / OpenAI)  ──fails──▶  pattern matching
        │
        ▼
Comment posted on the ticket by the AI assistant
```

## Deployment

```
            ┌──────────────────────┐
 Browser ──▶│  Vercel              │  Next.js frontend
            │  tickarus.vercel.app │
            └──────────┬───────────┘
                       │ HTTPS
            ┌──────────▼───────────┐
            │  API Gateway         │
            │  AWS Lambda          │  FastAPI in a container image (Mangum)
            └──────────┬───────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   Supabase         Claude /        GitHub API
   (Postgres+Auth)  OpenAI
```

- **Frontend:** deployed on Vercel from the `frontend/` directory.
- **Backend:** every push to `main` runs [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml). It assumes an AWS role through OIDC and starts a CodeBuild project, which follows [`backend/buildspec.yml`](backend/buildspec.yml) to build the image, push it to Amazon ECR and update the Lambda function.
- **Container:** [`backend/Dockerfile`](backend/Dockerfile) uses the AWS Lambda Python base image and downloads the sentence-transformer model at build time, so cold starts don't fetch it.
- **Secrets:** no AWS keys are stored in GitHub. The workflow uses OIDC with an IAM role.

## API

All endpoints except health checks, register, login and the GitHub webhook need `Authorization: Bearer <Supabase JWT>`.

```
GET    /health                                     → Health check

POST   /api/auth/register                          → Create an account
POST   /api/auth/login                             → Sign in, returns a Supabase session
GET    /api/auth/me                                → Current user

GET    /api/tickets                                → List (filters, search, pagination)
POST   /api/tickets                                → Create a ticket
GET    /api/tickets/{id}                           → Ticket details
PATCH  /api/tickets/{id}                           → Update status, priority, assignee...
POST   /api/tickets/{id}/tags                      → Add tags
DELETE /api/tickets/{id}/tags                      → Remove tags
POST   /api/tickets/{id}/watch                     → Watch a ticket
DELETE /api/tickets/{id}/watch                     → Stop watching

POST   /api/tickets/similar                        → Find related tickets
POST   /api/tickets/auto-tag                       → Suggest tags + priority
POST   /api/tickets/{id}/ai-analysis               → AI root-cause analysis
POST   /api/tickets/{id}/ai-analysis/rate          → Rate an analysis
POST   /api/tickets/similarity-click               → Log a click on a suggestion

POST   /api/comments                               → Add a comment
GET    /api/comments/ticket/{ticket_id}            → Comments on a ticket
PATCH  /api/comments/{id}                          → Edit a comment
DELETE /api/comments/{id}                          → Delete a comment

GET    /api/tags                                   → All tags
POST   /api/tags                                   → Create a tag
GET    /api/tags/popular                           → Most used tags

GET    /api/teams                                  → All teams
POST   /api/teams                                  → Create a team
PATCH  /api/teams/{id}                             → Update a team's name or description
GET    /api/teams/{id}/members                     → Team members
POST   /api/teams/{id}/members/{user_id}           → Add a member
PATCH  /api/teams/{id}/members/{user_id}           → Change a member's role
DELETE /api/teams/{id}/members/{user_id}           → Remove a member

POST   /api/ai-chat/sessions                       → Start a chat on a ticket
GET    /api/ai-chat/sessions                       → My chat sessions
GET    /api/ai-chat/sessions/{id}                  → Session with messages
POST   /api/ai-chat/sessions/{id}/messages         → Send a message, get a reply
GET    /api/ai-chat/sessions/{id}/messages         → Message history
POST   /api/ai-chat/sessions/{id}/close            → Close a session
GET    /api/ai-chat/tickets/{ticket_id}/sessions   → Chats on a ticket

GET    /api/github/health                          → GitHub connection check
GET    /api/github/repositories                    → Linked repositories
POST   /api/github/repositories                    → Link a repository to a team
GET    /api/github/repositories/{owner}/{repo}     → One repository
POST   /api/github/webhooks/ci-failure             → GitHub workflow_run webhook

POST   /api/evaluation/similarity                  → Evaluate duplicate detection
POST   /api/evaluation/tagging                     → Evaluate auto-tagging
POST   /api/evaluation/performance                 → Load test
POST   /api/evaluation/generate-test-data          → Seed synthetic tickets
```

## Project Structure

```
Tickarus/
├── .github/workflows/deploy.yml      # OIDC → CodeBuild → Lambda
├── overall_evaluation.md             # AI evaluation results
├── backend/                          # FastAPI
│   ├── Dockerfile                    # Lambda container image
│   ├── buildspec.yml                 # CodeBuild: build, push to ECR, update Lambda
│   ├── docker-compose.yml            # Local container
│   ├── requirements.txt
│   ├── migrations/                   # Supabase SQL: GitHub, actors, AI metrics, chat, evaluation
│   └── app/
│       ├── main.py                   # App, routers, startup (embeddings + LLM provider)
│       ├── lambda_handler.py         # Mangum entrypoint
│       ├── config.py                 # Settings from .env
│       ├── api/routes/               # auth, tickets, comments, tags, teams, ai_chat, github, evaluation
│       ├── models/                   # Pydantic models
│       └── services/
│           ├── similarity_service.py     # Embeddings + cosine similarity
│           ├── auto_tagging_service.py   # Tag + priority suggestions
│           ├── rootcause_service.py      # LLM analysis + pattern fallback
│           ├── ai_chat_service.py        # Ticket chat
│           ├── ai_automation_service.py  # Posts analysis comments on CI tickets
│           ├── github_service.py         # Webhooks, commits, logs
│           ├── llm_interface.py          # Anthropic / OpenAI / mock providers
│           └── evaluation_service.py
└── frontend/                         # Next.js 15 (Vercel)
    ├── app/
    │   ├── (auth)/                   # login, register
    │   └── (dashboard)/              # dashboard, tickets, tickets/new, tickets/my, tickets/[id], teams
    ├── components/ui/                # ticket-creator, similarity-suggestions, auto-tagging, ai-analysis, ai-chat
    └── lib/                          # API client, Zustand store, types
```

## Tech Stack

![Next.js](https://img.shields.io/badge/Next.js-000?style=flat-square&logo=nextdotjs&logoColor=white)
![React](https://img.shields.io/badge/React_19-20232A?style=flat-square&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)
![Radix UI](https://img.shields.io/badge/Radix_UI-161618?style=flat-square&logo=radixui&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python_3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=flat-square&logo=supabase&logoColor=white)
![Anthropic](https://img.shields.io/badge/Claude-D97757?style=flat-square&logo=anthropic&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat-square&logo=openai&logoColor=white)
![Hugging Face](https://img.shields.io/badge/sentence--transformers-FFD21E?style=flat-square&logo=huggingface&logoColor=black)
![GitHub](https://img.shields.io/badge/GitHub_API-181717?style=flat-square&logo=github&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![AWS Lambda](https://img.shields.io/badge/AWS_Lambda-FF9900?style=flat-square&logo=awslambda&logoColor=white)
![Vercel](https://img.shields.io/badge/Vercel-000?style=flat-square&logo=vercel&logoColor=white)

- **Frontend**: Next.js 15 (App Router) + React 19 + TypeScript + Tailwind CSS + Radix UI, hosted on Vercel
- **State & data**: TanStack Query + Zustand
- **Backend**: FastAPI + Pydantic v2, Mangum for Lambda
- **Database & auth**: Supabase (Postgres + Auth)
- **Embeddings**: `sentence-transformers` (`all-MiniLM-L6-v2`) + scikit-learn cosine similarity
- **LLM**: Anthropic Claude or OpenAI, with a mock fallback
- **GitHub**: `githubkit` for commits, workflow logs and repository context
- **Infrastructure**: Docker, AWS Lambda + API Gateway, Amazon ECR, AWS CodeBuild, GitHub Actions (OIDC)

## FAQ

**Do I need an LLM API key to run it?**
No. Without one, the backend uses a mock provider. Duplicate detection and auto-tagging still work because they run locally on the embedding model. Root-cause analysis falls back to pattern matching.

**Why is the first start so slow?**
On startup the backend downloads the MiniLM model (the first time only) and computes an embedding for every existing ticket. The Docker image bakes the model in, so this only costs time locally.

**How do I get CI failures turned into tickets?**
1. Link the repository to a team with `POST /api/github/repositories`.
2. In the GitHub repository settings, add a webhook for **Workflow runs** that points to `https://<your-backend>/api/github/webhooks/ci-failure`.
3. Set `GITHUB_TOKEN` so the backend can read logs and commits.

Only runs with `conclusion: failure` create a ticket. Repositories without a team are ignored.

**The analysis says "Pattern-based". Why?**
The LLM wasn't reachable: the key is missing, `LLM_PROVIDER` doesn't match the key you set, or the provider returned an error. Check the backend logs.

**Similar tickets never show up.**
Check that the frontend points at the backend you're running (`NEXT_PUBLIC_USE_CLOUD_API`), that you're signed in, and that there are tickets in the database to compare against.
