# Test Report

Report date: 2026-10-16. This report lists only what was actually executed, and by whom.

## Executed in the build sandbox
The sandbox had pandas, NumPy, scikit-learn and joblib, but not pytest, FastAPI or npm packages. The
39 ML and service-layer tests were run with a small stand-in runner that calls each `test_*`
function and reports pass or fail.

**Result: 39 passed, 0 failed** (final run after the last backend change).

| Test file | Test functions | Execution |
|-----------|----------------|-----------|
| `test_api.py` | 5 | Written; see below |
| `test_ml_preprocessing.py` | 7 | Executed in the build sandbox (stand-in runner) |
| `test_ml_training.py` | 13 | Executed in the build sandbox (stand-in runner) |
| `test_services_datasets.py` | 8 | Executed in the build sandbox (stand-in runner) |
| `test_services_workflow.py` | 11 | Executed in the build sandbox (stand-in runner) |

Covered: CSV loading and rejection of bad files; header mapping and excluded columns; missing, infinite
and duplicate value reporting; label encoding; cleaning counts; stratified, disjoint, reproducible splits;
fitting on training data only; hand-checked metric values; binary and multiclass training; rare-class
handling; model persistence and reload; prediction output format; invalid prediction requests;
severity policy; dataset upload safety (extension, size, path traversal); column overrides; background
training with confirmation and a single-job limit; full dataset-to-alert workflow; filters, sorting,
search and SQL-injection-style input; alert status persistence across new connections; timeline and
summary; single-record prediction; unlabelled data; CSV exports; system information.

Additionally, every API route handler was called directly through a throwaway stand-in for FastAPI
(upload, training, reload, prediction, analysis, filters, alert update, exports, error codes). This
checks the wiring between handlers and services. It is not an HTTP test.

## Executed by the project owner on Windows
After Phase 4 the project owner ran the backend tests (`python -m pytest backend\tests -q`, including the
5 HTTP-level tests in `test_api.py`) and the frontend commands
(`npm run build`, `npm test`) and reported that they produced no errors. The output itself was not shared
with the author of this report, so no counts are stated here beyond the file inventory above.

## Not tested
- Real-dataset training (for example CIC-IDS2017).
- Behaviour in real browsers, responsive layouts on phones and tablets, and keyboard or screen-reader use.
- Load and large-file performance near the upload and row limits.
- The PowerShell helper scripts in `scripts/`.

Total test functions in the repository: 44.
