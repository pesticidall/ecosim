# First food-web balance investigation

This is the historical investigation before nutritional reserves were added.
The original JSON remains unchanged. Current behavior, comparison profiles, and
new results are documented in `docs/nutrition.md`. The current script's `legacy`
profile reproduces this baseline; its `baseline` profile now means saved content
with nutritional reserves and caracal carrion eligibility.

The full roster runs to completion but fails to sustain its predators and
scavengers. This investigation retains saved content and simulation rules:
experiments modify private in-memory content copies only. No numerical balance
change is justified as a complete solution by these results.

## Reproduce

From the repository root:

```powershell
.\.venv\Scripts\python.exe -B -m scripts.investigate_balance --months 12 --seeds 104729 7 23 --profiles legacy > docs/balance-recheck-results.json
```

The JSON records content, simulation, and scenario fingerprints, the profile and
seed, monthly populations, births/deaths, food demand/intake/sources, hunt outcomes,
prey choices, zero-activity-overlap attempts, and scavenged biomass. It is an
unintervened experiment, not a comparison of player strategies. Reports project
saved daily/monthly evidence; no extra random draws are used for diagnostics.
Profiles use the same starting seed but can consume different random draws as
their ecology diverges; this is not a paired identical-encounter comparison.

## Baseline: first month, seed 104729

| Species | Start → end | Food coverage | Starvation deaths | Secured / attempts |
|---|---:|---:|---:|---:|
| Black-backed Jackal | 4 → 2 | 33.6% | 2 | 6 / 60 |
| Caracal | 2 → 1 | 8.3% | 1 | 3 / 48 |
| Brown Hyena | 2 → 2 | 58.3% | 0 | No hunting diet |
| White-backed Vulture | 3 → 2 | 53.2% | 1 | No hunting diet |

Caracal fails detection on 40 of 48 attempts. Of all attempts, 24 target prey
with zero modeled activity overlap: nocturnal caracal versus diurnal guineafowl.
The remainder of the hunt pipeline further reduces successful meals.

Caracal demand totals 27.87 kg across its surviving daily population, but it eats
only 2.32 kg. A secured kill supplies at most the current day's deficit; remaining
mass becomes carrion. Its saved definition has no scavenging diet, so it cannot
consume that leftover mass on later dates. Jackals do consume leftover hares,
but still remain well below demand.

Most first-month scavenger intake is not a sustainable flow of hunted prey:
hyenas receive about 11.96 kg of hare biomass out of 34.97 kg total; vultures
receive about 3.95 kg out of 10.85 kg. The remainder comes from dead carnivores
and scavengers. Temporary support from those deaths disappears as the guild dies
out. All four species reach zero by year end in each baseline seed.

## Separate content experiments

| Profile | Change | January caracal coverage: seeds 104729 / 7 / 23 |
|---|---|---:|
| baseline | Saved content | 8.3% / 10.2% / 12.0% |
| caracal_carrion | Allow hare/guineafowl carcass consumption | 20.3% / 43.7% / 24.9% |
| caracal_twilight | Use existing crepuscular activity weights | 24.0% / 16.0% / 12.0% |
| caracal_both | Both changes | 53.4% / 23.9% / 23.3% |

Twilight profiles remove zero-overlap caracal attempts. Carcass consumption
improves access to usable biomass. Nevertheless all four predator/scavenger
species still reach zero in all twelve year-long runs. These omissions contribute
to the problem but do not explain it alone.

Caracal kill revisitation is supported by the
[IUCN Cat Specialist Group](https://www.catsg.org/living-species-caracal), which
describes caching larger kills, and the
[Mammalian Species account](https://academic.oup.com/mspecies/article/52/993/71/6016926).
The trial's general shared carrion feeding does not implement private caches,
ownership persistence, or protected access on subsequent dates.

## System constraints exposed

- Daily nutrition is capped at 100%; no energy reserve carries a successful meal
  across later failed hunting days. Carcass biomass persists, but access to it is
  a separate question from physiological reserves.
- `DemographicCarry.starvation` is fractional expected-mortality rounding carry,
  not body condition. Every food deficit adds to it; fully fed days retain it.
  With low birth rates, even intermittent deficits eventually round to deaths
  in small populations. This follows the implemented daily demographic rule;
  treating it as recoverable condition would be an explicit model change.
- Hunting has a bounded opportunity budget. Group members spend opportunities
  together, and each required stage can fail. More prey does not grant more
  attempts or raise encounter success: current prey population gates availability,
  while dietary preferences weight species choice independently of abundance.
- Fruit supply exists in Acacia Scrub, but these jackals and hyenas start in Open
  Grassland. Resources are local, and the daily loop does not relocate them to
  exploit that fruit. Their dietary entry does not ensure access to it.

## Next implementation order

1. Define food/condition continuity: decide whether B should support recoverable
   nutritional condition, physical meal reserves, or both. Keep it separate from
   health (physiological robustness), injuries, and fractional birth/death rounding.
2. Implement that decision with tests for intermittent feeding, sustained famine,
   replenishment limits, deterministic replay, and real biomass accounting.
3. Refine carcass revisitation and activity-aware encounter selection. Neither
   should force success or let traits select behavior.
4. Re-run the same seed matrix before tuning food demand, hunt opportunities,
   birth rates, initial guild sizes, or the carcass supply supporting scavengers.

Do not lower hunger costs or boost hunt statistics just to preserve every starting
species. The target is understandable and responsive ecology, not guaranteed
survival. Broader seed samples, intervention policies, and multi-year runs follow
the first model correction.
