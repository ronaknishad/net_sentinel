"""Synthetic flow generator for demonstration and tests ONLY.

The records follow simple, documented rules inspired by how these attack types
usually look in flow data. They are NOT real traffic, and any model trained on
them says nothing about real-world detection performance.

Rules (per flow):
  BENIGN       web/DNS/SSH/NTP/MQTT/CoAP ports, balanced fwd/bwd traffic, moderate rates
  DoS          port 80/443, very high packet rate, many forward packets, almost no reply
  PortScan     random destination port, 1-2 tiny packets, SYN and often RST
  Brute Force  port 21/22, repeated short exchanges with small payloads

About 5% of attack rows are generated with benign-like parameters (label overlap),
a few feature values are blank or infinite, and some rows are duplicated, so the
cleaning code and the metrics are exercised realistically.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

CLASS_MIX = {"BENIGN": 0.60, "DoS": 0.15, "PortScan": 0.13, "Brute Force": 0.12}
OVERLAP_RATE = 0.05


def _benign(rng, n):
    port = rng.choice([80, 443, 53, 22, 8080, 123, 1883, 5683], size=n,
                      p=[.25, .35, .15, .05, .05, .05, .05, .05])
    fwd = rng.poisson(8, n) + 1
    bwd = rng.poisson(9, n) + 1
    dur = rng.lognormal(12, 1.5, n)
    fwd_len = rng.lognormal(5.5, 0.8, n)
    bwd_len = rng.lognormal(6.0, 0.9, n)
    syn = rng.binomial(1, 0.3, n)
    rst = rng.binomial(1, 0.03, n)
    proto = np.where(np.isin(port, [53, 123, 5683]), 17, 6)
    return port, proto, dur, fwd, bwd, fwd_len, bwd_len, syn, rst


def _dos(rng, n):
    port = rng.choice([80, 443], size=n)
    fwd = rng.poisson(120, n) + 20
    bwd = rng.poisson(2, n)
    dur = rng.lognormal(9.5, 0.8, n)
    fwd_len = rng.lognormal(3.6, 0.4, n)
    bwd_len = rng.lognormal(3.0, 0.6, n) * (bwd > 0)
    syn = rng.binomial(1, 0.85, n)
    rst = rng.binomial(1, 0.1, n)
    return port, np.full(n, 6), dur, fwd, bwd, fwd_len, bwd_len, syn, rst


def _portscan(rng, n):
    port = rng.integers(1, 65536, n)
    fwd = rng.integers(1, 3, n)
    bwd = rng.integers(0, 2, n)
    dur = rng.lognormal(6, 1.2, n)
    dur = np.where(rng.random(n) < 0.04, 0, dur)   # zero-duration flows -> infinite rates
    fwd_len = rng.lognormal(3.0, 0.3, n)
    bwd_len = rng.lognormal(2.5, 0.4, n) * (bwd > 0)
    syn = np.ones(n, dtype=int)
    rst = rng.binomial(1, 0.6, n)
    return port, np.full(n, 6), dur, fwd, bwd, fwd_len, bwd_len, syn, rst


def _bruteforce(rng, n):
    port = rng.choice([21, 22], size=n, p=[.4, .6])
    fwd = rng.poisson(14, n) + 6
    bwd = rng.poisson(14, n) + 6
    dur = rng.lognormal(13.2, 0.5, n)
    fwd_len = rng.lognormal(4.0, 0.3, n)
    bwd_len = rng.lognormal(4.3, 0.3, n)
    syn = rng.binomial(1, 0.15, n)
    rst = rng.binomial(1, 0.05, n)
    return port, np.full(n, 6), dur, fwd, bwd, fwd_len, bwd_len, syn, rst


GENERATORS = {"BENIGN": _benign, "DoS": _dos, "PortScan": _portscan, "Brute Force": _bruteforce}


def generate_synthetic_flows(n: int = 3000, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    counts = {k: int(round(n * v)) for k, v in CLASS_MIX.items()}
    parts = []
    for label, count in counts.items():
        gen = GENERATORS[label]
        if label != "BENIGN":
            n_overlap = int(count * OVERLAP_RATE)
            params = tuple(np.concatenate([a, b]) for a, b in
                           zip(gen(rng, count - n_overlap), _benign(rng, n_overlap)))
        else:
            params = gen(rng, count)
        port, proto, dur, fwd, bwd, fwd_len, bwd_len, syn, rst = params
        fwd_bytes = np.round(fwd * fwd_len)
        bwd_bytes = np.round(bwd * bwd_len)
        total_pkts = fwd + bwd
        dur_s = dur / 1e6
        with np.errstate(divide="ignore", invalid="ignore"):
            bytes_s = np.where(dur_s > 0, (fwd_bytes + bwd_bytes) / dur_s, np.inf)
            pkts_s = np.where(dur_s > 0, total_pkts / dur_s, np.inf)
        iat = dur / np.maximum(total_pkts, 1)
        parts.append(pd.DataFrame({
            "Destination Port": port, "Protocol": proto, "Flow Duration": np.round(dur),
            "Total Fwd Packets": fwd, "Total Backward Packets": bwd,
            "Total Length of Fwd Packets": fwd_bytes, "Total Length of Bwd Packets": bwd_bytes,
            "Fwd Packet Length Mean": np.round(fwd_len, 2), "Bwd Packet Length Mean": np.round(bwd_len, 2),
            "Flow Bytes/s": bytes_s, "Flow Packets/s": pkts_s, "Flow IAT Mean": np.round(iat, 2),
            "SYN Flag Count": syn, "ACK Flag Count": np.ones(len(port), dtype=int),
            "RST Flag Count": rst, "Label": label,
        }))
    df = pd.concat(parts, ignore_index=True).sample(frac=1, random_state=seed).reset_index(drop=True)

    # identifier / context columns (excluded from model input by design)
    size = len(df)
    base = pd.Timestamp("2026-01-01 08:00:00")
    df.insert(0, "Flow ID", [f"SYN-{i:06d}" for i in range(size)])
    df.insert(1, "Source IP", [f"10.0.{rng.integers(0, 4)}.{rng.integers(2, 250)}" for _ in range(size)])
    df.insert(2, "Source Port", rng.integers(1024, 65535, size))
    df.insert(3, "Timestamp", (base + pd.to_timedelta(np.cumsum(rng.integers(1, 5, size)), unit="s"))
              .strftime("%Y-%m-%d %H:%M:%S"))

    # realistic data-quality defects
    blank = rng.choice(size, size=max(1, size // 400), replace=False)
    df.loc[blank, "Flow IAT Mean"] = np.nan
    dupes = df.sample(n=max(1, size // 200), random_state=seed)
    return pd.concat([df, dupes], ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a SYNTHETIC demonstration flow CSV.")
    parser.add_argument("--rows", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", default="ml/data/sample_synthetic_flows.csv")
    args = parser.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df = generate_synthetic_flows(args.rows, args.seed)
    df.to_csv(out, index=False)
    print(f"Wrote {len(df):,} SYNTHETIC rows to {out}")


if __name__ == "__main__":
    main()
