# NetSentinel Setup Guide

How to download NetSentinel from GitHub and run it on a new computer. Follow the steps in order.
Windows is the primary target (steps in PowerShell); macOS and Linux commands are given where they differ.

**What you will have at the end:** the backend API running on port 8000 and the web interface on
http://localhost:5173, with a model trained on the bundled synthetic sample.

> Time needed: about 10 to 15 minutes on first setup, mostly downloading packages.
> Internet is needed for the first setup only. After the packages are installed, the app runs offline.

---

## 1. Install the prerequisites

| Tool | Version | Check with | Download |
|------|---------|-----------|----------|
| Python | 3.10 or newer (3.11 or 3.12 recommended) | `python --version` | python.org/downloads |
| Node.js | 18 or newer (the LTS version is fine) | `node --version` | nodejs.org |
| Git (optional) | any | `git --version` | git-scm.com (only needed for `git clone`) |

**Windows Python installer:** on the first screen, tick **"Add python.exe to PATH"** before clicking
Install. After installing either tool, **close PowerShell and open a new window** so the PATH change applies.

---

## 2. Get the code

**Option A: Git**
```powershell
git clone <your-repository-url> netsentinel
cd netsentinel
```

**Option B: Download ZIP**
1. On the GitHub page, click **Code**, then **Download ZIP**.
2. Right-click the ZIP and choose **Extract All**.
3. Open PowerShell **inside the folder that directly contains `backend`, `frontend`, `ml` and `docs`**.
   Extracted ZIPs are often nested (for example `netsentinel-main\netsentinel-main`). If you run
   `dir` and do not see `backend` and `frontend`, go one folder deeper.

Check you are in the right place:
```powershell
dir
```
You should see `backend`, `frontend`, `ml`, `docs`, `scripts` and `README.md`.

---

## 3. Set up the backend (Python)

Run these from the project folder. They create an isolated Python environment and install the packages.

**Windows (PowerShell)**
```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

After activation your prompt starts with `(.venv)`. You must activate the environment again in every
new terminal before running backend commands.

`Set-ExecutionPolicy -Scope Process Bypass` only affects the current window and changes nothing permanently.

---

## 4. Set up the frontend (Node)

```powershell
cd frontend
npm install
cd ..
```

`npm install` takes about a minute. Warnings about "deprecated" packages and "vulnerabilities" are normal
for development tools and do not stop the app. **Do not run `npm audit fix --force`**; it can upgrade
packages to versions that break the build.

---

## 5. Start the application

You need **two terminals** open at the same time.

**Terminal 1: backend** (project folder, `.venv` active)
```powershell
python -m uvicorn backend.app.main:app --port 8000
```
Wait for `Uvicorn running on http://127.0.0.1:8000`. Leave this window open.
Interactive API docs are at http://localhost:8000/docs.

**Terminal 2: frontend**
```powershell
cd frontend
npm run dev
```
It prints a local address, normally `http://localhost:5173`. Open it in your browser.

The first time, the top bar shows **No model loaded**. That is expected: trained models are not stored
in GitHub, so each new device trains its own (next step).

---

## 6. First run walkthrough

1. Open **Dataset Management**.
2. Press **Load bundled synthetic sample**. A validation report appears (3,015 rows, a `Label` column,
   mapped features, columns not used).
3. Under **Train a model**, keep **Multiclass**, tick the confirmation box and press **Train model**.
   On the sample it takes a few seconds. The top bar then shows *Model loaded: Random Forest (multiclass)*.
4. Under **Analyse traffic**, press **Analyse selected dataset**. A message reports records processed and
   records classified as suspicious.
5. Explore **Network Overview**, **Traffic Analysis**, **Detection Alerts** and **Model Evaluation**.
6. In **Traffic Analysis**, use **Classify a single flow** to try a normal and a suspicious example.

`docs/demonstration.md` has the full walkthrough with expected results.

> The bundled data is **synthetic**. The high scores describe the data generator, not real-world detection.

