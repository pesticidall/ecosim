# Carnivore feed compatibility trial

Launch the desktop shell with `.\.venv\Scripts\python.exe playtest_b.py`, select
**Playtest B — Carnivore Feed Trial**, and load it. Select **Open Grassland** and
choose **Carnivore Feed** under supplementary food.

The scenario adds two Black-backed Jackals, twenty Scrub Hares, and one Aardwolf
to the existing savanna. The new species use already-defined taxonomy. Jackals
have explicit resource-food, prey, and scavenging diets, plus the existing bite
method and a two-member hunting ceiling. Animal statistics, food requirements,
birth rates, and encounter preferences are initial gameplay balance values.

Carnivore Feed is kilogram biomass tagged for the carnivore reserve. A 50 kg
deployment costs 1 IC, consumes 50 kg from that reserve, and changes only the
selected habitat's food store and its regional aggregate. Ordinary feeding can
satisfy the jackals' daily demand before they attempt to hunt. Compatibility is
explicit: hares do not eat meat, and the aardwolf accepts only the separate
untagged termite resource. Neither species gains a generic survival bonus.

This is a controlled compatibility trial, not a balanced food web. It intentionally
has no termite supply or termite production. The aardwolf therefore remains
underfed even when meat is supplied. A termite food resource is defined so an
actual local supply can satisfy its normal feeding calculations, but modeling
invertebrate supply is outside this slice. No artificial termite-producing plant
or automatic specialist rescue has been added.

Meat and carrion remain distinct. Adding feed creates no predation death,
carcass, or reservation; existing reserved carcasses retain their first-access
rules. Deployed food persists under ordinary resource-store rules. Separate
feed decay remains deferred. The existing Playtest A animal diets and scenarios
are unchanged.

Integration tests load this actual content/scenario, verify stock/IC charging,
locality, normal consumption, specialist exclusion, reserved-carrion independence,
proportional competition using a test-only additional compatible consumer, seeded
monthly results, population accounting, and desktop deployment. Both supplemented
and unsupplemented monthly runs are exercised.

## Diet rationale

- [SANBI: Black-backed jackal](https://www.sanbi.org/gardens/hantam/wildlife-and-biodiversity-2/black-backed-jackal/)
  describes generalist omnivory, predation, scavenging, and occasional cooperative
  hunting. This supports an explicitly meat-compatible generalist model.
- [SANBI: Aardwolf assessment](https://speciesstatus.sanbi.org/taxa/detail/2196/)
  describes specialization on harvester termites and obligate insectivory. This
  supports excluding generic meat from its provisional simulation diet.

These sources support broad dietary distinctions, not the numerical balance
values or the nutritional suitability of any real captive-animal feed formulation.
