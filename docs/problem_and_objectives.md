# Problem Statement and Objectives

## Problem statement
5G and IoT networks connect very large numbers of devices that generate high volumes of short, varied
network flows. Many of these devices have limited built-in security, so unusual traffic (floods,
port scans, repeated login attempts) can be a sign of compromise. Rule-based filters struggle to keep
up with the variety of normal behaviour. This project investigates whether a supervised machine-learning
classifier can distinguish normal flows from suspicious flows using flow-level statistics, and presents
the results in a monitoring interface suited to a small security operations team.

## Scope
NetSentinel is a **prototype for offline flow analysis**. It reads recorded flow records from a CSV
file, trains and evaluates classifiers, labels each flow, and lets an analyst review and track the flows
predicted to be suspicious. It does not capture live packets, has not been deployed on a real 5G core,
and does not block or change anything on a network.

## Objectives
1. Import and validate labelled flow datasets, reporting every problem found.
2. Build a leakage-aware preprocessing and training pipeline and compare at least two classifiers.
3. Evaluate with metrics that suit intrusion detection (recall, false positive rate, per-class results).
4. Classify flows and keep a persistent, reviewable record of predicted suspicious activity.
5. Present everything through a clear dashboard where every number traces to the backend.
6. Document the method, the limits and the honest status of each feature.

## Role of AI/ML in the system
A supervised classifier (Random Forest, Decision Tree or Logistic Regression, whichever scores best on
the held-out test split) learns the statistical difference between normal and attack flows from labelled
examples. At analysis time it predicts a class and an estimated class probability for each flow. The ML
component does **not** decide what is a confirmed incident: a prediction is a lead for a human analyst.
Severity is not produced by ML at all; it comes from a fixed, documented rule on the predicted label.

## How intrusion detection is demonstrated without a real 5G network
5G and IoT traffic is analysed at the **flow level** (packet counts, byte counts, durations, rates,
TCP flag counts). Those features look the same whether the flow crossed a 5G user plane or an ordinary
network, and public intrusion datasets are published in exactly this form. The prototype therefore uses
recorded datasets (CIC-IDS2017 is the intended primary source) and a clearly labelled synthetic generator.
This shows the detection workflow end to end, but it is evidence about the method, not about performance
on a live operator network.
