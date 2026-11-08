# Local producer supply sensitivity

This investigation changes only the private scenario's Red Grass count: 2,000
(control), 4,000 and 8,000, each for 60 months with seeds 104729, 7 and 23.
All other corrected-age baseline factors remain fixed: 300 starting hares, small
guild, eight abundance-search opportunities with reference abundance 60,
food-paid condition recovery, reproduction threshold 0.9, 30 base-output days
of standing stock, 90% monthly carrion loss, nominal 90-day growth and separate
juvenile growth meals for explicit prey species. Saved playable defaults are
unchanged. No hunting-success, fertility, activity or age-allocation rule changes.

This is a producer-population sensitivity, not an isolated grass-ration change.
Red Grass supplies both forage and seeds in open grassland. Doubling its count
doubles potential output and standing capacity for both resources. Actual output
can be smaller when standing stock is full. Seasonal Rain multiplies production
by 1.25, but standing capacity remains based on unmodified daily output.

| Red Grass | Potential forage kg/day | Potential seeds kg/day | Forage capacity kg | Seed capacity kg |
|---|---:|---:|---:|---:|
| 2,000 | 20 | 5 | 480 | 120 |
| 4,000 | 40 | 10 | 960 | 240 |
| 8,000 | 80 | 20 | 1,920 | 480 |

The diagnostic now retains monthly starting and ending resource stocks per
habitat, local ending populations and producer counts. These are stock snapshots,
not daily local production/consumption ledgers. A regression test checks regional
reconciliation, consecutive-month continuity and the separation of grassland
animals from acacia-scrub fruit. Existing simulation accounting checks remain in
place. Candidate configuration inspection confirms that only Red Grass count
differs; starting resource quantities and all definitions are identical.

## Results

All nine five-year runs completed. At month 60, counts below are ordered by seeds
104729 / 7 / 23:

| Red Grass | Hares | Adult hares | Both hunters present | Entire four-species guild present |
|---|---|---|---|---|
| 2,000 | 169 / 0 / 0 | 37 / 0 / 0 | 1/3 | 0/3 |
| 4,000 | 2,166 / 398 / 378 | 504 / 153 / 150 | 3/3 | 2/3 |
| 8,000 | 4,698 / 1,972 / 1,913 | 1,422 / 930 / 922 | 3/3 | 3/3 |

More local producer supply improves persistence and supports more recruitment,
but does not demonstrate equilibrium. Year-five hare replacement:

| Red Grass | Seed | Births | Predation | Starvation | Maturations | Growth request met |
|---|---:|---:|---:|---:|---:|---:|
| 2,000 | 104729 | 140 | 690 | 0 | 16 | 7.4% |
| 2,000 | 7 | 36 | 203 | 0 | 38 | 100% |
| 2,000 | 23 | 0 | 1 | 0 | 0 | No requests |
| 4,000 | 104729 | 719 | 326 | 446 | 0 | 0.18% |
| 4,000 | 7 | 468 | 1,064 | 0 | 99 | 14.4% |
| 4,000 | 23 | 462 | 1,053 | 0 | 104 | 15.4% |
| 8,000 | 104729 | 2,138 | 446 | 208 | 30 | 1.5% |
| 8,000 | 7 | 1,547 | 934 | 0 | 461 | 28.1% |
| 8,000 | 23 | 1,517 | 920 | 0 | 489 | 30.3% |

The 100% control growth coverage in seed 7 is a small, collapsing population's
remaining requests, not successful replacement: that run reaches hare extinction.

At 4,000 grass, seeds 7 and 23 again lose hares faster than births replace them
in year five. Seed 104729 instead has 446 hare starvation deaths and no hare
maturation. Its scavengers had already disappeared in month 32, despite the
later starvation carcasses. Thus an aggregate carcass increase cannot be read
as evidence of reliable scavenger support.

At 8,000 grass, births exceed total hare deaths during year five in all seeds,
but adult counts fall from 1,642 / 1,040 / 1,006 to 1,422 / 930 / 922. Juvenile
growth-food coverage deteriorates, and seed 104729 also loses 1,392 guineafowl
to starvation. Its year-five starvation carcasses total 1,446.9 kg across species.
The other two seeds produce only 15.3 kg of starvation carcasses each, so full
guild survival cannot universally be attributed to a starvation subsidy.

Guineafowl still have zero predation deaths in every run. At 8,000 grass, seeds
7 and 23 end with 6,472 and 6,546 guineafowl, but year-five growth delivery is
below 0.1% of requests for both. Increasing supply also supports this growing
consumer population without adding a live-prey pathway to the hunters.

At month 60, every run has effectively zero grassland forage and seeds (rounded
to 0.001 kg), while unoccupied acacia scrub retains 24 kg of fruit and 100 kg of
browse. The local snapshots confirm that these regional stores are unavailable
to the grassland consumers; they do not establish continuous daily depletion.

## Verification and next slice

The three controls match every archived run field after removing only the newly
added habitat evidence. All 540 monthly accounting checks completed; the maximum
absolute monthly carrion residual is 2.85e-13 kg (rounded upward). Habitat stocks
sum to regional stocks and match across consecutive month boundaries. Annual
prey population identities reconcile and inferred maturations are nonnegative.
Raw evidence is in `local-producer-supply-results.json`; annual counts, growth
intake, hunter demand and carcass totals are in `local-producer-supply-summary.json`.
Annual calculations sum each consecutive twelve-month block starting at month 1.

All 862 tests pass. The initial sandbox test execution encountered 13 Windows
temporary-directory access errors; the unrestricted rerun passed. No simulation
code, saved content, scenario defaults or checklist completion states changed.

Keep both supply candidates private. This establishes that local food supply
constrains recruitment, while also showing that increasing it alone leaves
declining adult pools and an expanding prey species excluded from hunting.
The next distinct experiment should address explicit prey access/activity at
fixed producer supply, with a clearly specified content assumption and unchanged
hunt-success statistics. Do not silently grant nocturnal hunters access to
inactive birds: changing activity weights affects more than diet selection.
A longer continuation of any candidate considered for promotion remains required.
Maternal costs and age-specific vulnerability remain separate model changes.

## Reproduction

```powershell
.\.venv\Scripts\python.exe -B -m scripts.investigate_capacity --months 60 --seeds 104729 7 23 --hares 300 --grass 2000 4000 8000 --guilds small --opportunities 8 --abundance-search --paid-recovery --birth-thresholds 0.9 --standing-days 30 --carrion-monthly-loss 0.9 --growth-days 90 --growth-ration-modes separate > docs/local-producer-supply-results.json
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -q
```

Growth-food coverage is summed intake divided by summed requests; requests are
gated by maintenance coverage and do not represent all latent juvenile demand.
Inferred maturation is ending adults minus starting adults plus classified adult
deaths, valid here because these runs have no interventions or unknown-age prey
deaths. Yearly carcass biomass and hunter maintenance demand are not interchangeable:
scavengers, recovery, reserves, decay and timing also affect physical food access.
Same-seed variants need not retain paired encounter histories after food changes.
