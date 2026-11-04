# Population introduction

Pause play, select a habitat, and open **Interventions → Introduce**. Choose a
species and 1–10 animals. The preview shows the unresolved date, healthy arrivals,
local population change, IC balance after spending, and charge recovery. Applying
the action commits immediately without advancing ecology or drawing randomness.

The action costs 4 IC regardless of quantity and consumes one global introduction
charge. It recovers after three unique completed month boundaries, independently
of removal's charge. Introduction shares the IC pool but spends no food stock.
Failed month completion rolls back recovery. These costs and timings are
provisional balance targets.

Eligibility requires the selected habitat to appear in the species definition's
`preferred_habitat_ids`. A species can be introduced when absent locally or added
to an existing population. Missing habitat preferences do not imply eligibility.
No species-name branches or intervention quantity presets are needed. Both
introduction and removal take player-chosen positive integers capped at 10.

The engine validates date, target, quantity, population totals, injury cohorts,
IC, and charge before committing. Existing injuries remain unchanged: arrivals
increase the implicit healthy population. Existing fractional demographic carry
is retained for a living population; stale carry is cleared when repopulating an
empty habitat. Introduction generates no births, deaths, food, or carrion, and
does not guarantee that the habitat can feed the new population.
For species using nutrition, arrivals add no stored food and dilute mean
nutritional stress by their share of the new population. See `docs/nutrition.md`.

Typed dated records appear in notes, daily history, and monthly reports.
Monthly accounting treats introductions separately from births and reconstructs
the pre-intervention opening population for first-day actions:

`ending = starting + births + introductions - removals - deaths`
