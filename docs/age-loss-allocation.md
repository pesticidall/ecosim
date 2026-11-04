# Adult and juvenile loss allocation

The previous largest-remainder calculation rounded each event independently
across one adult bin and all juvenile cohorts. An adult bin could therefore win
every single-animal loss while a much larger juvenile population was fragmented
across many small cohorts. This affected reproduction and carcass supply.

`simulation/growth.py` now uses animal-count-weighted systematic sampling without
replacement for a loss batch. Exact equal-mass juvenile cohorts are merged and
mass bins sorted before selection, so splitting or reordering equivalent cohorts
does not change the selected ages or removed biomass. Adults are not weighted by
their larger body mass.

Each local species has a saved `growth_loss_phases` value, initially 0.5. After a
committed loss of `count` animals, the phase advances by
`count * 0.6180339887498949`, modulo one. Rotating the offset prevents repeated
small events from always selecting the same quantile. This is deterministic
aggregate allocation, not an independent random draw or a modeled preference
for a particular prey age. It adds no draws to the hunting random stream.
Batch sampling and repeated individual losses need not choose identical ages;
both conserve animal counts and the exact mass of their selected animals.

In a fixed-composition test with 77 adults and 242 juveniles, 10,000 single losses
select 2,414 adults, close to the population share of 2,413.79. The test replaces
each removed animal at the same age to hold composition fixed. This is a
regression example, not a universal error bound for changing populations.

## Commit and evidence

Single hunts, group hunts, daily starvation and player removal use the same pure
loss planner and commit helper. Carcass creation previews the current phase;
the corresponding population subtraction uses that phase and advances it once.
Zero-loss injury changes do not advance it. Phases survive maturation and healthy
introductions while the local population remains, and clear at local extinction.
All-adult populations without age state retain their existing mass accounting.

An untracked all-adult population does not need a saved cursor until juvenile
cohorts exist. Once tracked, the cursor persists even through adult-only periods,
so future cohorts do not reset the event history.

Daily snapshots retain phases as well as juvenile cohorts. They are copied by
daily staging, so failed days leave both phase and hunting randomness unchanged.
Death records optionally retain `adult_count` and `juvenile_count`, validated
to sum to the death count. Older records without known age remain unclassified;
the diagnostic explicitly separates those counts rather than inventing ages.
Removal still creates no deaths or carrion.

Age and injury cohorts remain independent aggregate marginals. The selected age
does not alter contact, chase or detention statistics in this slice. This corrects
loss accounting without claiming an individual joint age/injury participant
model or biological age-specific vulnerability. No food, growth, fertility,
hunting-success or species-name rules were changed to improve survival.

## Comparison and validation

Three 60-month runs repeat the prior separate-growth-food profile with seeds
104729, 7 and 23. All other inputs are held fixed: 300 starting hares, 2,000 Red
Grass, small guild, eight maximum abundance-search opportunities, reference
abundance 60, food-paid condition recovery, reproduction threshold 0.9, 30 days
of standing plant food, 90% monthly carrion loss and nominal 90-day growth.
The prior five-year results remain archived in
`separate-growth-food-five-year-results.json`; their cohort-loss algorithm is
different, so encounters need not stay paired even with the same seed.

All three five-year runs completed with unchanged parameter values. Results:

| Outcome | Previous event-local rounding | Rotating count-weighted allocation |
|---|---:|---:|
| Adult hares at month 36 | 77–79 | 206–272 |
| Hare births in year four | 77–83 | 191–325 |
| Hares at month 60 | 0 in all seeds | 169 / 0 / 0 |
| Both hunters present at month 60 | 0/3 | 1/3 |
| Both scavengers present at month 60 | 0/3 | 0/3 |

Month-60 hare counts are listed for seeds 104729, 7 and 23. In seed 104729, six
Jackals and two Caracals remain alongside 169 Hares (37 adults), while Hyena and
Vulture disappeared in month 22. In seed 7 all guild species disappear by month
56; in seed 23 all disappear by month 51. The previous allocation lost the whole
guild by month 49 in every seed. This is improved breeding-adult retention, not
evidence of equilibrium or uniformly improved scavenger survival.

Recorded year-four hare predation now separates 111 adult / 320 juvenile losses
in seed 104729, 274 / 242 in seed 7 and 375 / 171 in seed 23. These proportions
reflect different evolving populations and do not establish biological age
preferences. Younger carcasses also change feeding, hunt counts and subsequent
random-draw histories; same-seed events are not matched experiments.

Every monthly population, age-count, live-biomass and carcass ledger reconciles.
The maximum absolute monthly carrion residual is 8.53e-14 kg. The raw result file
retains adult, juvenile and unclassified deaths by cause as well as prey and food
records. Food settings and saved playable content remain unchanged.

Next assess species-specific recruitment, consumer demand and the explicit prey
network with this corrected allocation held fixed. Age-specific vulnerability
and maternal costs remain separate model work; neither is silently inferred by
the new sampler.

```powershell
.\.venv\Scripts\python.exe -B -m scripts.investigate_capacity --months 60 --seeds 104729 7 23 --hares 300 --grass 2000 --guilds small --opportunities 8 --abundance-search --paid-recovery --birth-thresholds 0.9 --standing-days 30 --carrion-monthly-loss 0.9 --growth-days 90 --growth-ration-modes separate > docs/age-loss-allocation-results.json
```

Verification: 861 tests pass using checkout-local temporary storage. New tests
cover fragmentation/order invariance, repeated small losses, integer and mass
conservation, pure previews, shared single/group carcass selection, starvation
age records, removal and extinction, phase persistence through maturation,
replay and failed-day rollback, and actual scenario live/carcass and age totals.
