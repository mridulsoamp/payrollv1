# Payroll AI Agent V2 (demo)

V2 is an extension of the supplied V1 project. It fixes the Playwright Sync API-in-asyncio error by using `playwright.async_api` throughout FastAPI endpoints. It includes CSV/XLSX import, effective-dated rule records, deterministic payroll calculations, plain-English change proposals, SQLite-persisted payroll approval state, and five CSV exports.

## Run on macOS

Prerequisites: Python 3.10+ recommended (V1's Python 3.9 environment may work, but use Python 3.11/3.12 for a clean V2 environment), and Docker Horilla running at `http://localhost:8000`.

```bash
cd ~/Downloads/payroll-ai-agent-v2
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
uvicorn app.main:app --reload --port 8001
```

Open http://localhost:8001. Load synthetic demo data or upload CSV/XLSX. Open the Horilla browser, log in manually, navigate to a page with HTML tables and capture. Capture currently reads visible table headers/rows and page text; it does **not** automatically infer all Horilla-specific employee/pay/leave fields or directly import a capture into payroll. Review and map those fields before using the spreadsheet template.

## Spreadsheet schema

Required: `employee_code, employee_name, basic`. Optional: `state, hra, allowances, unpaid_leave_days, tds, other_deductions`. `sample_data/employees.csv` is the sample.

## AI boundary

The V2 instruction interpreter is a transparent, deterministic proposal parser (not an LLM). It supports clear commands for unpaid-leave divisor (actual month days / 30 / 26 working days), PF wage basis (first ₹15,000 or full basic), and dated rules. It never calculates payroll. A user must review and approve the proposal. Payroll arithmetic uses Python `Decimal`, a versioned rules snapshot and per-line formula/inputs/reason. Identical inputs and rules produce identical results.

## Rules and demo assumptions

Rules are stored in SQLite with `effective_from`. Company choices: `lop_basis` and `pf_basis`. Demo statutory parameters include employee PF rate, ESI rate/ceiling and a Karnataka PT threshold/amount. **These seeded values are illustrative demo defaults, not legal advice or a claim of current statutory compliance.** Add/maintain actual jurisdiction-specific rates, thresholds, exemptions, wage definitions, rounding and effective dates only after verification by payroll/legal experts. TDS is an imported employee monthly amount in this demo; no tax-regime computation is implemented. PF/ESI/PT/TDS CSVs are output files only; no payment is initiated. No government IDs are collected.

## Workflow durability

Calculated runs, immutable rule snapshots, results, maker/checker names and statuses are persisted in `data/payroll_v2.db`. Pending approval remains pending after restarting the FastAPI process. The demo uses named maker/checker actions, not production authentication/authorization. Approved run exports are gated until approval.

## Current limitations / next work

- Horilla screen capture is real Playwright browser automation using the async API. Automatic Horilla-specific field mapping, multi-page navigation, OCR/vision fallback and capture-to-payroll mapping UI remain to be built; the captured page can be reviewed and exported/mapped via CSV.
- Workflow is durable SQLite state rather than Temporal. This meets restart persistence for the demo but not distributed worker orchestration or production retries.
- Finance-friendly single-page dashboard is included; production security, multi-tenant isolation, audit immutability, role-based access, full statutory rule coverage and deployment hardening are not implemented.
- Rule editing is effective-dated. Past payroll runs retain their original rules/results snapshots; new calculations use the latest rules effective for the selected month.

## Tests

```bash
python -m compileall app
```

The demo data is synthetic. Never import real employee data into this demo.
