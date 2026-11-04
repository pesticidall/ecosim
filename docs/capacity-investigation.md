# Prey biomass, producer capacity, and guild size

No saved scenario, animal statistics, diet, birth rate, demand, or producer output
rate was changed in this investigation. Temporary scenario copies exercise the
actual loader and habitat allocation. Content changes to opportunity budgets are
private to each experiment. No interventions or initial carrion are supplied.

## Matrix

The 12-month screen combines:

- Scrub Hares: 60 or 300 (210 or 1,050 kg of initial modeled body mass).
- Red Grass: 500 or 2,000 plants. Output remains the saved grass/seed rate.
- Current guild: 4 jackals, 2 caracals, 2 hyenas, 3 vultures (168 kg/month of
  starting demand). Small guild: 2, 1, 1, 1 respectively (80 kg/month).
- One or two hunt opportunities per animal per round.
- Seeds 104729, 7, and 23.

This is 16 combinations × 3 seeds = **48 year-long runs**. All other animal,
producer, and colony populations and initial resource stores remain fixed.
Producer capacity here means Red Grass count, not a change to plant growth or
per-plant production. Both grass and seed output change together. Rain remains
the scenario's fixed weather, with its existing production multiplier.

January grass output is 155 versus 620 kg. Initial hare demand alone is 30 versus
150 kg/month. Warthogs and other compatible consumers also require local food;
regional leaf/fruit surplus is not automatically accessible in grassland.

## Year-one results

Entries are the number of seeds retaining **all four guild species**, out of 3:

| Hares | Red Grass | Guild | One opportunity | Two opportunities |
|---:|---:|---|---:|---:|
| 60 | 500 | Current | 0 | 0 |
| 60 | 500 | Small | 0 | 0 |
| 60 | 2,000 | Current | 0 | 0 |
| 60 | 2,000 | Small | 0 | 0 |
| 300 | 500 | Current | 3 | 3 |
| 300 | 500 | Small | 1 | 3 |
| 300 | 2,000 | Current | 0 | 0 |
| 300 | 2,000 | Small | 0 | 0 |

Increasing plants did not rescue the guild. Increasing hares helped only when
plant supply was tight enough to cause substantial starvation. Reducing guild
size alone did not solve insufficient intake. Two opportunities with 60 hares
and the current guild depleted hares to zero in every seed, at both plant levels.

For seed 104729 with 300 hares and the current guild, gross carcass production
over year one was:

| Red Grass | Opportunities | Hunted carcasses | Starvation carcasses | Hare starvation deaths |
|---:|---:|---:|---:|---:|
| 500 | 1 | 49.0 kg | 2,205.0 kg | 376 |
| 500 | 2 | 108.5 kg | 2,122.0 kg | 358 |
| 2,000 | 1 | 59.5 kg | 159.0 kg | 0 |
| 2,000 | 2 | 360.5 kg | 154.0 kg | 0 |

Starvation biomass includes all species, including large warthog carcasses; it
must not be interpreted as hare biomass alone. The high-grass controls' early
starvation carcasses come from declining consumers rather than hare famine.
They end year one with 974–1,233 hares across guild/opportunity variants while
the guild mostly disappears. Prey abundance alone does not raise absolute hunt
success under the present mechanics.

## Three-year follow-ups

Twelve additional runs extend four combinations across the same three seeds:

| Hares / grass | Guild | Opportunities | All guild species through 36 months |
|---|---|---:|---:|
| 300 / 500 | Current | 1 | 3/3 |
| 300 / 500 | Current | 2 | 3/3 |
| 300 / 500 | Small | 2 | 3/3 |
| 300 / 2,000 | Current | 2 | 0/3 |

This brings the investigation to **60 runs and 84 simulated years**. Surviving
low-grass cases end with roughly 321–327 hares. They are not a demonstrated
predator–prey balance: for seed 104729, year three supplies 2,045–2,145 kg of
starvation carcasses across the three low-grass configurations, versus only
0–3.5 kg of hunted carcasses. In the current-guild/two-opportunity and
small-guild/two-opportunity runs there are no hunting kills during year three.
Caracals and jackals persist by consuming their explicitly allowed hare carrion.

The high-grass/current-guild/two-opportunity controls lose their last guild member
in months 15–19. Later, their hares also become food-limited and generate carcasses,
but extinct consumers cannot return without introduction or migration. Timing of
food supply matters as well as its eventual amount.

## Interpretation and next correction

The lower-producer cases demonstrate an internally consistent starvation-carrion
pathway, not a reason to starve herbivores deliberately to preserve predators.
Do not promote those factors into the playable scenario as a balance fix.

The current activity-aware selector weights abundance **between eligible species**.
Here, the nocturnal hunters effectively target only hares. With one eligible prey
species, its normalized selection probability is 1 whether there are 60 or 300.
More hares do not increase search opportunities, detection probability, or catch
probability. Encounter selection therefore does not yet model absolute density
or area searched. Resting diurnal prey vulnerability is also absent.

The next correction should separate finding an encounter from succeeding in its
hunt stages, with a defined spatial/search-effort scale. Measure whether greater
eligible prey density increases encounter frequency while retaining probabilistic
detection, chase, contact, and detention. Then compare the same matrix. Do not
boost every stage or add free carrion to reach a desired survivor count.

Other limits remain: fixed producer populations/weather, accumulated food stores,
aggregate demographic rates, adult body-mass carcasses without age structure,
and no full material/energy conversion model for growth and reproduction. Carrion
bookkeeping can reconcile without establishing physically calibrated ecosystem
energetics. Carcass records retain source species but not death cause, so the
ledger measures creation by cause; it cannot attribute every scavenged bite to
starvation versus hunting when both create carcasses of the same species.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -B -m scripts.investigate_capacity > docs/capacity-screen-results.json
.\.venv\Scripts\python.exe -B -m scripts.investigate_capacity --months 36 --hares 300 --grass 500 --guilds current --opportunities 1 2 > docs/capacity-three-year-current-results.json
.\.venv\Scripts\python.exe -B -m scripts.investigate_capacity --months 36 --hares 300 --grass 500 --guilds small --opportunities 2 > docs/capacity-three-year-small-results.json
.\.venv\Scripts\python.exe -B -m scripts.investigate_capacity --months 36 --hares 300 --grass 2000 --guilds current --opportunities 2 > docs/capacity-three-year-control-results.json
```

Each JSON file retains factors, seeds, source fingerprints, monthly population
and food records, resource production/consumption/stocks, carcass budgets, and
first extinction month indices. Every completed month is checked for population
reconciliation, local/regional totals, finite nonnegative resources/carrion, injury
bounds, and carcass mass balance. An invalid ledger fails the experiment rather
than being counted as a valid result. Same-seed cases diverge in random draw
history; these are controlled-input runs, not matched encounter sequences.
