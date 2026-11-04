# Juvenile growth and carcass accounting

Animal definitions may opt into `growth` with `newborn_mass_fraction` (finite,
strictly between zero and one), `days_to_adult` (positive integer), and optional
`biomass_gain_per_food_kg` (finite, positive, at most one; default 0.25). Adult
mass must be defined. Definitions without growth retain legacy demographics.
Saved playable animal content has not yet been assigned provisional growth rates.

The optional `feeding_model: "separate"` now supports physical juvenile-only
growth meals in addition to maintenance. See [separate growth food](separate-growth-food.md)
for its stage ordering, accounting and limitations. The shared-ration description
below remains the default behavior when that setting is omitted.

Initial scenario animals and population introductions are adults. Births create
habitat-local immutable juvenile cohorts at the configured fraction of adult
mass. The untracked remainder of the local population consists of adults.
Juveniles do not reproduce. A juvenile that reaches adult mass becomes eligible
to reproduce the following day. No species-name branches select growth behavior.

Growth runs after feeding and starvation, before newborn cohorts are added.
Unfed juveniles do not grow. Daily potential growth is adult mass times
`(1 - newborn_mass_fraction) / days_to_adult`, scaled by food coverage. Actual
retained biomass is further capped by juveniles' equal per-capita share of food
consumed times `biomass_gain_per_food_kg`. Intake allocated to adults or animals
that starved is not reassigned to juvenile growth. Each juvenile receives the
same absolute growth allowance, capped by its remaining distance to adult mass.
Unused allowance from a maturing animal is not reassigned that day.
Thus `days_to_adult` is a minimum fully-fed duration, not a guaranteed calendar
maturation date when food intake constrains growth.

Food demand deliberately remains the existing full per-animal allowance, including
juveniles, as a conservative maintenance-and-growth ration. This does not implement
a complete energy conversion, maternal gestation/lactation cost, or body mass loss
under starvation. Newborn biomass is an explicit reproduction source in the live
biomass ledger, rather than being hidden as immediate adult biomass. The default
retention coefficient and diagnostic newborn fraction are provisional assumptions.

Losses now use count-weighted systematic allocation with a saved rotating phase;
see [adult/juvenile loss allocation](age-loss-allocation.md). This replaces the
original event-local largest-remainder rule, which could favor adults when
juveniles were fragmented into small cohorts. No random draws are added.
Injury and growth cohorts are independent population marginals,
not individual identities. Single and group hunts record the mass removed by this
allocation; multi-animal starvation records store the removed animals' mean mass.
Carrion creation, first meals and leftovers then use those recorded quantities.
Population removal reconciles cohorts without making carrion; introductions add
adults while preserving existing juveniles.

The hunt's contact, chase, detention, and group-selection statistics still use
species-level definitions. This slice corrects carcass mass and maturation, not
age-specific hunting competence or vulnerability. Extending those statistics
requires an explicit joint participant-age model rather than guessing ages from
injury cohorts.

## Evidence and verification

Saved daily snapshots retain local growth cohorts. Daily demographic evidence
retains starting live biomass, starvation biomass, somatic growth, newborn biomass,
and ending live biomass. The diagnostic checks each daily growth ledger and the
full monthly living biomass ledger, including predation, alongside existing
population, resource, injury and carrion checks.

Verification: 826 tests pass using the checkout-local temporary-directory
workaround for the Windows sandbox. Existing uncommitted work was preserved.

Tests cover food-limited and zero-food growth, maturation, adult-only reproduction,
newborn mass, full food charges, proportional losses, juvenile starvation carrion,
single and group kills, removals, adult introductions, snapshots, deterministic
replay, and failed-day rollback. A real scenario test runs two months and checks
both live and carcass accounting.

The diagnostic's `--growth-days 0` preserves existing growth content; positive
values apply a private uniform maturation duration and newborn fraction 0.1 to
animals. This sensitivity test is not a calibrated species life-history model.

Six three-year runs compare the control with a uniform minimum 90-day maturation
period, using three seeds and the same 30-day plant stock limit and 90% monthly
carrion loss as the previous investigation. Results in year three:

| Profile | Starvation carrion created | Hunt carrion created | Carrion stock at month 36 | Guild species present at month 36 |
|---|---:|---:|---:|---:|
| Immediate adult births | 4,941–4,943 kg | 0–3.5 kg | 127–136 kg | All four in 3/3 runs |
| Food-limited juvenile growth | 16–36 kg | 0–100 kg | 3.81 kg | None in 3/3 runs |

With growth enabled, Brown Hyena and Vulture disappear in months 17–18, Caracal
in months 18–28 and Jackal in months 22–29. Final hare populations are 15, 2 and
121 for seeds 104729, 7 and 23, versus 1,115–1,116 in the controls. Guineafowl
end at 212 rather than 653–654. Live and dead biomass checks passed every month;
maximum absolute carrion residual was 1.99e-13 kg.

This experiment changes both the immediate body mass of births and reproductive
eligibility, so it does not isolate their individual effects. It also applies one
provisional growth profile to every animal, with actual maturation constrained by
food and body mass. The results expose a food-web shortage once rapid reproductive
and carcass subsidies are removed; they do not establish realistic life histories
or a balanced population target. Saved animal definitions remain unchanged.

Next choose explicit species growth/retention values and reassess renewable prey
recruitment against predator demand with maternal reproductive costs made explicit.
Do not restore guild survival by increasing carcass mass or granting juveniles
immediate reproduction. Age-specific hunt participants can follow after the
aggregate demographic supply is credible.

Correction: [growth feasibility and recruitment](recruitment-rations.md) found
that the original limited-food allocation could keep near-adult cohorts juvenile
indefinitely as younger cohorts arrived. That calculation is now corrected to
allocate equal absolute growth per juvenile before capping at adulthood. The
archived results above used the older allocation and must not be used as current
balance evidence; the follow-up reruns the controls and records breeding adults.

```powershell
.\.venv\Scripts\python.exe -B -m scripts.investigate_capacity --months 36 --seeds 104729 7 23 --hares 300 --grass 2000 --guilds small --opportunities 8 --abundance-search --paid-recovery --birth-thresholds 0.9 --standing-days 30 --carrion-monthly-loss 0.9 --growth-days 0 90 > docs/growth-investigation-results.json
```
