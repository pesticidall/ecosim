# Playtest B food-web roster

Select **Playtest B — Food Web**. Seed 104729 starts all seven requested B animals,
three plant producers, termite colonies, and Scrub Hares retained as supporting
prey. Earlier scenarios remain available, including the termite-free feed trial.

Caracal explicitly hunts hares and guineafowl. Brown Hyena has a primarily
scavenging role plus fruit and meat feed; White-backed Vulture scavenges and
accepts meat feed, with flight/soaring capability. The other four B species retain
their existing diets. Generic diet labels do not select actions. All numerical
values remain provisional gameplay values, not calibrated ecology.

Jackal and Caracal now use local abundance and activity overlap when choosing
among their explicit prey entries. Their search budget now responds to eligible
local abundance, capped at four member opportunities per animal per round; see
`docs/abundance-search.md`. Stage/supply diagnostics and temporary budget/demand
experiments are documented in `docs/encounter-investigation.md`.

Both hunters also opt into a separate concealed-approach stage: habitat vegetation
and shelter help them approach unseen, opposed by prey perception and group
awareness. Producer populations still do not generate dynamic cover. See
`docs/cover-investigation.md` for the rules and subsequent balance results.

The four carnivore/scavenger species now opt into bounded food reserves and
recoverable nutritional condition. Caracal also explicitly accepts carcasses of
its listed prey. See `docs/nutrition.md` for rules and the subsequent balance runs.

Redgrass is renamed **Red Grass** while retaining `redgrass`. **Umbrella Tree**
retains `umbrella_thorn`. Existing plant output remains grass/seeds, leaves/fruit,
and leaves/seed pods respectively. Raisin berries use the existing generic Fruit
resource. Intended ground cover, shrub cover, and tree shade are not yet dynamic
effects of producer populations; existing habitat conditions govern hunting.

Termite Colony is a separate `colony` entity in `content/colonies/`, stored in
`colony_populations` on regions and habitats. It reuses the validated production
shape: `amount_per_producer_per_day` means per colony here. Local production
replenishes Termites; starting stores follow production capacity. Output currently
uses the same weather multiplier as other production. Colonies do not yet grow,
deplete, consume plants, or support interventions; eating termite biomass does
not reduce colony count. This supplies the specialist without an invented plant.

Carrion continues to use habitat-local carcass deposits with source species,
mass, decay, and first access. No duplicate generic carrion food resource is added.
Brown Hyena hunting and additional opportunistic diets remain future refinements.

IC now recovers **2 per completed month**, capped at 10. Feed refills and separate
charge recovery timings are unchanged.

## Verification and initial balance evidence

A year-long integration test applies all three interventions, spends the initial
10 IC, rejects further spending, and checks monthly population accounting,
regional/local totals, nonnegative resources/carrion, injury bounds, and recovery.
Three-month replay tests compare results and random state.

Unintervened exploratory runs over 12 months:

| Seed | Hunt attempts | Secured outcomes | Scavenged biomass |
|---|---:|---:|---:|
| 104729 | 203 | 17 | 194.57 kg |
| 7 | 209 | 22 | 207.47 kg |
| 23 | 175 | 10 | 173.26 kg |

All completed, but jackals, caracals, hyenas, and vultures reached zero by year
end while prey increased. Aardwolves ended at five in each run. This exposes a
balance problem rather than proving stability. Investigate hunting success, food
demand, starvation timing, and carrion access before tuning. Multi-year testing
and a broader seed sample remain outstanding.

The follow-up investigation and reproducible counterfactual runs are documented
in `docs/balance-investigation.md`, with raw results in
`docs/balance-investigation-results.json`.

## Biological role references

- [SANBI Caracal assessment](https://speciesstatus.sanbi.org/taxa/detail/1974/)
  supports small-mammal and bird prey roles.
- [Brown hyaena diet study, Koedoe](https://koedoe.co.za/index.php/koedoe/article/view/968)
  supports primarily scavenging with supplemental fruit and other foods.
- [Kalahari Research Centre bird guide](https://kalahariresearchcentre.org/wp-content/uploads/2016/05/KMP_Bird_Guide_light.pdf)
  describes White-backed Vulture carrion feeding.

These sources support broad roles, not balance numbers. Supplementary meat
acceptance is a gameplay abstraction, not wildlife feeding guidance.
