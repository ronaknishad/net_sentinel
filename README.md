# NetSentinel

Machine-learning-based network intrusion detection prototype for simulated 5G/IoT traffic.
It classifies recorded network *flow records* from a CSV dataset, lets an analyst review the flows
predicted to be suspicious, and evaluates the models behind those predictions.
It does **not** capture live traffic, has not been deployed on a real 5G network, and takes no action on any network.
A "suspicious" classification is a model prediction, not a confirmed incident.

## Status

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Structure, FastAPI app, design tokens and layout | Done |
| 2 | ML pipeline: validation, mapping, cleaning, training, evaluation, inference | Done; 20 tests executed |
| 3 | Datasets, background training, predictions, analyses, alerts (SQLite), exports | Done; 19 service tests executed, HTTP tests written |
| 4 | React frontend: six pages, charts, alert workflow | Done; build and tests run by the project owner, no errors reported |
| 5 | Testing | See `docs/test_report.md` for exactly what was run and by whom |
| 6 | Polish and documentation | Done; see `docs/` |

Not yet done: evaluation on a real public dataset, browser and device testing, authentication. See `docs/limitations.md`.

## Quick start (Windows, PowerShell, from the project root)

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
cd frontend; npm install; cd ..
python -m uvicorn backend.app.main:app --port 8000      # terminal 1
cd frontend; npm run dev                                 # terminal 2 -> http://localhost:5173
```

Then follow `docs/demonstration.md`: load the bundled synthetic sample, train, analyse, review alerts.
Helper scripts are in `scripts/` (setup, train, start, test).

Command-line training: `python -m ml.train --csv ml\data\sample_synthetic_flows.csv --mode multiclass --synthetic`
Tests: `python -m pytest backend\tests -q`, then `cd frontend; npm test; npm run build`.
API docs while running: http://localhost:8000/docs

## Documentation

| Document | Contents |
|----------|----------|
| `docs/problem_and_objectives.md` | Problem statement, objectives, role of AI/ML, why no real 5G network is needed |
| `docs/architecture.md` | System architecture and data flow diagrams, design decisions |
| `docs/dataset_guide.md` | Datasets, features, excluded columns, leakage assessment, data-quality handling |
| `docs/model_methodology.md` | ML workflow, training, evaluation, severity policy, example synthetic results |
| `docs/api_documentation.md` | Every endpoint and error code |
| `docs/test_report.md` | Tests actually executed, and what was not tested |
| `docs/limitations.md` | Feature status, known limitations, future scope |
| `docs/demonstration.md` | Step-by-step demo, including a normal and a suspicious flow |

## Honest notes
- The bundled dataset is synthetic. Scores on it describe the generator, not real traffic.
- CIC-IDS2017 is the intended real dataset. It is not bundled or downloaded automatically; check its licence and size first.
- Confidence values are uncalibrated model probabilities. Severity comes from a fixed rule on the predicted label.
- There is no login: run the backend on a trusted local machine only.
