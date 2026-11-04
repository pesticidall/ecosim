# Carrion turnover investigation

The capacity diagnostic now accepts `--carrion-monthly-loss` as a list of
experimental fractional losses. Omission preserves habitat content; an explicit
zero selects a no-decay control. Overrides apply to a private copy of habitat
definitions, leaving saved content and scenarios unchanged. Invalid, nonnumeric,
boolean, nonfinite, or out-of-range values are rejected.

This uses the existing `carrion_decay_fraction_per_cycle` field and daily decay
engine. The fraction is monthly loss for untouched carrion, converted to a daily
fraction using each month's length. It is not the daily loss fraction. Feeding
and reserve replenishment precede decay, and new starvation carcasses appear
after decay, becoming available the next day. First-access reservations remain
intact. Proportional decay reduces biomass over time; it does not assign a hard
expiry date or remove arbitrarily small remnants.

## Comparison

Nine runs compare monthly loss 0, 0.5 and 0.9 across seeds 104729, 7 and 23, each
for 36 months. Other factors remain fixed: 300 starting hares, 2,000 Red Grass,
small guild, eight maximum abundance-search opportunities, reference abundance
60, food-paid condition recovery, reproduction threshold 0.9, and 30 base-output
days of standing plant food capacity. These rates are sensitivity tests, not
calibrated biological lifetimes. Same-seed cases can diverge in encounter draws.

The saved output retains monthly carcass creation from hunting and starvation,
predator first meals, scavenging (including reserve deposits), decay and remaining
stock. Each monthly carrion ledger must reconcile within 1e-8 kg; population and
local/regional quantity checks also run every month.

All nine runs completed (27 simulated years). All four guild species remained
present through month 36. Results across the three seeds:

| Monthly carrion loss | Year-three starvation carrion | Year-three hunt carrion | Carrion remaining at month 36 |
|---|---:|---:|---:|
| 0% | 4,945–4,952 kg | 0 kg | 5,916–6,000 kg |
| 50% | 4,945–4,948 kg | 0 kg | 367–373 kg |
| 90% | 4,941–4,943 kg | 0–3.5 kg | 127–136 kg |

At 90% loss, year-three scavenging still supplied 1,438–1,479 kg and decay removed
3,435–3,467 kg. Only seed 104729 recorded a secured hunt in year three: one
Caracal kill. The 50% cases recorded no hunt attempts in that year. Reduced
backlogs therefore do not establish a sustained hunting balance: ongoing
starvation production is still sufficient to support the guild. Maximum absolute
monthly carrion ledger residual was 9.10e-13 kg.

For seed 104729 at 90% loss, year-three starvation produced 1,700 kg from 17
Warthogs, 16 kg from two Aardwolves, 799.5 kg from 533 Guineafowl and 2,425.5 kg
from 693 Hares. The same year recorded 11, 2, 486 and 732 births respectively.
The engine currently applies typical adult mass to every death regardless of
age, while births immediately join the aggregate population. These counts do not
identify which dead animals were newborns; they identify the next model
assumption to investigate, not a measured juvenile carcass error.

Keep the tested rates experimental and leave playable defaults unchanged for this
slice. Decay demonstrably removes the permanent carcass stock, but selecting a
rate cannot fix excessive fresh carcass production. Next inspect a lightweight
birth/growth and carcass-biomass model, including its food requirements and
population accounting, before calibrating resource-specific stocks or promoting
balance settings.

## Reproduce

Follow-up: [juvenile growth and carcass accounting](juvenile-growth.md) removes
immediate adult-sized births and juvenile reproduction in an optional model,
then compares six three-year runs with food-limited growth and reconciled live
and carcass biomass.

```powershell
.\.venv\Scripts\python.exe -B -m scripts.investigate_capacity --months 36 --seeds 104729 7 23 --hares 300 --grass 2000 --guilds small --opportunities 8 --abundance-search --paid-recovery --birth-thresholds 0.9 --standing-days 30 --carrion-monthly-loss 0 0.5 0.9 > docs/carrion-turnover-results.json
```

New tests verify private configuration isolation, omission versus explicit zero,
input validation, deterministic populated-world replay with nonzero decay, and
an untouched 100 kg carcass across January and February. At 50% monthly loss it
ends January at 50 kg and February at 25 kg, with exact losses retained in the
monthly evidence. Existing tests cover day-stage order, first access, complete
loss and conversion for all month lengths.

Verification: all 811 tests pass. The ordinary full-suite invocation initially
encountered Windows sandbox temporary-directory permission failures; running the
same discovery suite with `tempfile.tempdir` set to a temporary directory inside
the checkout passed. No engine change was needed to correct decay ordering or
conversion.
