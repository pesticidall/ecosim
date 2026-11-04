# Abundance-responsive hunting search

The subsequent food/reproduction investigation is recorded in
`docs/recovery-reproduction-investigation.md`. It finds that free condition
recovery masks an intake shortfall and that surviving runs still receive large
starvation-carcass subsidies. The saved search configuration below is unchanged.

Jackal and Caracal now opt into a bounded encounter budget through content:

```json
"search_budget": {"reference_prey": 60.0, "max_opportunities": 4}
```

Species without it retain their fixed `hunting_attempts_per_animal` budget, which
defaults to one. Both fields cannot be declared together. Reference prey must be
finite and positive; the maximum must be an integer from 1–8.

## Rules

Eligible abundance sums local populations in explicit prey diets, weighted by
activity overlap. Nonprey, absent prey, and zero-overlap prey contribute nothing.
Same-species prey excludes the searching animal. Dietary preferences still
determine relative prey selection afterward; they do not multiply prey abundance.

Expected **member opportunities** per round are:

`population × maximum × eligible / (eligible + reference)`

This is stochastically rounded to an integer using one seeded draw when fractional.
Integer and empty budgets consume no rounding draw. It never exceeds population
times maximum, and may allocate zero. Fully fed populations do not search. Each
member of a temporary hunting group spends one opportunity per attempt; solo
hunters spend one. A round still stops when fed or when no prey remains.

With one hunter and full activity overlap, the initial configuration gives an
expected 2 opportunities at 60 eligible prey and 3.33 at 300, approaching but never
exceeding 4. Actual allocation can be 3 or 4 in the second example. More prey now
changes absolute opportunity frequency even when only one prey species is
eligible. Detection, concealed approach, chase, contact, and detention remain
separate probabilistic stages. No encounter guarantees a hit or a death.

This is a provisional **local abundance** model, not physical prey density: habitat
area and searched distance are not defined. The reference count specifies the
abundance scale at which half the maximum is expected. It should not be presented
as a calibrated real-world encounter rate. Search effort, fatigue costs, dynamic
producer cover, and resting-prey vulnerability remain unfinished.

Hunting rounds retain the eligible count, reference, cap, expectation, rounded
allocation, and rounding roll. Daily/Calendar Hunts details show the search budget
even when no encounter was allocated. Daily transaction staging preserves those
records and the random stream across failure/retry and copied-state replay.

## Trial and evidence

Select **Playtest B — Hunting Search Trial** after restarting the desktop app.
It starts 300 hares, 2,000 Red Grass plants, and the current full guild. Initial
food stores, other producer/colony populations, and guild sizes match Food Web.
Earlier scenario starting populations remain available; they now use the hunters'
updated content-defined search behavior. `prior_search` in the diagnostic tool
disables the new budget for a previous-one-opportunity comparison.

The fixed-budget screen comprised 12 year-long runs, using 300 hares, 2,000 Red
Grass, current/small guilds, four/eight opportunities, and seeds 104729, 7, 23.
Four fixed opportunities kept the current guild and 286–316 hares through year
one. Eight fixed opportunities exhausted hares in all three current-guild runs.

Six three-year fixed-four runs then showed that the year-one success was fragile:
the current guild exhausted hares in every seed and lost its hunters by months
26–29. The small guild retained all four species but fed predominantly on later
starvation carcasses.

Twelve three-year abundance-search runs used 60/300 hares, 2,000 Red Grass,
current/small guilds, and the same seeds:

| Initial hares | Guild | All species at 36 months | Ending hares |
|---:|---|---:|---:|
| 60 | Current | 0/3 | 615–1,090 |
| 60 | Small | 0/3 | 1,620–3,047 |
| 300 | Current | 3/3 | 1,143–1,742 |
| 300 | Small | 2/3 | 1,264–1,284 |

This is **30 experiments and 66 simulated years** altogether. In the high-prey
current-guild search runs, year-three hunted carcass mass is 1,001–2,492 kg, but
starvation carcasses still contribute 8,352–17,044 kg. The small-guild search runs
have no hunting kills in year three and rely on starvation carrion. Retaining
species therefore does **not** establish a healthy or calibrated food web.

The feedback improves the larger guild's prey-depletion outcome relative to a
fixed-four budget, but is not a cure for trophic balance. Low initial prey can
still lose consumers before prey growth supplies later food. Resource backlog,
prey overshoot, aggregate nutrition/reproduction rules, and carcass creation from
adult body masses remain important limitations. Next compare nutritional condition
and reproduction against sustained food income, and investigate starvation-derived
carcass supply without treating it as an invisible subsidy.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -B -m scripts.investigate_capacity --months 12 --hares 300 --grass 2000 --guilds current small --opportunities 4 8 > docs/search-budget-screen-results.json
.\.venv\Scripts\python.exe -B -m scripts.investigate_capacity --months 36 --hares 300 --grass 2000 --guilds current small --opportunities 4 > docs/search-budget-three-year-results.json
.\.venv\Scripts\python.exe -B -m scripts.investigate_capacity --months 36 --hares 60 300 --grass 2000 --guilds current small --opportunities 4 --abundance-search > docs/abundance-search-three-year-results.json
```

The capacity tool's fixed mode explicitly removes search_budget; its search mode
sets the configured cap and reference in a private registry. Saved content is not
mutated by experiments. JSON retains factors and source fingerprints; all monthly
population/resource/carrion/injury checks from the capacity investigation apply.
The archived files identify their source snapshots; later code/content changes
can change results. Same-seed variants diverge in random draw history.
