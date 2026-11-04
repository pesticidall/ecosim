# Growth feasibility and prey recruitment

Before assigning species life histories or adding maternal food costs, check
whether the existing food allowance can physically support the configured growth
rule. This slice adds that diagnostic and a private ration sensitivity test.
It also corrects a growth allocation defect; saved playable animal definitions
remain unchanged.

## Growth budget

`scripts/growth_budget.py` compares the biomass needed to reach adulthood with
the intake available at full nutrition and the configured retained-biomass
coefficient. It reports minimum growth food per day, the ration needed in a
particular month, and the effective optimistic maturation bound. A zero ration
has no finite bound and is recorded as JSON null. Bounds assume full feeding,
no mortality and no competition; real recruitment can be lower.

For newborn fraction 0.1, retention 0.25 and a nominal 90-day growth period:

| Animal | Existing monthly food | Food-limited maturation bound in a repeated 30-day month | Ration supporting the target even in a 31-day month |
|---|---:|---:|---:|
| Scrub Hare | 0.5 kg | 756 days | 4.34 kg |
| Helmeted Guineafowl | 0.25 kg | 648 days | 1.86 kg |

These are implications of EcoSim's current equations, not biological estimates.
Changing `days_to_adult` alone cannot bypass the food budget. The previous
extinction experiment therefore combined reduced carcass mass, adult-only
reproduction and a large intake-driven delay in replacement adults. Its outcome
does not establish that hunting success alone is insufficient.

The audit also exposed an implementation defect: the earlier calculation scaled
each cohort's remaining growth when food was limited. With a stream of younger
cohorts, near-adult cohorts could approach adulthood asymptotically without
reaching it. Growth now allocates equal absolute mass gain per juvenile, then
caps each gain at adult mass. Unused allowance at maturation is not reassigned
that day. The food budget remains an upper bound and no random draws are added.
A mixed-cohort regression test verifies that a near-adult animal matures on
schedule even with many younger juveniles competing for the growth budget.

## Controlled comparison

The capacity diagnostic accepts `--growth-ration-modes existing floor`. The floor
mode raises only the food allowances of species referenced by a `prey_diet` to
at least their 31-day growth budget. It discovers prey from data and has no
species-specific engine branches. Predator and scavenger rations, initial food,
producer output, birth rates, growth conversion and hunting rules stay fixed.
Higher demand must be satisfied by the ordinary local feeding system; no food
is created to make the new target feasible.

The floor applies to the whole prey population, including adults. This is a
conservative sensitivity test under the existing feeding model, not an
age-specific ration implementation or a proposed final balance setting. It can
reduce carrying capacity and alter competition, starvation and carrion supply
at the same time that it permits faster fully-fed juvenile growth. It does not
isolate maturation from all food-web effects. Maternal costs remain unmodeled.

Each run now retains growth budgets for all month lengths and monthly adult and
juvenile counts, alongside the existing live-biomass, population, resource and
carcass ledgers. This makes a population increase distinguishable from an
increase in breeding adults.

## Results after correcting growth allocation

Six runs completed, each for 36 months, with seeds 104729, 7 and 23. All use
300 starting hares, 2,000 Red Grass, the small guild, eight maximum abundance
search opportunities, reference abundance 60, food-paid condition recovery,
reproduction threshold 0.9, 30 base-output days of standing plant stock, 90%
monthly carrion loss and nominal 90-day juvenile growth. Same-seed variants may
diverge in their random encounter histories.

| Outcome | Existing prey rations | Prey ration floor |
|---|---:|---:|
| Hares at month 36 | 2–124 | 113–144 |
| Adult hares at month 36 | 0–83 | 85–120 |
| Adult Guineafowl at month 36 | 109 | 73–125 |
| Year-three starvation carrion | 16–36 kg | 297–727 kg |
| Year-three hunt carrion | 0–100 kg | 0–189 kg |
| Both hunters remain at month 36 | 0/3 runs | 1/3 runs |
| Both scavengers remain at month 36 | 0/3 runs | 0/3 runs |

In the floor profile, seed 104729 retains one Jackal and one Caracal, 85 adult
and 28 juvenile Hares, and records 54 secured hare deaths in year three. Seeds
7 and 23 lose both hunters by months 13–14. Hyena and Vulture disappear in months
9–13 in all floor cases. The floor therefore does not establish robust guild
survival. All population, live-biomass and carcass checks passed; the largest
absolute monthly carrion residual was 1.43e-13 kg.

The growth fix matters independently of ration tuning. With existing rations,
Guineafowl now finish with 109 adults and 162 juveniles, rather than the archived
old-allocation result of 40 adults and 172 juveniles. Corrected control hunters
still disappear by months 18–29 and scavengers by months 17–18. The earlier raw
growth investigation remains archived with a correction notice; this file's
controls supersede it for current-model comparisons.

Keep the ration floor experimental. The next implementation should separate
adult maintenance allowance from juvenile growth demand, recording physical
intake for both. Then test species-specific recruitment and producer capacity
together. Maternal reproductive costs are still needed, but layering them onto
the currently inconsistent shared ration would obscure this constraint further.
There is no evidence here for increasing hunt success or restoring adult-sized
births. Saved playable defaults remain unchanged.

Follow-up: [separate juvenile growth food](separate-growth-food.md) implements
the opt-in maintenance/growth split, records actual physical growth meals, and
compares all three ration models while preserving the earlier controls.

## Reproduce and validation

```powershell
.\.venv\Scripts\python.exe -B -m scripts.investigate_capacity --months 36 --seeds 104729 7 23 --hares 300 --grass 2000 --guilds small --opportunities 8 --abundance-search --paid-recovery --birth-thresholds 0.9 --standing-days 30 --carrion-monthly-loss 0.9 --growth-days 90 --growth-ration-modes existing floor > docs/recruitment-ration-results.json
```

Tests compare the analytical budget with actual cohort maturation across 28–31-day
months, cover zero and invalid food budgets, verify private-config isolation and
unchanged predator/scavenger allowances and starting supplies, and replay a real
scenario while checking adult-plus-juvenile totals and carcass accounting.

Verification: 832 tests pass using checkout-local temporary storage for the
Windows sandbox. This includes the mixed-age limited-food maturation regression.
