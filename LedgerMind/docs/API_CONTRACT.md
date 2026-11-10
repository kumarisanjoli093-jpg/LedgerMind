# Shared API contract (initial)

Agree changes in the team before implementation.

## Upload
`POST /api/upload/purchase` and `POST /api/upload/gstr2b` accept CSV files with columns `month,vendor,gstin,invoice,invoice_date,taxable,tax`.

## Issues
`GET /api/issues` returns reconciliation issue records. Keep a stable shape:
`month, vendor, gstin, invoice, issue, detail, risk, status`.

## Agent
`POST /api/run-agent` triggers analysis/recommendation generation. It must not send external messages automatically. Return counts and status, not secrets or raw credentials.

## Integration rule
Frontend calls FastAPI. FastAPI calls the GST engine and AI agent. Only the backend communicates with Hindsight and the LLM provider.
