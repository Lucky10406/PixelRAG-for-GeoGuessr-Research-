# PixelRAG GeoGuessr Experiment Log

This file is the permanent record of what we do.

## Experiment format

For every experiment, record:

* Date
* Experiment ID
* Objective
* Code version / Git commit
* Environment
* Dataset / image IDs
* PixelRAG version
* Parameters
* Results
* Problems encountered
* Decision
* Next action

\---

# Phase 1

## EXP-001 — Environment + API smoke test

Date:
Status: NOT STARTED

### Objective

Verify that the PixelRAG environment works and that one GeoGuessr image can be queried successfully.

### Environment

Python:
OS:
PixelRAG version:

### Steps

* \[ ] Python 3.12 verified
* \[ ] Virtual environment created
* \[ ] PixelRAG installed
* \[ ] PixelRAG import verified
* \[ ] Hosted service/API interface verified
* \[ ] One GeoGuessr image selected
* \[ ] Image query successful
* \[ ] Raw retrieval response saved

### Result

### Problems

### Decision

### Next action

\## Phase 5 — Deterministic Reader



Date: 2026-10-05



Reader:

\- Deterministic rank-weighted country-title reader.

\- Input: PixelRAG Top-5 retrieval results.

\- Gold labels are not used during prediction.

\- UNKNOWN is allowed when no explicit country evidence is retrieved.

\- Rank weights: 1=5, 2=4, 3=3, 4=2, 5=1.

\- Ties produce UNKNOWN.



Inputs:

\- results/retrieval\_hits.csv



Outputs:

\- results/reader\_predictions.csv

\- results/reader\_metrics.json



Evaluation:

\- Overall country accuracy

\- Prediction coverage

\- Selective accuracy

\- Abstention rate

\- Per-country accuracy

\- Correct / incorrect / UNKNOWN examples



Phase status:

\- Completed only after all 150 images have predictions and reader\_metrics.json is successfully generated.

