# Private prey-access sensitivity

This experiment holds local producer supply at 4,000 Red Grass and compares a
two-by-two diet/activity intervention in private content snapshots. The control
is the 4,000-grass candidate from `local-producer-supply.md`, not a promoted default.
All runs use 60 months and seeds 104729, 7 and 23.

| Profile | Jackal live-prey diet | Jackal and Caracal activity | Hunters able to select guineafowl |
|---|---|---|---|
| `current` | Hare | Nocturnal | Neither |
| `bird_diet` | Hare and guineafowl, equal preference | Nocturnal | Neither |
| `flexible_hunters` | Hare | Flexible | Caracal |
| `flexible_bird_diet` | Hare and guineafowl, equal preference | Flexible | Both |

Caracal already lists both prey species. The flexible profiles change only the
two hunters' activity pattern to the existing `flexible` value. Bird activity
remains diurnal and hare activity remains nocturnal. Flexible activity has weight
1 in both day and night. Under the existing narrower-schedule overlap equation,
hare overlap remains 1 while bird overlap becomes 1 instead of 0.

This is an upper-bound access assumption, not a calibrated life-history claim
or a model of finding inactive/roosting birds. Activity affects eligible search
abundance, weighted prey choice and detection. Opening access therefore changes
effective opportunities and prey-specific encounter outcomes even though hunt
equations, statistical attributes and maximum opportunities remain unchanged.
It is not an isolated prey-choice substitution. No extra daily hunting round,
activity energy cost or species-name simulation branch was added.

The diet change is limited to live prey. Jackal scavenging remains hare-only:
a secured bird supplies its first meal, but does not grant permission for later
bird scavenging or reserve feeding. Caracal's existing scavenging diet already
includes birds. Resource diets, growth, reproduction, reserves and carrion decay
stay fixed. Guineafowl already receive separate juvenile growth food because they
are in Caracal's original prey diet; the added Jackal entry does not newly enable it.

All other factors match the preceding supply experiment: 300 initial hares,
small guild, eight maximum abundance-search opportunities, reference abundance
60, paid recovery, birth threshold 0.9, 30 base-production days of standing stock,
90% monthly carrion loss, nominal 90-day growth and newborn mass fraction 0.1.
Corrected count-weighted age allocation remains fixed. Same-seed profiles can
diverge in their random-draw histories; outcomes are not paired individual hunts.

## Results

All twelve five-year runs completed. The control exactly reproduces the earlier
4,000-grass results after removing the new default `prey_access` metadata field.
The diet-only profile reproduces every monthly control record for all three
seeds. A dietary entry alone does not bypass the activity gate.

Counts and extinction months below are ordered by seeds 104729 / 7 / 23:

| Profile | Guineafowl extinction month | Both hunters at month 60 | Both scavengers at month 60 | Hares at month 60 |
|---|---|---|---|---|
| Current | None / None / None | 3/3 | 2/3 | 2,166 / 398 / 378 |
| Bird diet | None / None / None | 3/3 | 2/3 | 2,166 / 398 / 378 |
| Flexible hunters | 24 / 25 / 12 | 0/3 | 0/3 | 2,311 / 2,315 / 2,324 |
| Flexible + bird diet | 6 / 9 / 5 | 1/3 | 0/3 | 2,321 / 1,900 / 2,323 |

Caracal remains in all runs. With flexible activity alone, Jackals disappear in
months 9 / 7 / 7 and both scavengers in months 13 / 9 / 13. With combined access,
Jackals disappear in months 6 / never / 12, and both scavengers in months 6 / 5 / 13.
The full four-species guild survives in neither activity variant for any seed.

Bird recruitment cannot sustain the newly opened live-prey pathway. All runs
start with 40 adult birds. Lifetime bird births and predation losses are:

| Profile | Seed | Births before extinction | Predation deaths | Starvation deaths |
|---|---:|---:|---:|---:|
| Flexible hunters | 104729 | 33 | 73 | 0 |
| Flexible hunters | 7 | 36 | 76 | 0 |
| Flexible hunters | 23 | 21 | 61 | 0 |
| Flexible + bird diet | 104729 | 9 | 49 | 0 |
| Flexible + bird diet | 7 | 10 | 50 | 0 |
| Flexible + bird diet | 23 | 11 | 51 | 0 |

