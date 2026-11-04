# Recovery, reproduction, and starvation-carrion dependence

Continuing balance work is useful when it isolates assumptions rather than
changing statistics until species survive. This slice adds two optional models,
leaves saved content/scenario values unchanged, and compares them over three years.

## Experimental rules

Animal nutrition may declare `recovery_requires_food: true`. On a fully fed day,
condition recovery then consumes actual stored food. Recovered deficit-days are
limited by the configured recovery rate, outstanding deficit, and
`reserve_kg / daily_requirement`. The corresponding mass is deducted from reserves.
Meeting today's metabolic requirement without any remaining food cannot erase
past deficit-days. Draws and deposits still follow the normal physical food path.
Partial feeding adds its unmet fraction as before. Missing/false retains the
previous free-recovery rule, so current playable content keeps its behavior.

Actual food used for recovery is retained in daily demographic evidence, diagnostic
JSON, Calendar Food coverage details, and monthly reports. Physical resource
consumption includes deposits later used for recovery; the main feeding result
still describes ordinary daily nutrition. Tests reconcile resources, remaining
reserves, metabolic intake, and recovery expenditure without creating food.

An animal may independently declare `reproduction_food_threshold`, from 0 inclusive
to 1 exclusive. Birth expectations use the fertility multiplier:

`max(0, (actual_food_coverage - threshold) / (1 - threshold))`

The default 0 preserves existing behavior. At threshold 0.9, coverage of 90% or
less adds no birth expectation, 95% gives half the normal rate, and 100% gives
the full configured birth rate. Existing rounding carry is retained. Mortality,
health, injury, and reserve capacity are unchanged. This is a simple current-food
gate, not pregnancy, developmental nutrition, or a body-condition fertility model.

Both options are experimental and are not enabled in saved animal definitions.
Their values are game-model trials, not biological measurements.

## Controlled experiments

All runs start with 300 hares and 2,000 Red Grass plants, abundance-responsive
search (reference 60), fixed scenario weather, and no interventions. Seeds are
104729, 7, and 23. Saved statistics, demand, base birth rates, initial stores, and
plant output rates stay fixed. The reproduction threshold is applied to all animal
definitions in a private registry; paid recovery applies only to definitions with
the existing nutrition model. Scenario experiments never modify saved content.

The first 12 runs form a two-by-two comparison: free/paid recovery and birth
threshold 0/0.9, with the current guild and search ceiling 4. Nine further runs
test ceiling 8 with paid recovery: both guilds at threshold 0.9, and the small
guild at threshold 0.99. Total: **21 three-year runs, 63 simulated years**.

| Recovery | Birth threshold | Search ceiling | Guild | All four species at 36 months |
|---|---:|---:|---|---:|
| Free | 0 | 4 | Current | 3/3 |
| Free | 0.9 | 4 | Current | 3/3 |
| Paid | 0 | 4 | Current | 0/3 |
| Paid | 0.9 | 4 | Current | 0/3 |
| Paid | 0.9 | 8 | Current | 0/3 |
| Paid | 0.9 | 8 | Small | 3/3 |
| Paid | 0.99 | 8 | Small | 3/3 |

With paid recovery and ceiling 4, hunters vanish in months 5–6, hyenas in month 7,
and vultures by month 13. Free recovery therefore masks a sustained food shortfall;
requiring real recovery food exposes it rather than improving survivor counts.
Raising the ceiling to 8 with the current guild exhausts prey enough that only
15–30 hares remain at year three, and all guild species disappear.

The surviving small-guild variants are still not healthy hunting balances:

| Paid recovery, small guild, ceiling 8 | Year-three hunted biomass | Year-three starvation biomass |
|---|---:|---:|
| Birth threshold 0.9 | 322–346 kg | 14,200–14,225 kg |
| Birth threshold 0.99 | 329–343 kg | 12,942–12,957 kg |

For seed 104729, the threshold-0.9 run's year-three starvation mass consists of:

| Source | Starvation deaths | Modeled carcass biomass |
|---|---:|---:|
| Aardwolf | 2 | 16 kg |
| Helmeted Guineafowl | 1,291 | 1,936.5 kg |
| Scrub Hare | 2,128 | 7,448 kg |
| Warthog | 48 | 4,800 kg |

These records reconcile mechanically. They reveal a modeled supply problem rather
than disappearing carcass mass. Earlier food accumulation supports population
overshoot; later shortages create large carcass pulses. Newly born animals enter
an aggregate population whose deaths use typical adult mass, without age/mass
structure. Reproduction and adult body mass are not constrained by a full material
conversion model. A tighter current-food birth gate does not remove those limits.

## Decision

Follow-up: [standing food investigation](standing-food.md) implements optional
growth limits and compares nine three-year runs. It reduces starvation pulses
but also identifies unconfigured carrion decay as another persistent food subsidy.

Keep these options experimental; do not promote a surviving small-guild result as
a balanced scenario. Do not compensate for paid recovery simply by increasing hunt
statistics or manufacturing carcasses. The next useful slice is finite standing
food stocks/food turnover, with separate resource types rather than unlimited
accumulation. Then assess growth, reproduction, and the adult-mass carcass
approximation. A lightweight aggregate solution may suffice for B; detailed
individual anatomy or a full energy model is not required by this investigation.

The original habitat cover and abundance-search work remains intact. There is
no reason to keep tuning their numbers while the main food supply can be dominated
by delayed starvation pulses. Same-seed variants diverge in encounter/random-draw
history, so the comparisons do not hold individual encounters fixed.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -B -m scripts.investigate_capacity --months 36 --hares 300 --grass 2000 --guilds current --opportunities 4 --abundance-search --birth-thresholds 0 0.9 > docs/recovery-birth-control-results.json
.\.venv\Scripts\python.exe -B -m scripts.investigate_capacity --months 36 --hares 300 --grass 2000 --guilds current --opportunities 4 --abundance-search --paid-recovery --birth-thresholds 0 0.9 > docs/recovery-birth-paid-results.json
.\.venv\Scripts\python.exe -B -m scripts.investigate_capacity --months 36 --hares 300 --grass 2000 --guilds current small --opportunities 8 --abundance-search --paid-recovery --birth-thresholds 0.9 > docs/recovery-search-eight-results.json
.\.venv\Scripts\python.exe -B -m scripts.investigate_capacity --months 36 --hares 300 --grass 2000 --guilds small --opportunities 8 --abundance-search --paid-recovery --birth-thresholds 0.99 > docs/recovery-search-strict-birth-results.json
```

Results retain factor settings, seeds, source fingerprints, food/recovery records,
monthly resource and population evidence, and carcass budgets. Existing accounting
and nonnegative-state checks run at every month completion. Tests additionally
cover recovery with empty/insufficient reserves, exact monthly physical food
accounting, reproduction threshold behavior, content validation, private-config
isolation, rollback, and copied-state replay.
