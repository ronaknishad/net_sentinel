# Trains on the bundled SYNTHETIC sample (not a real benchmark).
$ErrorActionPreference = "Stop"
& .\.venv\Scripts\python.exe -m ml.train --csv ml\data\sample_synthetic_flows.csv --mode multiclass --synthetic