This demonstrates depletion of the configured 40-bird starting stock under these
upper-bound access assumptions. It does not establish that every positive overlap
or biologically calibrated bird population would collapse.

Opening access also does not increase total early carcass supply: year-one hunt
carcasses fall from 919–953 kg in controls to 589–776 kg with flexible activity
alone and 479–829 kg with combined access. These totals include evolving hunter
populations and age-adjusted carcasses, not matched encounters. They do not isolate
whether prey switching, different mass, food access or subsequent hunter losses
contribute most to the decline.

Higher surviving hare counts are not equilibrium. In year five, flexible-activity
runs lose 516–553 hares to starvation and have zero hare maturation in all seeds.
Combined-access runs lose 160–575 hares to starvation, with only 0 / 3 / 0
maturations. Breeding adults decline in every activity variant during that year.
Year-five starvation carcasses total 904–1,052 kg in five of those runs; the
remaining combined seed 7 produces 363 kg. Later carcasses do not restore already
extinct scavengers. No artificial carrion source was added.

## Verification and next investigation

All 720 monthly simulation accounting checks completed. Maximum absolute monthly
carrion residual is 2.85e-13 kg, rounded upward. Independently checked habitat
stocks sum to regional stocks and continue across month boundaries. Annual prey
population identities reconcile; known-age adult accounting gives nonnegative
inferred maturations. No unclassified prey deaths occur. Inferred maturation is
ending adults minus starting adults plus classified adult deaths; these runs have
no interventions. Annual growth coverage is summed intake divided by summed
requests, whose maintenance gate excludes some latent juvenile demand.

Raw monthly evidence is in `prey-access-results.json`; annual recruitment,
growth food, hunter maintenance demand, carcass totals and extinction summaries
are in `prey-access-summary.json`. Annual blocks are months 1–12, 13–24 and so on.

Reject these flexible-activity profiles for promotion. Broadening live prey
access alone fails this test and consumes the small bird stock before recruitment
can replace it. Do not compensate by raising hunt success, creating adult-sized
births or manufacturing carrion.

The next useful slice is an early-month food-flow audit: retain predator-specific
prey choices, secured-prey mass, first meals, leftover scavenging, reserves and
recovery alongside daily bird breeding counts. The current capacity output has
species-wide predation totals but not a predator-by-prey food-flow table. Trace
why Jackals and scavengers lose feeding support while hares remain abundant
before choosing another content adjustment. A later partial-overlap sensitivity
must state its effects on hare detection as well as bird access; existing
`crepuscular` weights halve overlap with both prey schedules. Calibrating prey
starting stocks and recruitment is separate from opening the access gate.
Maternal costs and age-specific vulnerability remain separate model changes.

## Reproduction

```powershell
.\.venv\Scripts\python.exe -B -m scripts.investigate_capacity --months 60 --seeds 104729 7 23 --hares 300 --grass 4000 --guilds small --opportunities 8 --abundance-search --paid-recovery --birth-thresholds 0.9 --standing-days 30 --carrion-monthly-loss 0.9 --growth-days 90 --growth-ration-modes separate --prey-access current bird_diet flexible_hunters flexible_bird_diet --progress > docs/prey-access-results.json
.\.venv\Scripts\python.exe -B -c "import tempfile, unittest; tempfile.tempdir='.'; result=unittest.TextTestRunner().run(unittest.defaultTestLoader.discover('tests')); raise SystemExit(not result.wasSuccessful())"
```

`--progress` writes completed-case notices to stderr and leaves stdout as JSON.
The new `prey_access` factor defaults to `current`; existing commands retain
their prior ecological configuration and case labels. Four new tests cover
override isolation, independent diet/activity gates and search budgets, actual
bird predation with deterministic replay, diet-only control equivalence, and
invalid profile rejection. All 866 tests pass with checkout-local temporary storage.
Saved content, simulation modules and playable defaults are unchanged.
