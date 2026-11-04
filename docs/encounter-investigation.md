# Encounter, hunt-success, and scavenger-supply investigation

## Saved change

Jackal and Caracal now opt into `encounter_model: activity_abundance`. Other
definitions retain preference-only selection. The opt-in model weights an
explicit prey entry by:

`diet preference × sqrt(available local population) × activity overlap`

Same-species availability excludes the hunter. Zero-overlap prey is omitted
because the current detection model already makes those encounters impossible.
If nothing is eligible, selection returns no encounter and consumes no random
draw. Otherwise it consumes exactly one seeded selection draw. Candidates retain
local counts, dietary preference, activity overlap, and normalized probabilities.
Log-space normalization avoids overflowing products. Traits do not select prey.

Abundance changes relative prey choice, not the number of hunt opportunities or
the probability of a particular detection roll. Activity remains an input to
detection as before; no stage guarantees success. Inactive resting prey is not
modeled, so nocturnal predators cannot target strictly diurnal prey through this
model. Those cases require a future distinction between activity and vulnerability.

`hunting_attempts_per_animal` is an optional integer from 1–8, default 1. A round
has population × configured attempts of member opportunities. Each group member
spends one per attempt; solo hunters spend one. Rounds stop when the daily
requirement is met or prey is unavailable. Repeated attempts may use the same
living animal; fatigue/energy costs are not modeled. The value is a per-round
budget, and the daily runner invokes one round per date. Saved roster values
remain at the default: increased opportunities are experiments only.

## Reproduce and inspect

```powershell
.\.venv\Scripts\python.exe -B -m scripts.investigate_balance --months 12 --seeds 104729 7 23 --profiles prior_encounters baseline attempts_two scavenger_demand_half attempts_two_demand_half > docs/encounter-investigation-results.json
```

`prior_encounters` retains nutrition/carcass feeding but disables the new selector.
`baseline` uses saved content. Other profiles temporarily give hunting species two
opportunities per animal, halve food demand for scavenging-only species, or do both.
These diagnostic changes never write content. Saved hunt statistics, demand,
birth rates, opportunity counts, starting populations, and resource production
remain unchanged. Input fingerprints identify the source used for a run. The
same seed does not preserve identical random encounters once runs diverge.

Raw results retain conditional stage reach/pass counts and probability sums,
carcass consumption by source species, reserve deposits/draws, and a physical
carrion budget. The maximum absolute carrion-budget discrepancy over all fifteen
year-long runs is approximately 7.1e-14 kg: no unexplained biomass loss appears.

## First month, seed 104729

With saved encounters, Caracal directs all 57 attempts toward active hares rather
than wasting some on zero-overlap guineafowl. Its detection stage passes 20 times,
chase 7, contact 5, and detention 4. Mean conditional probabilities are about
40.2%, 47.2%, 70.0%, and 63.4%, respectively. Their product is roughly 8.4%; this
is a rough pipeline estimate, not an unconditional probability derived from
independent fixed encounters. Each attempted stage uses its actual saved inputs.
Jackals secure 7 prey in 60 attempts. Raising opportunities to two gives Caracal
8 secured prey from 106 attempts, but does not guarantee more successes for every
predator in each seed.

The saved scenario's starting monthly food demand is:

| Guild member | Population × individual demand | Total |
|---|---|---:|
| Jackal | 4 × 12 kg | 48 kg |
| Caracal | 2 × 18 kg | 36 kg |
| Brown Hyena | 2 × 30 kg | 60 kg |
| Vulture | 3 × 8 kg | 24 kg |
| Total | | 168 kg |

January predation generates only 38.5 kg of carcasses. Another 13 kg comes from
starvation deaths. First meals use 9.73 kg, scavenging including storage uses
36.77 kg, 5 kg remains, and decay is zero. The ledger reconciles exactly within
floating-point precision. Demand totals decline as animals die, so 168 kg is the
starting-population requirement, not the month's realized surviving demand.

At the starting 60 fully fed hares, their monthly birth expectation of 0.12
replaces about 7.2 hares, or 25.2 kg of modeled body mass per month. This is a
local initial estimate, not an equilibrium calculation: population, births,
injuries, and deaths evolve daily. The guild is oversized relative to renewable
eligible prey at these initial settings. Other body mass is present, but diets,
activity, and locality determine access. Fruit exists in the scrub while these
consumers start in grassland. Predator/scavenger starvation carcasses are a
temporary subsidy, not a sustainable source.

## Year-long comparisons

Across seeds 104729, 7, and 23:

| Profile | January Caracal coverage | Year-end guild result |
|---|---|---|
| Prior encounters | 16.3–28.3% | All four species extinct |
| New saved encounters | 22.6–27.5% | All four species extinct |
| Two opportunities | 36.2–65.8% | Hunters/hyenas extinct; one vulture remains |
| Half scavenger demand | 25.1–32.1% | Hunters/hyenas extinct; one vulture remains |
| Both experiments | 40.3–73.6% | Hunters/hyenas extinct; one vulture remains |

The selector removes mechanically futile targets and responds to local abundance,
but is not a balance cure. Increased opportunities improve food income in some
runs; lower scavenger demand reduces competition. Neither experiment supports a
self-sustaining guild within the tested year. A remaining vulture can still be
living off old carcasses; persistence is not proof of stable reproduction.

## Next balance slice

Build a scenario matrix that varies initial prey biomass, producer-supported
prey replacement, and guild size alongside bounded opportunities. Check grass
and seed budgets rather than adding animals that the plant base cannot feed.
Measure prey depletion, reproduction, carcass provenance, and multi-year guild
persistence. Only then choose provisional opportunity/demand values. Avoid
boosting every hunt stage or creating carcasses to keep scavengers alive.

The matrix is now tested: `docs/capacity-investigation.md` records 48 year-long
screens and 12 three-year follow-ups. Persistence in the low-producer cases is
dominated by starvation carrion, exposing the missing absolute encounter-density
mechanism rather than establishing a balanced scenario.