---

## 7. Using your own data

1. Dataset Management, **Import traffic data**, choose a CSV (under 200 MB, one flow per row, with a label column).
2. Read the validation report. If a feature column is not recognised, use the **Feature mapping**
   drop-downs, then **Re-validate**. If the label column is not detected, choose it from the list.
3. Train and analyse as above.

For CIC-IDS2017, download one day's CSV from the Canadian Institute for Cybersecurity website after
checking its licence and citation terms. Place it anywhere and upload it through the interface.
Large files take longer to validate and train, so start with a single day.

---

## 8. Stopping, restarting and resetting

- **Stop:** press `Ctrl+C` in each terminal.
- **Restart later:** activate `.venv`, then repeat step 5. Your datasets, analyses, alerts and trained
  model are kept in `backend\data` and `ml\artifacts`, so no retraining is needed.
- **Reset everything:** stop the backend, then delete the `backend\data` folder and the files inside
  `ml\artifacts` (keep the `.gitkeep` file).

---

## 9. Running the tests

```powershell
python -m pytest backend\tests -q      # backend and ML tests (.venv active, project folder)
cd frontend
npm test                               # frontend tests
npm run build                          # type-check and production build
```

---

## 10. Troubleshooting

| Problem | Cause and fix |
|---------|---------------|
| `py` is not recognized | The Python launcher is not installed. Use `python` instead (as in this guide), or reinstall Python with "Add to PATH" ticked |
| `python` opens the Microsoft Store or is not recognized | Python is not installed or not on PATH. Install from python.org with "Add python.exe to PATH", then open a new PowerShell |
| `Activate.ps1 cannot be loaded because running scripts is disabled` | Run `Set-ExecutionPolicy -Scope Process Bypass`, then activate again |
| `pip` is not recognized | Use `python -m pip install -r backend\requirements.txt` |
| `ModuleNotFoundError: No module named 'fastapi'` (or `backend`) | The environment is not active, or you are in the wrong folder. Activate `.venv` and run from the folder that contains `backend` and `ml` |
| `npm` is not recognized | Install Node.js LTS, then open a new PowerShell |
| `npm install` fails with network errors | The first install needs internet. Check your connection or proxy and run it again |
| `npm run dev` fails with an esbuild error | Run `npm rebuild esbuild` inside `frontend`, then try again |
| Page says **Backend unreachable** | Terminal 1 is not running, or it failed to start. Start the backend first and check its output for errors |
| `Address already in use` / port busy | Another program uses the port. Stop it, or use another backend port and change the proxy target in `frontend\vite.config.ts` to match |
| **No model loaded** after a fresh clone | Expected. Train one in Dataset Management (step 6) |
| Train button disabled | Tick the confirmation box and make sure the dataset shows **Valid** |
| Upload rejected | Only `.csv` files up to 200 MB are accepted. The message names the problem (empty file, no label column, fewer than 6 supported features) |
| Browser shows an old or blank page | Hard refresh with `Ctrl+Shift+R`, and confirm the frontend terminal is still running |

If something else fails, copy the full error text from the terminal. The first error line is the most
useful part.

---

## 11. What is and is not included

- Included: dataset import and validation, three classifiers with comparison, evaluation, traffic
  classification, alerts with investigation status, exports.
- Not included: live packet capture, real 5G network integration, user login. The app is meant to run
  on a trusted local machine; do not expose port 8000 to other networks.
- Details: `docs/limitations.md`.

---

## Appendix: publishing the project to GitHub (for the owner)

The `.gitignore` already excludes `node_modules`, uploaded datasets, the local database and trained models.
```powershell
git init
git add .
git commit -m "NetSentinel: ML-based intrusion detection prototype"
git branch -M main
git remote add origin <your-repository-url>
git push -u origin main
```
Before pushing, confirm `git status` does not list `.venv`, `frontend/node_modules` or `backend/data`.
Add a licence file if you want others to reuse the code, and do not commit large public datasets.
