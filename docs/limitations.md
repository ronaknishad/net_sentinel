# Limitations, Status and Future Scope

## Feature status
| Capability | Status |
|------------|--------|
| CSV import, validation, feature mapping and overrides | Implemented |
| Training and comparison of three classifiers, binary and multiclass | Implemented |
| Evaluation metrics, confusion matrix, exports (CSV, JSON) | Implemented |
| Flow classification of datasets, single records and synthetic flows | Implemented |
| Persistent alerts with investigation status | Implemented |
| Analysis history, filters, sorting, pagination | Implemented |
| Synthetic traffic generator | Simulated (documented rules, not real traffic) |
| Live packet capture | Not implemented |
| Real 5G core or operator network integration | Not implemented |
| User accounts and authentication | Not implemented |
| Automatic blocking or any action on a network | Not implemented (by design) |

## Known limitations
**Data and evaluation**
- Real-dataset performance has not been measured in the build environment. Bundled results are synthetic.
- One stratified split, no cross-validation, no hyperparameter tuning.
- The reported model is selected on the same test split it is scored on, so its score is slightly optimistic.
- Destination port is a model input and a known shortcut in many public datasets. Excluding individual
  features is not configurable.
- Public datasets can contain labelling and capture artefacts; verify before drawing conclusions.
- The model can only predict classes it saw in training, and predictions on unrelated datasets may be unreliable.
- Probabilities are uncalibrated and are not risk scores.

**Application**
- No authentication or roles: anyone who can reach the backend can change alert status. The interface
  and API assume a single local user. Do not expose the backend to an untrusted network.
- Offline analysis only. Nothing is monitored in real time.
- Each analysis stores up to 100,000 flows in SQLite; larger files are rejected. Uploads are limited to 200 MB.
- One training job at a time, running in memory inside the API process.
- Binary-mode alerts are all Medium severity because the model does not know attack types.
- Analyses do not remove duplicate rows (training does).
- The timeline chart appears only when most flows carry parseable timestamps.
- No model versioning beyond the active model; training replaces it.
- No drift monitoring, retraining schedule or protection against adversarial evasion.

**Testing**
- Interface behaviour in real browsers, on phones and tablets, and with assistive technology has not
  been verified by automated tests. Accessibility features (labels, focus outlines, text labels beside
  colour) were built in but not audited with tooling.
- Frontend tests are limited to formatting helpers and a few shared components.

## Future scope
- Live flow ingestion from a capture or flow-exporter feed, kept separate and used only in an authorised test environment.
- Authentication, roles and an audit log of alert changes.
- Cross-validation, a separate validation split, calibrated probabilities and per-feature exclusion.
- Evaluation on additional public datasets (for example an IoT-focused one) and cross-dataset testing.
- Model registry with comparison between trained versions.
- Explanations for individual predictions and analyst feedback to improve labels.
