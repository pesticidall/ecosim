# Standing plant food investigation

Production entries now accept optional `standing_capacity_per_producer`, measured
in the produced resource's own units (kg for the current plant foods). It must be
a finite positive number. Within each habitat, capacities from bounded producers
of the same resource add together. Growth fills remaining headroom; weather scales
the growth rate but does not enlarge capacity. Monthly production records contain
only growth that actually entered the food stock.

Existing stock above capacity is preserved. Production waits for consumption to
make room, so the limit cannot silently delete initial supplies or supplementary
food. This is a growth limit, not spoilage, senescence, or a complete resource
turnover model. Unbounded sources keep producing independently; mixed bounded and
unbounded sources therefore have no finite total limit. Shared existing stock
counts against the bounded sources' headroom.

Definitions without this field retain their previous production calculations.
Saved playable content and scenarios have not been assigned provisional limits.
The diagnostic's `--standing-days` setting multiplies each plant's base daily
output by the supplied number to construct private experimental capacities. It
leaves termite colonies alone. Zero selects the uncapped control. This uniform
duration is a sensitivity test, not a calibrated grass/fruit/leaf lifespan.

## Comparison

The comparison uses 300 starting hares, 2,000 Red Grass, the small guild, abundance
search with eight maximum opportunities and reference abundance 60, food-paid
condition recovery, and reproduction threshold 0.9. Each of the uncapped, 30-day,
and 90-day plant stock profiles runs for 36 months with seeds 104729, 7 and 23.
Resource and population totals, local totals, injury bounds and carrion budgets
are checked monthly. Same-seed variants diverge in random-draw history.

Nine runs (27 simulated years) completed. All four guild species remained present
in all profiles, but survival still depends on starvation carrion. Year-three
totals and the actual final stock, across three seeds:

| Plant stock limit | Starvation carrion created in year 3 | Hunt carrion created in year 3 | Carrion remaining at month 36 |
|---|---:|---:|---:|
| Uncapped | 14,200–14,225 kg | 322–347 kg | 13,089–13,143 kg |
| 30 base-production days | 4,945–4,952 kg | 0 kg | 5,916–6,000 kg |
| 90 base-production days | 6,242–6,409 kg | 0 kg | 7,784–7,855 kg |

The 30-day limit reduced year-three starvation biomass by about 65%. Guineafowl
ended at 653–654 instead of 1,302; hares still ended at 1,116–1,117 instead of
1,120–1,123. Resource backlogs fell: final fruit was 24 kg instead of 1,115 kg,
seed pods 54 kg instead of 2,484 kg. Leaves remained at the original above-capacity
100 kg, which demonstrates that this feature does not remove unused initial food.
Maximum absolute monthly carrion accounting residual was 1.82e-12 kg.

An additional audit found that the saved habitats omit
`carrion_decay_fraction_per_cycle`. The existing decay engine therefore applies
zero decay, and these runs retain old carcasses indefinitely. Capped profiles
recorded no predation deaths in year three despite persistent hunters. Their
continued survival is not evidence of a functioning sustained hunting balance.

Keep the stock limits experimental. Next test nonzero carrion decay using the
existing monthly-to-daily conversion, with explicit carcass budgets; then revisit
the immediate adult-mass treatment of births and starvation carcasses. Calibrate
resource-specific plant capacities after these supply artifacts are understood.

Follow-up: [carrion turnover investigation](carrion-turnover.md) tests nonzero
decay across nine three-year runs. It removes the permanent carcass backlog, but
fresh starvation carcasses still dominate the food supply.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -B -m scripts.investigate_capacity --months 36 --seeds 104729 7 23 --hares 300 --grass 2000 --guilds small --opportunities 8 --abundance-search --paid-recovery --birth-thresholds 0.9 --standing-days 0 30 90 > docs/standing-food-results.json
```

Tests cover saturation, regrowth, above-capacity deposits, pooled capacities,
habitat isolation, weather-independent capacity, mixed sources, schema errors,
private configuration isolation, and deterministic monthly evidence with physical
resource accounting. Full suite: 808 tests pass.
