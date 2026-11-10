# LedgerMind — Team Starter

A shared starting repository for a 4-person team building a GST reconciliation AI agent with persistent Hindsight memory.

## Current application
The existing MVP runs from the repository root:
```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload
```
Open http://127.0.0.1:8000

Do not commit `.env`, API keys, virtual environments, database files, or personal data.

## Team ownership
| Person | Branch | Ownership |
|---|---|---|
| 1 | `frontend` | `templates/`, `static/`, `frontend/` |
| 2 | `backend` | `main.py`, `integrations.py`, `backend/`, database/API integration |
| 3 | `gst-engine` | `gst_engine/`, `datasets/`, reconciliation logic |
| 4 | `ai-agent` | `ai_agent/`, Hindsight, LLM and agent tools |

The existing MVP files are a shared baseline. Coordinate before editing the same file. Person 2 owns integration of modules into the FastAPI app; each module owner should expose functions with agreed interfaces rather than independently changing API routes.

## First-time setup for every teammate
1. Install Git and VS Code.
2. Accept the GitHub repository invitation.
3. Clone the repository:
   `git clone <YOUR_GITHUB_REPOSITORY_URL>`
4. Enter the folder:
   `cd LedgerMind`
5. Switch to your assigned branch:
   `git switch <your-branch>`
6. Create your Python environment and install dependencies using the commands above.

The team leader must create and push the four branches once:
```bash
git switch main
git pull origin main
git switch -c frontend
git push -u origin frontend
git switch main
git switch -c backend
git push -u origin backend
git switch main
git switch -c gst-engine
git push -u origin gst-engine
git switch main
git switch -c ai-agent
git push -u origin ai-agent
```
If a branch already exists, use `git switch <branch>` instead of creating it again.

## Daily Git workflow
Before working:
```bash
git switch <your-branch>
git pull origin <your-branch>
```
After making changes:
```bash
git status
git add <your-files>
git commit -m "Describe the change"
git push origin <your-branch>
```
When a task is ready, open a Pull Request on GitHub from your branch into `main`. Ask another teammate to review it. Merge only after the app still runs and the relevant checks pass.

To bring the latest integrated work into your branch:
```bash
git fetch origin
git merge origin/main
```
Resolve conflicts carefully; do not blindly accept one side.

## Shared API/data contract
Use the common CSV columns:
`month,vendor,gstin,invoice,invoice_date,taxable,tax`

A reconciliation issue should use this shape (field names are the agreed contract; values below are illustrative):
```json
{
  "month": "2026-10",
  "vendor": "Example Traders",
  "gstin": "29ABCDE1234F1Z5",
  "invoice": "INV-001",
  "issue": "GSTIN mismatch",
  "detail": "Supplier GSTIN differs",
  "risk": 12500.0,
  "status": "unresolved"
}
```
GST engine functions should return Python dictionaries using these keys. Backend owns HTTP routes and database writes. AI agent receives issue dictionaries plus recalled Hindsight context and returns recommendations/drafts. Frontend consumes backend JSON APIs; it must not call Hindsight or LLM APIs directly.

## Suggested interfaces
- GST engine: `reconcile(purchase_rows, gstr2b_rows) -> list[dict]`
- AI agent: `review_exception(issue: dict, vendor_context: list[str]) -> dict`
- Backend: validates files, calls GST engine and agent, persists results and exposes APIs.
- Frontend: displays API results and submits user-approved actions.

These are integration contracts, not all implemented modules yet. Coordinate changes in a short team meeting before changing function signatures.

## Important product boundaries
- Hindsight is the required persistent agent memory technology for the hackathon. Do not claim SQLite vendor profile fields are Hindsight.
- Band AI desktop must be installed and used separately as required by organisers; it is not an embedded website feature.
- Groq is optional/recommended. Keep model calls on the backend and secrets in environment variables.
- Current MVP uses demo/synthetic data. It does not connect to GSTN, fetch live GSTR-2B, file returns, or send emails/WhatsApp messages.
- GST/ITC decisions must be reviewed by a qualified finance/tax professional. Clearly label estimates and require human approval for external actions.

## Project map
- `main.py`, `templates/`, `static/`: current FastAPI MVP.
- `integrations.py`: Hindsight and Groq adapters.
- `frontend/`: frontend team's notes and new modular UI code.
- `backend/`: backend team's notes and service modules.
- `gst_engine/`: reconciliation engine work.
- `ai_agent/`: agent and memory work.
- `datasets/`: synthetic CSV files only.
- `tests/`: automated tests.
- `docs/`: architecture, API contracts and team decisions.
