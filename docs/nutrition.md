# Food reserves and recoverable nutritional condition

Optional food-paid recovery and a food-limited reproduction threshold have now
been implemented and tested experimentally. They are not active in saved content.
See `docs/recovery-reproduction-investigation.md` for rules and three-year results;
the recovery rules described below remain the current playable defaults.

The result table below records the nutrition slice before encounter selection
was refined. The current encounter model and newer comparisons are documented
in `docs/encounter-investigation.md`; `prior_encounters` reproduces the former
saved encounter behavior with nutrition enabled.

The daily habitat food web now supports opt-in animal `nutrition` content:

```json
"nutrition": {
    "reserve_days": 3.0,
    "starvation_grace_days": 7.0,
    "recovery_per_fed_day": 1.0
}
```

The initial configuration applies to jackals, caracals, brown hyenas, and
white-backed vultures. Other definitions retain their existing daily demographic
rules; the legacy monthly runner is unchanged. All three fields must be finite,
positive numbers. These are provisional gameplay assumptions, not biological
calibration. Health remains physiological robustness; reserves and condition are
separate from health, injuries, and demographic rounding fractions.

## Daily order and food accounting

1. Physical resource feeding supplies today's requirement.
2. Existing stored food fills remaining deficits before hunting.
3. Hunting and ordinary scavenging supplement remaining daily requirements.
4. Fully fed populations can fill reserves from leftover compatible resources,
   then compatible carrion. All populations' ordinary feeding precedes storage.
5. Carrion decays; nutritional condition and demographics resolve.

Reserves are aggregated assimilated food measured in kg-equivalent, not a private
carcass cache or an additional habitat resource. Capacity is population times
monthly food requirement divided by 30, times reserve_days. This fixed reference
day keeps capacity stable across month boundaries; actual daily metabolic demand
still uses the current month's length. Initial reserves are empty. No extra hunt
is launched just to store food. Resource top-ups use proportional competition;
carrion top-ups use the existing dietary eligibility and first-access rules.

Caracal now explicitly accepts hare and guineafowl carrion, enabling leftover
consumption without inferring behavior from its carnivore label. The existing
first meal still ends predator first access. Subsequent reserve allocation does
not grant protected caches or lasting ownership.

Every reserve deposit debits actual local resources or carrion. Drawing it later
does not debit that habitat food again. Physical resource consumption in monthly
reports therefore includes storage deposits; daily nutrition counts reserve draws
only when metabolically used. The feeding source `stored_food` is an accounting
marker, not content or a deployable food. Structured reserve-deposit records retain
resource and carcass sources. Carrion totals include reserve top-ups.

## Recoverable condition

`NutritionalState` records population, stored mass, and accumulated deficit-days.
A day at 40% coverage adds 0.6 deficit-days. A fully fed day removes one deficit-day
under the initial configuration, down to zero. Partial feeding still adds the
unmet fraction. Stress is bounded at twice the grace interval.

Starvation pressure is zero through seven accumulated deficit-days, then rises
linearly to full pressure at fourteen. Expected daily starvation is:

`population × current food deficit × pressure / current month length`

Births still use actual nutrition, not the grace-adjusted mortality value. Once
starvation pressure produces fractional expected deaths, the existing rounding
carry retains them; it is not a condition meter and is not erased by feeding.
Sustained famine still causes extinction. The aggregate model does not represent
individual fat stores, digestive timing, reserve spoilage, or nutrition cohorts.

## Population changes, persistence, and reporting

Population loss removes proportional stored mass and keeps mean stress among
survivors. The removed portion is part of the departing animal's aggregate state;
it is not refunded to habitat stores or added as extra carcass mass. Births and
healthy introductions add no stored food and dilute mean stress by population.
Local extinction clears nutritional state. This is a population-average
approximation, not individual allocation of the best-fed or hungriest animals.

Nutritional records are immutable values in habitat state. Daily staging copies
their containers, and snapshots retain them. Failed day/report generation rolls
back reserves and stress along with ecology and randomness. Introduction/removal
previews reconcile them before committing; copying a world retains them.

Daily details (including the Calendar Food coverage filter) and monthly reports
show stored kg and deficit-days. These fields are diagnostics, not HP. Existing
headless tests cover cap/finite validation, physical food accounting, intermittent
shortage recovery, famine, locality, competition, first access, population changes,
rollback, and deterministic resume.

## Measured effect

Saved results: `docs/nutrition-investigation-results.json`. Reproduce with:

```powershell
.\.venv\Scripts\python.exe -B -m scripts.investigate_balance --months 12 --seeds 104729 7 23 --profiles legacy nutrition_only baseline caracal_twilight > docs/nutrition-investigation-results.json
```

`legacy` removes nutrition and caracal carrion eligibility in private content,
reproducing the earlier model. `nutrition_only` enables reserves/condition without
caracal carrion. `baseline` is the new saved content. `caracal_twilight` additionally
changes activity only in memory. Hunt statistics, food demand, birth rates, and
starting populations are unchanged. Diverging runs consume different random draws;
they are same-seed simulations, not identical encounter-by-encounter comparisons.

| Species | Legacy extinction month, seeds 104729 / 7 / 23 | New saved model |
|---|---|---|
| Jackal | 4 / 4 / 3 | 4 / 5 / 4 |
| Caracal | 2 / 2 / 2 | 3 / 4 / 3 |
| Brown Hyena | 4 / 5 / 4 | 5 / 6 / 5 |
| Vulture | 10 / 10 / 10 | 11 / 11 / 11 |

Caracal January food coverage rises from 8.3–12.0% to 16.3–28.3%. Jackal and
scavenger January coverage decreases in these runs, even though extinction is
generally later. Delayed starvation changes carcass supply and encounter/random
histories; no single cause is isolated by those coverage comparisons.

All four species still reach zero within the year in all tested profiles,
including the twilight experiment. This provides buffering and recovery but does
not create enough sustained food income. Next investigate encounter selection,
stage success and opportunity budgets, then scavenger demand relative to the
actual carcass supply. Do not increase reserve capacity merely to conceal a
persistent energy deficit.
