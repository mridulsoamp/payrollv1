# Prosperr Payroll AI Agent V3

V3 is on the separate `version-3` branch. V2 main is preserved.

## Run

```bash
cd v3
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --reload --port 8003
```

Open http://localhost:8003. Horilla should run separately at http://localhost:8000.

## V3 direction

- Prosperr-inspired finance workspace.
- Horilla browser capture plus CSV/XLSX import.
- Human-reviewed proposals for salary revisions and one-time bonuses.
- Deterministic payroll calculator reused from V2.
- Effective-dated rules, persistent approval state, maker/checker separation, and gated exports.

The current V3 branch is a demo foundation, not a production payroll system. It does not yet include Temporal workers, production RBAC/tenant isolation, a hosted LLM, complete statutory coverage, or payment/filing integrations. V2's seeded statutory settings remain illustrative and must be verified before real payroll use. Use synthetic data only.