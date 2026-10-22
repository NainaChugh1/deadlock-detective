# Deadlock Detective — OS Investigation Tool

A browser-based educational simulator for Operating Systems deadlock concepts.

## Features

- Preset scenarios: Classic Deadlock, Safe State, Dining Philosophers, and Unsafe-but-No-Deadlock
- Editable total resource, allocation, maximum-demand, and request matrices
- Automatic Available and Need calculations
- Resource Allocation Graph (RAG) visualization
- Banker's Algorithm safe-state analysis with a trace
- Directed cycle analysis
- Recovery options: process termination, resource preemption, and checkpoint rollback
- Downloadable JSON and text investigation reports

## Run locally

Python 3.10 or newer is recommended.

1. Install Python from https://www.python.org/downloads/ if it is not already installed.
2. Open a terminal in this folder.
3. Create a virtual environment (optional but recommended):

   **Windows**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

   **macOS/Linux**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Start the app:

   ```bash
   streamlit run app.py
   ```

Streamlit will print a local URL, usually http://localhost:8501.

## Deploy on GitHub + Streamlit Community Cloud

GitHub stores the source code; Streamlit Community Cloud runs the app.

1. Create a GitHub repository named `deadlock-detective`.
2. Upload `app.py`, `requirements.txt`, and `README.md` to the repository root.
3. Sign in at https://share.streamlit.io/ using GitHub.
4. Choose **Create app**, select the `deadlock-detective` repository, branch `main`, and main file path `app.py`.
5. Deploy. Streamlit will install packages from `requirements.txt` and provide a shareable URL.

## Model assumptions and limitations

- This is an educational model, not a live operating-system monitor.
- Banker's Algorithm determines whether the supplied state is safe given the declared maximum demands and available resources. An unsafe state is not necessarily an existing deadlock.
- A directed cycle in a resource-allocation graph is not sufficient by itself to prove deadlock when resource types have multiple instances.
- The recovery recommendations are illustrative. Real recovery choices depend on resource preemptibility, rollback support, process priorities, and lost work.
- The supplied project report described a PyQt5 desktop UI. This repository rebuilds its core educational workflow as a Streamlit website so it can be shared in a browser.
