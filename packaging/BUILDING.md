# Building EcoSim Playtest A

EcoSim Playtest A is distributed as a 64-bit Windows one-folder application
inside a ZIP archive.

## Requirements

- Windows 10 or Windows 11, 64-bit
- Python 3.14
- Git
- PowerShell

## Prepare the environment

From the project root, create and activate a virtual environment:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the pinned build tools:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
```

Run the test suite:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## Build the distribution

Run:

```powershell
powershell -ExecutionPolicy Bypass -File ".\build_playtest.ps1"
```

The script:

1. Builds `EcoSim.exe` from `EcoSim.spec`.
2. Includes the `content` and `scenarios` directories.
3. Copies `packaging\README.txt` beside the executable.
4. Creates the playtester ZIP archive.

Generated output:

```text
dist\EcoSim\
dist\EcoSim-playtest-a.1-windows-x64.zip
```

The `build` and `dist` directories are generated files and are not committed.

## Test the archive

Extract the ZIP into a new directory outside the repository. Do not test only
the copy in `dist`.

Verify that:

1. `EcoSim.exe`, `README.txt`, and `_internal` are present.
2. Both scenarios appear.
3. A scenario can run through multiple cycles.
4. The starting report contains one `DIETS` section.
5. Export creates `run_report.txt` beside `EcoSim.exe`.
6. The export contains the release identifier, scenario ID, seed, starting
   report, and every completed cycle.
7. Canceling and confirming quit both work.

## Preparing another release

Before building another release, update every release-specific reference:

- `ECOSIM_RELEASE` in `simulation\reporting.py`
- Release text in `packaging\README.txt`
- Archive filename in `build_playtest.ps1`
- Release assertions in the reporting and export tests

Run the full test suite, build the ZIP, and repeat the clean extraction test.