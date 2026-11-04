# Separate maintenance and juvenile growth food

Animal `growth` content now accepts `feeding_model: "separate"`. The default
`"shared"` preserves the earlier model and saved playable definitions have not
been changed. In separate mode the existing per-animal food allowance is the
maintenance requirement for every living animal. Adults do not receive a growth
charge. Juveniles may request an additional daily growth ration.

The order is resource maintenance, stored maintenance food, maintenance hunts,
maintenance scavenging, juvenile growth meals, reserve top-ups, then decay and
demographics. Newborns enter after feeding and first request growth food the next
day. Animals that mature stop requesting growth food the next day. Only a
population whose maintenance is fully covered requests growth food; an unmet
growth request slows growth without being treated as maintenance starvation.
The gate uses aggregate local species nutrition, not individual feeding identity.

For each juvenile, the requested daily growth food is:

`adult_mass * (1 - newborn_mass_fraction) / days_to_adult / biomass_gain_per_food_kg`

This is a fixed daily allowance until adulthood. Some allowance can be unused
biologically on the last growth day; physical intake is still recorded. Actual
retained biomass cannot exceed the paid growth-food budget, and maintenance
intake is not reused for somatic growth. Growth meals share remaining local
resources proportionally using existing dietary preferences. Explicit scavenging
diets govern carcass access, including predator first access and specialist
exclusions. No scavenging ability is inferred, no extra hunts are triggered for
growth, and stored reserves remain a maintenance buffer. A hunter that lacks a
compatible resource or explicit scavenging diet cannot fund its extra growth
meal through a new hunting round in this slice.

This remains an aggregate model. Juvenile maintenance uses the existing full
per-animal allowance, not body-mass scaling. Growth does not yet include maternal
gestation/lactation costs, age-specific hunt statistics, or preferential juvenile
starvation. The schema supports separate feeding for any species; the comparison
below changes only species referenced by a prey diet to hold predator food rules
fixed while investigating prey recruitment.

## Recorded evidence

`DailyFoodWebResult.growth_meals` retains required and consumed growth food,
physical sources, juvenile count, and carcass consumption. Maintenance coverage
and growth food remain separate. Reports show juvenile growth food explicitly;
resource expenditure and carrion scavenging include that intake exactly once.
The diagnostic records monthly growth requests and intake alongside breeding
adult counts, live biomass and carcass budgets. Flat daily regions support local
resource growth meals; carrion remains a habitat-based feature.

## Comparison and reproduction

Nine runs compare existing shared rations, the earlier whole-prey ration floor,
and separate juvenile growth meals, using seeds 104729, 7 and 23 for 36 months.
All other factors are fixed: 300 starting hares, 2,000 Red Grass, small guild,
eight maximum abundance-search opportunities, reference prey 60, food-paid
condition recovery, reproduction threshold 0.9, 30 base-output days of plant
stock, 90% monthly carrion loss and nominal 90-day growth with newborn mass 0.1.
These are provisional sensitivity settings, not species life-history calibration.
Same-seed variants may diverge in encounter draws.

All nine three-year runs completed and reconciled their ledgers. The six shared
and whole-population-floor controls reproduce the previous investigation's
monthly species, resource and carcass evidence exactly. Year-three comparisons:

| Profile | Both hunters remain at month 36 | Both scavengers remain | Hunt carrion in year three | Starvation carrion in year three |
|---|---:|---:|---:|---:|
| Existing shared ration | 0/3 | 0/3 | 0–100 kg | 16–36 kg |
| Whole-prey ration floor | 1/3 | 0/3 | 0–189 kg | 297–727 kg |
| Juvenile-only growth meals | 3/3 | 3/3 | 1,327–1,337 kg | 16 kg |

