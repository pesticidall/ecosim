ECOSIM — PLAYTEST A
Release: playtest-a.1

ABOUT

EcoSim is an ecosystem simulation in development. Playtest A focuses on
resource production, herbivore feeding, competition, starvation, and
reproduction across repeated simulation cycles.

This build contains two scenarios:

1. Balanced Beginnings
   Three herbivore species begin with plentiful food reserves.

2. Grazing Pressure
   The same environment begins with twice as many animals, creating stronger
   competition and an early population crash.

SYSTEM REQUIREMENTS

- Windows 10 or Windows 11, 64-bit
- No Python installation is required

LAUNCHING ECOSIM

1. Extract the entire EcoSim folder from the ZIP file.
2. Keep EcoSim.exe and the _internal folder together.
3. Double-click EcoSim.exe.

Do not move EcoSim.exe out of its folder by itself. The _internal folder
contains files required by the simulation.

CONTROLS

Scenario selection:
- Enter a scenario number and press ENTER.
- At confirmation, press Y to continue.
- Press B or ENTER to return to scenario selection.

During a simulation:
- Press ENTER to advance one cycle.
- Press E to export the run report.
- Press Q to request quitting.

At quit confirmation:
- Press Y to quit.
- Press B or ENTER to return to the simulation.

EXPORTED REPORTS

Exporting creates or updates run_report.txt beside EcoSim.exe.

The report contains:
- EcoSim release identifier
- Scenario name, description, and ID
- Random seed
- Starting populations and resources
- Weather and diets
- Every completed cycle report

Export again after advancing more cycles to update the file with the latest
history.

KNOWN PLAYTEST A LIMITATION

Starvation deaths and births are rounded down each cycle. Small, partially fed
populations can sometimes persist because fractional changes do not carry into
later cycles.

FEEDBACK

When reporting a problem, please include:
- The EcoSim release identifier
- The selected scenario
- What you expected to happen
- What happened instead
- run_report.txt, when available