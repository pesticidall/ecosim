# Prey recruitment and consumer-demand audit

This slice audits the corrected-age-loss baseline without changing simulation or
playable content. PC checkout: `ecosim-rework`, commit
`8b2c4f5eb6129c944ecc0f3c11e3ead13ad6e7f9`. The baseline suite passed all
861 tests without the laptop temporary-directory workaround. Untracked `spike`
was preserved.

## Effective prey network and locality

Both hunters use `activity_abundance`. `select_habitat_prey` excludes entries with
zero activity overlap before selection; prey abundance cannot overcome that gate.

| Hunter | Explicit prey | Activity overlap | Effective prey |
|---|---|---:|---|
| Black-backed Jackal | Scrub Hare | 1 | Hare |
| Caracal | Scrub Hare | 1 | Hare |
| Caracal | Helmeted Guineafowl | 0 | Excluded |

The scenario loader places all eight animal species in open grassland. Red Grass
also starts there, while Sandpaper Raisin and Umbrella Thorn start in acacia scrub.
Thus current hunter/prey co-location is adequate, but regional plant supply is
not interchangeable with local food. Fruit and browse produced in scrub cannot
fund grassland maintenance or growth. Jackals' explicit fruit diet does not give
them access to that remote production. Regional food totals alone are misleading.

Guineafowl remain unavailable as live prey in all three baselines: they record
zero predation losses over five years. Their growth still competes with hares for
local food, including grass forage. This is a model/content consequence, not a
claim that real nocturnal predators cannot catch diurnal birds.

## Replacement, maturation and demand

Year-four hare results from the corrected-age baseline:

| Seed | Births | Predation deaths | Adults at year end | Maturations | Growth request met |
|---|---:|---:|---:|---:|---:|
| 104729 | 325 | 431 | 165 | 4 | 0.5% |
| 7 | 245 | 516 | 113 | 162 | 33.0% |
| 23 | 191 | 546 | 1 | 170 | 64.4% |

Maturations are reconstructed as ending adults minus starting adults plus known
adult deaths. This inference applies to these intervention-free runs with known
ages; it must not be applied to legacy unclassified deaths or introductions.
Growth coverage is total consumed growth food divided by total requested growth
food, not an average of monthly percentages. Requests are gated by maintenance
coverage, so this ratio is not an estimate of every juvenile's latent food need.

Hares have no starvation deaths in any of the three runs. Nevertheless, fully
covered maintenance does not imply adequate growth or replacement. In seed 104729,
year-three hare growth receives only 6.9% of its request; year four receives 0.5%.
Only four animals mature in year four while 111 adults die from predation. The
adult breeding pool falls from 272 to 165. Guineafowl growth is also constrained:
only 3.6% of requested year-three growth food is delivered in every seed.

All three runs have more hare predation deaths than births in year four. Seed 23
has appreciable maturation but still loses 375 adults and 171 juveniles that year.
The bottleneck therefore differs in severity by seed: both recruitment supply and
consumer losses matter; growth shortage alone is not a complete explanation.

| Seed | Year-four hunter maintenance demand (kg) | Hunt carcass biomass (kg) |
|---|---:|---:|
| 104729 | 784.1 | 694.0 |
| 7 | 939.9 | 1401.0 |
| 23 | 1294.9 | 1636.9 |

These columns are not a closed food budget. Carcasses also feed scavengers and
reserves, incur decay, and are distributed across dates; maintenance demand omits
food-paid recovery. A yearly carcass surplus does not guarantee daily food access.
Carcass biomass uses recorded selected-age mass, not adult mass times kill count.

## Next controlled experiment

Keep corrected loss allocation, hunt statistics and age-mass accounting fixed.
First vary local producer supply privately to measure whether additional growth
food improves maturation and birth replacement across seeds. Record local rather
than only regional resource stocks. Then separately test an explicitly justified
prey-network/activity content change; adding guineafowl to a diet alone will not
bypass zero activity overlap. Avoid changing producer supply, fertility and prey
access together in the first comparison because their effects become inseparable.

Assess at least five years across the established seeds, including breeding
adults, maturation, births versus deaths, growth-food delivery, hunter demand,
scavenger persistence and all accounting checks. Longer persistence is evidence
for further testing, not equilibrium. Maternal costs and age-specific hunting
remain separate model changes. No playable settings or checklist items changed.

## Source and reproduction

Source inspected: `simulation/predator_diet.py`, `simulation/activity.py`,
`simulation/habitats.py`, `simulation/scenario_loader.py`,
`simulation/daily_demographics.py`, `simulation/growth_feeding.py`,
`scripts/investigate_capacity.py`, explicit animal/producer content, and
`scenarios/playtest_b_food_web.json`. Historical growth reports were read with
their supersession notices; the numerical audit uses only corrected-age evidence.

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -q
.\.venv\Scripts\python.exe -B -m scripts.investigate_capacity --months 60 --seeds 104729 7 23 --hares 300 --grass 2000 --guilds small --opportunities 8 --abundance-search --paid-recovery --birth-thresholds 0.9 --standing-days 30 --carrion-monthly-loss 0.9 --growth-days 90 --growth-ration-modes separate
```

PC reproduction completed: all three 60-month runs match the archived runs exactly, including every monthly record. All diagnostic accounting checks passed. Raw input byte fingerprints differ across checkouts; the cause was not established. The PC fingerprints and annual prey calculations are retained in `prey-recruitment-audit-results.json`. Annual population identities and nonnegative inferred maturation were independently checked; no unclassified prey deaths occur in this evidence.