Separate mode ends with six Jackals, one Caracal, one Hyena and one Vulture in
each seed. Hares end at 318–322, including 77–79 adults. However, year-three hare
births total only 184–189 against 379–382 predation deaths, so this is not evidence
of steady replacement. Guineafowl end at 758, of which 482 are juvenile, and
receive only about 229 kg of 6,290 kg requested year-three growth food. Unmet
growth demand is a real supply constraint even when maintenance coverage is full.
Monthly carcass residuals remain below 1.43e-13 kg. These results warrant a longer
continuation before changing playable defaults.

A separate audit confirms the previously documented sensitivity of age-loss
allocation to cohort grouping. In a representative population of 77 adults and
242 juveniles split into 121 two-animal cohorts, the current single-loss rule
removes an adult although adults comprise only about 24% of the population.
This is a deterministic example, not a measured age distribution of individual
hunts in the experiment. Repeated adult-biased losses can affect recruitment;
that allocation needs investigation before compensating with food or birth-rate
changes. The age-loss rule is unchanged in this slice.

Follow-up: [adult/juvenile loss allocation](age-loss-allocation.md) corrects the
grouping-sensitive rule and reruns the five-year scenario with unchanged food
settings. Results below remain historical evidence for the previous allocation.

## Five-year continuation

Three additional 60-month separate-mode runs use the same seeds and inputs.
They reject an equilibrium interpretation of the three-year survival result:

| Date | Hare population across seeds | Adult hares | Jackals |
|---|---:|---:|---:|
| Month 12 | 413–414 | 310–311 | 2 |
| Month 24 | 512–517 | 209–211 | 4 |
| Month 36 | 318–322 | 77–79 | 6 |
| Month 48 | 0 | 0 | 1 |
| Month 60 | 0 | 0 | 0 |

Year-four hare births total 77–83 against 396–405 predation deaths. Caracal
disappears in months 47–48, and all four guild species have disappeared by month
49 in every seed. Guineafowl reach 1,680–1,700 at month 60; that does not replace
the depleted hare recruitment under the existing prey diets and encounter rules.
All monthly live and carcass ledgers reconcile; the largest absolute carcass
residual in the five-year runs is 8.53e-14 kg.

The maintenance/growth separation is a functioning accounting improvement, not
a balanced scenario. Keep its provisional prey settings experimental. Next audit
repeated small-loss allocation across adults and juvenile cohorts, then calibrate
species-specific recruitment and demand. Maternal costs and age-specific hunt
statistics remain separate follow-up work; do not mask the observed depletion by
granting immediate adult-sized births or unaccounted carcasses.

```powershell
.\.venv\Scripts\python.exe -B -m scripts.investigate_capacity --months 60 --seeds 104729 7 23 --hares 300 --grass 2000 --guilds small --opportunities 8 --abundance-search --paid-recovery --birth-thresholds 0.9 --standing-days 30 --carrion-monthly-loss 0.9 --growth-days 90 --growth-ration-modes separate > docs/separate-growth-food-five-year-results.json
```

```powershell
.\.venv\Scripts\python.exe -B -m scripts.investigate_capacity --months 36 --seeds 104729 7 23 --hares 300 --grass 2000 --guilds small --opportunities 8 --abundance-search --paid-recovery --birth-thresholds 0.9 --standing-days 30 --carrion-monthly-loss 0.9 --growth-days 90 --growth-ration-modes existing floor separate > docs/separate-growth-food-results.json
```

Tests cover mixed-age charges, maintenance priority, growth shortage without
maintenance starvation, competition, habitat isolation, flat regions, explicit
carcass compatibility and first access, resource and carcass ledgers, reserve
priority, birth and maturation timing, saved reports, copied-world replay and
failed-day rollback. A two-month actual scenario test checks the live/carcass
ledgers and separate growth evidence.

Verification: 848 tests pass using checkout-local temporary storage for the
Windows sandbox. Tests distinguish maintenance coverage from extra growth intake;
for a fixed two-animal fixture, January maintenance consumes 62 kg, juvenile
growth consumes 36 kg, and physical resource expenditure is exactly 98 kg.
