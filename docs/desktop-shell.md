# Playtest B desktop shell

From the repository root, launch:

```powershell
.\.venv\Scripts\python.exe playtest_b.py
```

The shell uses the Python installation's Tkinter. It loads the current content
catalog and existing scenarios without changing their definitions. The existing
`main.py` terminal launcher remains separate.

Choose a scenario and press **Load scenario** to start a new world. Select a
habitat to inspect its species, injured population, resources, weather, and
carrion. The date in the header is the next unresolved ecological date.

- **Next day** completes one date and refreshes the panels.
- **Play month** completes dates one at a time until month end.
- **Pause** stops before the next scheduled date. Completed days stay committed.
- **Slow / Normal / Fast** change presentation delay, not ecological inputs.
  Slow is the default, with one completed day per callback after a one-second
  presentation delay.
- At month end, the notes panel shows the stored monthly report. **Finish review**
  releases the review pause without advancing the date. Start the next month or
  step another day when ready.

Simulation errors stop play and leave the failing date unresolved. Daily
transactions preserve the world and random stream for a retry. Scenario loading
starts a fresh world; save/load is not part of this shell yet.

The **History** tab lists completed dates and stored monthly reports, newest
first. **Latest completed day** follows the run automatically. Select a particular
date to keep that day's view open while play continues, or choose a month report
to revisit it after review. Daily entries use saved evidence for weather, births,
starvation, food shortages, hunt stages, new contact injuries, predation deaths,
resource changes, scavenging, decay, and remaining carrion. Browsing does not
advance the clock or consume randomness. Loading a scenario clears the previous
run's history view.

For hunts using concealed approach, detailed reports show cover, predator
concealment, prey awareness, chance/roll, and the temporary chase escape-score
multiplier between detection and chase. These records also appear in the
Calendar's Hunts filter. An unnoticed approach still can end in escape.

The **Calendar** tab provides a month grid built from recorded daily evidence.
Select a date to read its weather, interventions, hunts, injuries, population
changes, resources, and carrion details. **D** marks a completed date, **N** the
current unresolved date, and **+** an intervention. Interventions on the current
date appear immediately, before ecology runs. Future dates show no predicted
events; earlier dates without daily evidence are explicitly unrecorded.

**Current month / review** opens the active month, or the completed month while
review is pending. Select a named month to keep it open across month boundaries.
Date selection persists within that month while play continues. Calendar browsing
is read-only: it does not advance ecology, spend resources, or change randomness.
Loading a scenario resets the calendar view.

The category selector beside the calendar month offers **All events**, **Weather**,
**Interventions**, **Populations**, **Food coverage**, **Hunts**, **Injuries**,
**Resources**, and **Carrion**. It filters the selected day's details without
changing the date or the grid's intervention markers. Populations includes births,
starvation, and predation deaths; introductions and removals remain under
Interventions. Food coverage shows recorded shortages and, for nutrition-enabled
species, stored food and recoverable deficit-days. Month-end reports show their
ending nutritional state too. Injuries includes new
contact injuries and injured populations remaining at day end. Empty results are
explicit. The filter persists while playing and browsing dates, and resets to
All events when loading a scenario. History and monthly reports retain full detail.

To add **Supplementary food**, pause play, select a populated habitat, choose a
compatible food, select an amount in 50 kg steps, and press **Add food**. The
panel shows the exact unresolved date the action applies to. Food is added
immediately to that habitat and its regional total without advancing time.
The next daily feeding stage can consume it. The action appears immediately
in notes, then in its completed date's History entry and monthly report. During
month-end review, the date is already the next month's first unresolved date;
adding food prepares that date and does not change the completed report.
The selector starts at 50 kg. Herbivore amounts cap at 1000 kg and carnivore
amounts at 500 kg; actual deployment also requires sufficient stock and IC.
The preview shows cost and projected balances, and the header shows current
IC and both feed reserves. Add food is disabled for invalid or unaffordable
requests and while play is running. The headless engine revalidates every
commit, even after an earlier preview. Cancelling a selection without pressing
Add food spends nothing. No water, relocation, or future scheduling is added.

The resource foundation now stores IC and separate food reserves in world state:
10 IC maximum with 2 monthly recovery, 1000 kg herbivore feed with 100 kg monthly
refill, and 500 kg carnivore feed with 50 kg monthly refill. Reserves start full.
Recovery occurs once when a complete daily-simulated month finishes. Every
deployment now costs `ceil(kg / 100)` IC and consumes that mass from its feed
reserve. IC, stock, habitat deposit, regional total, and history record commit
together. Records include deterministic event IDs, feed type, IC spent, and
before/after budget snapshots.

Resource content declares `supplementary_feed_type` as `herbivore` or `carnivore`.
Only tagged kilogram biomass that appears in a living local animal's ordinary
diet is offered. Current plant resources are tagged as herbivore feed. Carnivore
Feed now has a real resource definition and an explicitly compatible jackal diet.
Deployed meat remains a consumable resource and does not create carrion or a death.

Select **Playtest B — Carnivore Feed Trial**, load it, select **Open Grassland**,
and choose **Carnivore Feed** to try the meat intervention. The controlled trial
contains jackals, scrub hares, and an aardwolf. Jackals can consume the meat;
the specialist and hares cannot. The trial intentionally has no termite supply
or production and does not represent a balanced ecosystem. See
`docs/carnivore-feed-trial.md` for scope and diet references.

This first version is a functional desktop dashboard.
The **Interventions** tab provides **Remove** and **Introduce** panels. Select a habitat
on the left, choose a species and a quantity from 1–10, inspect the population preview,
then press **Remove animals · 3 IC** or **Introduce animals · 4 IC**. Play must be paused. Removal uses one
global charge, available again after two completed month boundaries. Too few
animals, insufficient IC, or a recovering charge disables the action. Removed
animals leave without producing carrion. The resulting record appears in notes,
daily history, and monthly reports. Introduction has an independent charge that
recovers after three completed month boundaries and offers species that prefer
the selected habitat. Introduced animals are healthy and count separately from
births. Neither action needs species preset fields. See `docs/population-removal.md`
and `docs/population-introduction.md`. Initial habitat selection now favors populated
habitats so empty locations do not obscure the controls.

Illustrated habitat views and final visual assets are future slices. Water
remains outside Playtest B.

For the expanded roster, select **Playtest B — Food Web**. It includes the seven
B animals, supporting hare prey, all three plants, and local termite colonies.
It is a provisional longer-run trial, not a balanced ecosystem. See
`docs/playtest-b-roster.md` for roles, limits, and initial year-long results.

**Playtest B — Hunting Search Trial** starts 300 hares and 2,000 Red Grass plants
with the full guild. Jackal and Caracal search budgets now respond to eligible
local prey abundance, with a cap of four per animal. The Calendar Hunts filter
shows allocated member opportunities. This remains an experimental scenario:
longer runs still rely heavily on starvation carrion. See `docs/abundance-search.md`.

The controller is tested against the headless runner. Widget tests render a
withdrawn window, load a real scenario, and verify play/pause and month-end
review states without leaving a visible window open.
