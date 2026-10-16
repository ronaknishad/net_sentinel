# NetSentinel API

Interactive OpenAPI docs are served at `http://localhost:8000/docs` while the backend runs.
All list endpoints are paginated (`page`, `page_size`, maximum 200). Errors return `{"detail": "..."}`.

| Status | Meaning |
|--------|---------|
| 400 | Request values not acceptable (bad filter, missing confirmation, unsupported file type) |
| 404 | Record or evaluation does not exist |
| 409 | Conflict: no trained model loaded, or a training job is already running |
| 413 | Uploaded file exceeds 200 MB |
| 422 | Dataset failed validation, prediction record invalid, or request body malformed |

## System
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Backend status, model-loaded flag, live capture = `not_implemented` |
| GET | `/api/model/status` | Active model metadata or a "train a model" message |
| GET | `/api/system/info` | Dataset directory, storage, input schema, severity policy |
| GET | `/api/overview` | Latest analysis summary, open alert count, evaluation availability |

## Datasets
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/datasets` | List imported datasets with validation reports |
| POST | `/api/datasets/upload` | Multipart CSV upload (`file`, optional `label_column`, `is_synthetic`) |
| POST | `/api/datasets/sample` | Register the bundled SYNTHETIC demonstration dataset |
| GET | `/api/datasets/{id}` | One dataset with its validation report |
| GET | `/api/datasets/{id}/preview?rows=10` | First rows (max 50), JSON-safe |
| POST | `/api/datasets/{id}/validate` | Re-validate with `label_column` and/or `column_overrides` |

## Models
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/models/train` | Start a background job. Body: `dataset_id`, `mode`, `confirm: true`. Returns 202 |
| GET | `/api/models/train` | Training history |
| GET | `/api/models/train/{run_id}` | Poll one job (`running`, `completed`, `failed`) |
| GET | `/api/models/evaluation` | Full evaluation of the saved model |

## Predictions, analyses, flows
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/predictions/samples` | Synthetic example flows, one per class |
| POST | `/api/predictions` | Classify one record; `save: true` stores it as an analysis |
| POST | `/api/analyses` | `source: dataset` (with `dataset_id`) or `source: synthetic` |
| GET | `/api/analyses` | Analysis history |
| GET | `/api/analyses/{id}` | Summary: class and severity distribution, timeline (only if timestamps exist) |
| GET | `/api/flows` | Search, filter (`classification`, `attack_class`, `protocol`, confidence range, `analysis_id`), sort, paginate |
| GET | `/api/flows/facets` | Distinct classes and protocols for filter menus |
| GET | `/api/flows/{id}` | Flow detail with features, model info and linked alert |

## Alerts and exports
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/alerts` | Filter by `status`, `severity`, `analysis_id`; includes status counts |
| GET | `/api/alerts/{id}` | Alert with feature values and model info |
| PATCH | `/api/alerts/{id}` | Body `{"status": "new" \| "under_review" \| "resolved"}` |
| GET | `/api/exports/evaluation?format=json\|csv` | Evaluation report download |
| GET | `/api/exports/analyses/{id}` | All flows of an analysis as CSV |

Predicted classes are model outputs. They are not independently verified incidents, and the
confidence value is not a calibrated risk score.
