# Concealed approach and hunting balance

The comparisons below predate abundance-responsive search. The latest budget
and longer-run findings are documented in `docs/abundance-search.md`.

Jackal and Caracal now opt into `approach_model: concealed`. Species without this
field retain their previous approach behavior and random draw sequence. No
species statistics, food demand, birth rates, starting populations, or opportunity
budgets were changed. The new rules are provisional gameplay assumptions.

## Two separate awareness questions

1. The predator first detects prey, using the existing perception versus prey
   stealth, activity, habitat visibility/concealment, and weather calculation.
2. If prey was found and movement is compatible, a separate concealed-approach
   roll determines whether the prey notices the predator closing the distance.
3. Chase, contact, retaliation, and detention still resolve normally and can fail.

The second step uses predator stealth (including its stealth trait modifier)
against prey perception. Group size creates exposure for hunters and collective
awareness for defenders. For opted-in groups, the earlier awareness contribution
is removed from prey-detection scores and moved into this separate stage so prey
noticing hunters is not counted twice. Coordinated group search still applies.

The current formulas are:

`cover = (vegetation_density + shelter_availability) / 2`

`concealment = predator stealth × stealth trait modifier × cover / sqrt(hunter count)`

`awareness = prey perception × weather visibility × sqrt(defender count)`

`P(unnoticed) = concealment / (concealment + awareness)`

An unnoticed approach changes the effective prey escape score for this chase by
`1 - 0.5 × cover`. The multiplier stays between 0.5 and 1. It represents reduced
starting distance, not a persistent reduction to prey mobility or an injury.
It never bypasses movement incompatibility or guarantees contact or death.

No cover or zero concealment gives no advantage and consumes no additional roll.
Failed initial detection and incompatible movement never invoke the stage.
Otherwise a seeded approach roll is retained alongside its scores and result.
Detailed hunt reports present it between detection and chase. Counterattack,
trauma, injuries, and detention keep their established meanings.

## Scope and limits

Shelter availability currently represents access to hiding places for this
calculation. Physical refuges that exclude a predator, body-size fit, dens, and
resting-prey vulnerability are not implemented. Existing vegetation still hides
prey in the first detection step. Cover is therefore a trade-off, not a universal
predator bonus.

Producer populations do not yet modify cover. This slice uses saved habitat
conditions only. Dynamic Red Grass, shrub, and tree contributions need an explicit
coverage/occupancy scale; summing plant counts into a concealment bonus would be
arbitrary. Absolute encounter frequency also remains unchanged. Finding prey and
approaching unnoticed are distinct from how often searching creates an encounter.

## Same-seed experiments

Twelve year-long runs compare seeds 104729, 7, and 23:

- `prior_cover`: previous saved encounter/nutrition model, no concealed approach.
- `baseline`: new approach with saved Open Grassland conditions (cover 0.25).
- `dense_cover_no_approach`: synthetic dense conditions without the new stage.
- `dense_cover`: identical dense conditions with the new stage.

Dense conditions set openness to 0.5 and vegetation and shelter to 0.7 in a
private registry copy; they do not relocate animals or rewrite the habitat file.
The diagnostic reports conditional stage counts/probabilities and biomass ledgers.
Runs diverge in random draw history; they do not share identical encounters.

| Profile | January Caracal coverage, seeds 104729 / 7 / 23 |
|---|---|
| Previous approach | 27.5% / 26.3% / 22.6% |
| New approach, saved habitat | 32.2% / 32.2% / 13.1% |
| Dense cover, no new approach | 19.6% / 18.0% / 10.8% |
| Dense cover, new approach | 19.7% / 20.9% / 16.1% |

All four guild species still reach zero by year end in all tested profiles.
Unnoticed approaches improve a conditional chase chance, but do not guarantee
better whole-run outcomes. Denser vegetation improves concealment on approach
while also making prey harder to find. Numerical tuning must account for both.
The earlier prey/producer/guild capacity findings remain relevant: this does not
solve sustained food income or the missing absolute encounter-density mechanism.

The test suite covers independent shelter and vegetation contributions, stealth,
prey perception, group awareness/exposure, zero-cover and opt-out behavior,
deterministic replay, movement incompatibility, bounded advantage, failed capture,
finite normalization, actual solo/group wiring, and detailed reporting.

Reproduce the saved raw evidence with:

```powershell
.\.venv\Scripts\python.exe -B -m scripts.investigate_balance --months 12 --seeds 104729 7 23 --profiles prior_cover baseline dense_cover_no_approach dense_cover > docs/cover-investigation-results.json
```
