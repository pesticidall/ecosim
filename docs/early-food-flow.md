# Early predator food-flow audit

Nine 13-month traces repeat the `current`, `flexible_hunters` and
`flexible_bird_diet` profiles at 4,000 Red Grass with seeds 104729, 7 and 23.
All ecological parameters are held fixed from `prey-access.md`. This covers the
early Jackal and scavenger losses in the rejected activity profiles. It is a
diagnostic audit, not another balance adjustment or equilibrium test.

## What the trace adds

`scripts/food_flow.py` projects completed daily records without changing world
state or using random draws. Enable it with `--food-flows`. Each habitat records
consumer maintenance demand and sources, search budgets, predator-specific prey
attempts and secured counts, selected-age carcass mass, first meals, released
leftovers, maintenance scavenging by source, reserve deposits by source and
growth scavenging. Start/end nutritional states retain population, reserves and
accumulated deficit days. Region-level fields retain recovery spending and daily
prey populations, adults, births and starvation deaths.

First meals and maintenance scavenging are components of maintenance intake.
Stored-food use is already included in that intake; reserve deposits are separate
physical intake, and condition recovery spends stored food. Released leftovers
are a transfer from a carcass, not another source of biomass. Summing these
columns indiscriminately would count food twice. Recovery spending remains
regional because the saved demographic result does not attribute it to habitats.
Initial missing nutritional states are represented by null, not invented history.
Daily adult counts are opening/closing counts, not the exact post-hunt breeding
count used inside demographics. Age and injury state remain aggregate marginals.

## Findings

There is no missing-prey or habitat gate preventing Jackals from trying to hunt
hares in these failures. For example, flexible-activity seed 7 ends month three
with 336 hares. Jackals make 167 hare attempts and secure 12 animals that month.
Their maintenance intake is nevertheless only 11.35 kg against 24 kg required:
8.66 kg from first meals, 1.96 kg from maintenance scavenging and 0.73 kg from
stored food. They experience 17 shortfall days and reach 13.15 accumulated deficit
days, above the configured seven-day grace period. Monthly abundance and monthly
carcass supply do not guarantee successful daily intake.

The same seed illustrates the reserve/recovery feedback:

| Month-three Jackals | Control | Flexible activity |
|---|---:|---:|
| Maintenance required kg | 24.00 | 24.00 |
| Maintenance consumed kg | 17.65 | 11.35 |
| Reserve deposits kg | 9.74 | 6.83 |
| Recovery spending kg | 5.62 | 6.10 |
| Stored food used for maintenance kg | 4.12 | 0.73 |
| Shortfall days | 11 | 17 |
| Maximum deficit days | 4.41 | 13.15 |

In the flexible case, roughly 89% of month-three deposits are spent on recovery.
This is not extra food created or lost by the diagnostic: `update_condition`
spends reserves after top-ups on fully fed dates. The current rule has no protected
maintenance buffer. It can leave little reserve for subsequent shortfall dates.
That mechanism is visible in the trace, but its causal contribution to extinction
has not been isolated by a policy counterfactual. The first Jackal loss in this
run occurs on month 4, day 23, with 345 hares at the start of the day. The final
Jackal disappears in month seven; its partial-month maintenance intake is only
1.59 of 6.19 kg, despite 110 hare attempts. Thus low delivered food and accumulated
stress, not hare extinction, precede the loss.

Prey switching reduces shared carcass supply even when kill counts rise. Over
the first three months of seed 7:

| Profile | Hare kills | Bird kills | Hunt carcasses kg | First meals kg | Released leftovers kg |
|---|---:|---:|---:|---:|---:|
| Control | 71 | 0 | 230.09 | 40.82 | 189.27 |
| Flexible hunters | 61 | 14 | 215.93 | 42.90 | 173.03 |
| Flexible + bird diet | 53 | 29 | 208.37 | 47.27 | 161.10 |

