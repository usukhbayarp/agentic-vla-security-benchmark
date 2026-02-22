# Agentic VLA Security Benchmark

A minimal visual sandbox for benchmarking **security failures and explainability** in
**Vision–Language–Action (VLA) agents**.

This repository provides a lightweight, reproducible environment for studying how
security defenses that appear robust in static benchmarks can fail during **multi-step
agentic execution**, and for collecting traces suitable for downstream
**mechanistic interpretability (MI)** analysis.

---

## Motivation

Most existing safety benchmarks evaluate models in static, single-turn settings.
However, real-world agents operate over **sequential decision loops** where internal
representations can drift and constraints may degrade over time.

This project introduces a **minimal agentic sandbox** inspired by WebArena-style
evaluation, while intentionally avoiding large-scale web environments.
The focus is on **controlled failures, trace collection, and explainability** rather
than task coverage or web realism.

---

## What This Is (and Is Not)

**This is:**
- A local, sandboxed **visual agentic environment**
- Screenshot-based **Vision → Language → Action** evaluation
- Deterministic UI with explicit **policy violations**
- Trace logging for analysis and MI

**This is not:**
- A full WebArena or browser-scale benchmark
- A production agent system
- A replacement for large web benchmarks

---

## Repository Structure

```text
agentic-vla-security-benchmark/
  sandbox_ui/        # Minimal HTML UI sandbox
  src/               # Agent loop, VLM interface, utilities
  runs/              # Generated traces (ignored by git)
  requirements.txt
  README.md
```

## Setup

```
python -m venv vla_env
source vla_env/bin/activate
pip install -r requirements.txt
```

## Running the Sandbox

```
python src/agent_sandbox.py
```

This will:
- Open a local HTML UI via Selenium
- Capture a screenshot of the UI state
- Pass the screenshot to a VLM (or stub)
- Execute the selected action
- Save screenshots and a structured trace to ```runs/```


### Development / Testing

```bash
pip install -r requirements-dev.txt
pytest -q
```