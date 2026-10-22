# Run this project on your own computer

This guide is for **Windows and Mac**. It needs about 10 minutes and an internet connection for the first install.
You do **not** need the 3 GB raw data: notebooks 02 and 04 and the dashboard run from the cleaned files already in `data/clean/`.

| What you want to run | Works from this package? |
|---|---|
| `notebooks/02_full_eda.ipynb` (full EDA) | **Yes** |
| `notebooks/04_ai_integration.ipynb` (AI integration + fact-check) | **Yes** |
| Dashboard (`python app.py`) and tests | **Yes** |
| `notebooks/01_...` (cleaning) and `notebooks/03_...` (district maps) | Only if you download the raw data first (see `data/raw/HOW_TO_GET_RAW_DATA.txt`). Without it they stop at the first code cell with a clear message. |

## Step 1 – Install Python
1. Go to https://www.python.org/downloads/ and install **Python 3.11 or newer** (3.10–3.13 work).
2. **Windows:** on the first installer screen tick **"Add python.exe to PATH"**, then click Install.

## Step 2 – Unzip
Unzip `drought_project_run_on_device.zip`. You get one folder, `india-drought-project`. Keep the folders inside it as they are
(`notebooks`, `data`, `reports`, ...).

## Step 3 – Open a terminal in the folder
* **Windows:** open the folder in File Explorer, click the address bar, type `powershell` and press Enter.
* **Mac:** open *Terminal*, type `cd ` (with a space), drag the `india-drought-project` folder into the window, press Enter.

## Step 4 – Create a virtual environment and install the packages
**Windows (PowerShell):**
```
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-user.txt
python -m ipykernel install --user --name drought
```
(If PowerShell says scripts are disabled, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use **cmd** and `.venv\Scripts\activate.bat`.)

**Mac (Terminal):**
```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-user.txt
python -m ipykernel install --user --name drought
```
You should see `(.venv)` at the start of the terminal line. The install can take a few minutes.

## Step 5 – Run a notebook
```
jupyter notebook
```
A browser tab opens. Open `notebooks` → `02_full_eda.ipynb`. If it asks for a kernel, choose **Python 3** or **drought**.
Then menu **Kernel → Restart & Run All**. It takes about 1–3 minutes. Do the same for `04_ai_integration.ipynb`.
You can start Jupyter from the project folder or from inside `notebooks/`; both work.
Figures are saved into `reports/figures/`.

## Step 6 – Run the dashboard
In the same terminal (with `(.venv)` active, in the project folder):
```
python app.py
```
Open **http://127.0.0.1:8050** in your browser. Stop it with **Ctrl+C**.

Optional test (no browser needed): `python tests/test_dashboard.py` – it should end with `ALL TESTS PASSED`.

## Troubleshooting
| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named '...'` (pandas, scipy, seaborn …) | The packages are not installed in the environment Jupyter uses. Activate `.venv`, run `pip install -r requirements-user.txt`, then restart Jupyter **from the same terminal**. |
| Notebook kernel is not using the venv | With `.venv` active run `python -m ipykernel install --user --name drought`, then in Jupyter choose **Kernel → Change kernel → drought**. |
| `No module named 'dash'` | `pip install dash` (inside the activated venv). Make sure you run `python app.py`, not another Python. |
| `FileNotFoundError ... data/clean/...` | The notebook cannot find the project folder. Keep the unzipped folder structure unchanged and start Jupyter inside `india-drought-project` (or its `notebooks` folder). Do **not** upload a single notebook on its own – it needs the `data/` folder next to it. |
| Notebook 01 or 03 says "Raw atlas data not found" | Expected. They need the raw data. Follow `data/raw/HOW_TO_GET_RAW_DATA.txt`, or just use notebooks 02 and 04. |
| `pip install geopandas` fails on Windows | Update pip (`python -m pip install --upgrade pip`) and retry; modern versions install from ready-made wheels. If it still fails, use Anaconda (below) and run `conda install -c conda-forge geopandas`. geopandas is only needed for notebook 03 and the dashboard map. |
| Port 8050 already in use | Close the other dashboard window, or run on another port: Windows PowerShell `$env:PORT=8060; python app.py`, Mac `PORT=8060 python app.py`. Then open http://127.0.0.1:8060. |
| `python` not found (Windows) | Re-install Python and tick "Add python.exe to PATH", or use `py -m venv .venv`. |
| Figures look slightly different | Fine. Numbers are the same; only fonts and spacing can differ by system. |

## Other ways to run
* **Anaconda / Miniconda:** `conda create -n drought python=3.11`, `conda activate drought`, `conda install -c conda-forge geopandas`, `pip install -r requirements-user.txt`, then `jupyter notebook`.
* **JupyterLab:** `pip install jupyterlab`, then `jupyter lab` from the project folder.
* **VS Code:** open the `india-drought-project` folder (File → Open Folder), install the *Python* and *Jupyter* extensions, open a notebook and select the `.venv` / `drought` interpreter at the top right.
* **Google Colab:** upload `drought_project_run_on_device.zip` (Files panel), then in a notebook cell run:
  ```
  !unzip -q drought_project_run_on_device.zip
  %cd india-drought-project
  !pip install -q -r requirements-user.txt
  ```
  then open `notebooks/02_full_eda.ipynb` from the Files panel (or copy its cells), and run it from the `india-drought-project` folder. The dashboard needs a local computer.