The combined profile produces 82 kills versus 71 in the control, yet less mass
and fewer leftovers. Physical kilograms use the recorded ages and body masses.
The combined profile also diverts more biomass into hunters' first meals. This
is a measured difference between evolving runs, not a matched-hunt causal estimate.

Bird carcasses are not categorically unavailable to the scavengers. In combined
seed 7, hunters release 23.56 kg of bird leftovers over these three months;
Hyena and Vulture together consume 19.69 kg from birds through maintenance and
reserve scavenging. Jackals still cannot scavenge birds under their explicit
unchanged scavenging diet, but this does not exclude the other consumers.
The source enforces predator first access, then proportional sharing of eligible
remaining demand. No evidence here supports manufacturing carrion or bypassing
those diets.

In that combined run, both scavengers have 17 shortfall days in month three and
reach 13.88 deficit days. In month five, Hyena receives 13.49 of 30 kg of
maintenance food and Vulture 3.60 of 8 kg. Both have 20 shortfall days, reach the
14-day deficit cap and die while 379 hares remain at month end. This establishes
repeated inadequate food delivery before extinction; it is not a claim that
every monthly carcass deficit is caused by the same hunting stage.

Across seeds, the first-three-month combined profiles release 158.64–173.55 kg
of leftovers, compared with 186.25–197.50 kg in their controls. They spend
45.44–64.47 kg on recovery from 84.19–91.44 kg of reserve deposits across the guild.
The activity-only profile is less uniform: seed 104729 initially improves guild
maintenance coverage (74.7% versus 71.4%) before later losses. Early three-month
averages alone do not predict all outcomes. The saved daily sequence is necessary.

## Verification and next step

All nine traces reproduce every corresponding archived monthly ecological field
for months 1–13 after removing only the new food-flow output. All 117 monthly
simulation accounting checks passed. Projected first meals and carcass mass
reconcile with monthly budgets; maintenance source sums and recovery spending
also reconcile. All 867 tests pass with checkout-local temporary storage.
The new actual-scenario regression covers replay, no change when tracing is
enabled, both prey sources, reserve intake without double counting, daily dates,
births and monthly mass totals. Existing uncommitted work is preserved.

Evidence: `early-food-flow-results.json` contains the daily traces;
`early-food-flow-summary.json` aggregates each month. Its `short_days` counts
habitat-days with positive demand and coverage below `1 - 1e-12`; in this scenario
all consumers occupy a single habitat. The summary's intake decomposition was
checked for this scenario, which supplies these consumers no local resource
meals. Resource-fed scenarios must retain resource meals in that decomposition.

This audit explains how abundant hares coexist with hunger: opportunities are
not kills, kills are not interchangeable kilograms, leftovers are shared, and
recovery competes with future maintenance for stored food. It does not identify
a new balanced default or prove an engine defect. Keep the rejected activity
profiles private and hunt-success values unchanged.

The next controlled sensitivity should isolate recovery spending versus reserve
buffering at fixed prey access and supply, retaining food-paid recovery. Compare
daily shortfalls, paid recovery, cumulative deficits and later losses; do not
grant free recovery or food. A protected reserve floor or bounded recovery budget
would be a separate explicit policy change requiring tests and long scenarios.
If investigating hunt competence instead, retain stage outcomes and injuries;
the present flow audit records attempts and meals, not a causal injury analysis.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -B -m scripts.investigate_capacity --months 13 --seeds 104729 7 23 --hares 300 --grass 4000 --guilds small --opportunities 8 --abundance-search --paid-recovery --birth-thresholds 0.9 --standing-days 30 --carrion-monthly-loss 0.9 --growth-days 90 --growth-ration-modes separate --prey-access current flexible_hunters flexible_bird_diet --food-flows --progress > docs/early-food-flow-results.json
.\.venv\Scripts\python.exe -B -c "import tempfile, unittest; tempfile.tempdir='.'; result=unittest.TextTestRunner().run(unittest.defaultTestLoader.discover('tests')); raise SystemExit(not result.wasSuccessful())"
```
