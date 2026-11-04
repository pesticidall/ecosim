# Playtest B

## Goal

Playtest B should turn EcoSim's producer-herbivore resource model into an observable terrestrial food web. It should demonstrate that predators, prey, scavengers, groups, traits, habitats, movement, time of day, weather, and simple territorial pressure can interact without requiring species-specific system code.

## Starting Scenarios

- [ ] At least three scenarios are available from the main menu
- [x] Playtest A - Balanced Beginnings remains available as a comparison scenario
- [x] The comparison scenario preserves its Playtest A behavior during Playtest B
- [ ] A predator-focused scenario demonstrates hunting, injury, carrion, and scavenging
- [ ] A habitat-focused scenario demonstrates refuge, movement differences, and territorial pressure
- [ ] Every scenario has a known random seed
- [ ] Every scenario explains which Playtest B systems it is intended to demonstrate

## Expanded Modular Content

- [x] Additional animal definitions load without system-code changes
- [x] Predator and scavenger species are represented
- [ ] Additional herbivores fill distinct ecological niches
- [x] Additional producer and resource definitions are represented
- [x] Additional terrestrial habitats and weather types are represented
- [ ] Optional creator attribution can be stored in entity definitions
- [ ] Creator attribution is informational and has no simulation effect
- [x] Invalid Playtest B entity fields produce understandable errors

## Animal Statistics and Size

- [ ] Species definitions provide the statistics required by hunting and defense
- [ ] Power, defense, health, mobility, perception, stealth, and intelligence have distinct purposes
- [ ] Body size and mass influence only calculations where structural scale or physical mass is relevant
- [x] Species statistics are assigned independently without a mandatory total-point budget
- [x] Weight classes remain separate from general body-size categories
- [x] Larger animals are not universally superior to smaller animals
- [x] Species-level statistics remain separate from live population conditions

## Taxonomy

- [x] Taxonomic groups are defined as modular JSON content
- [x] Taxonomic definitions identify their rank and parent taxon
- [x] Animal definitions can reference their lowest defined taxon
- [x] EcoSim can resolve an animal's taxonomic lineage
- [x] Missing parents and circular taxonomic relationships are rejected
- [x] The first required mammalian lineages are represented
- [x] Taxonomy supplies overridable biological defaults rather than rigid behavior
- [x] Taxonomy can organize species information without determining ecological success

## Traits

- [ ] A small catalog of mechanically meaningful starting traits exists
- [x] Taxonomic groups can provide default starting traits
- [x] Species can add starting traits of their own
- [x] Species can override inappropriate taxonomic defaults
- [x] Traits modify specific simulation calculations rather than acting as decorative labels
- [ ] Trait effects are visible in detailed reports
- [x] Traits do not provide unexplained universal stat bonuses

## Calendar and Activity Phases

- [x] Simulation time advances through named months and years
- [x] Twelve monthly cycles advance the year
- [x] One ecological timestep represents one completed calendar day
- [x] One reporting and player-review period represents one completed month
- [x] A headless daily-advance operation resolves one date without depending on the interface
- [x] Running a month repeatedly advances daily ecological steps through that month's actual length
- [x] The current date identifies the next unresolved day so interventions never apply retroactively
- [x] The simulation can pause between daily steps and resume without changing ecological results
- [x] Immediate interventions apply on the current unresolved date and record that exact date
- [x] The simulation stops at month end for report and calendar review before the next month begins
- [ ] Ecological processes declare whether they resolve daily, accumulate across days, or resolve at month or year boundaries
- [x] Every simulated day contributes to an aggregated monthly day activity total
- [x] Every simulated day contributes to an aggregated monthly night activity total
- [x] Animal definitions can describe diurnal, nocturnal, crepuscular, or flexible activity
- [ ] Activity overlap influences ecological encounters
- [ ] Simulation results do not depend on presentation or animation speed
- [x] Seasons are not presented as functional until they have ecological effects
- [x] Months use their conventional lengths from 28 to 31 days
- [x] February contains 29 days during leap years
- [x] Leap years follow the Gregorian divisible-by-4, 100, and 400 rules
- [x] A completed monthly cycle records its month, year, and number of days
- [x] Completed monthly totals are stored as structured historical data
- [x] The same month can be compared across different years
- [x] Producer growth uses daily rates so unequal month lengths produce proportionally different growth

Daily-loop migration has begun with `feed_region_for_day`. Existing animal
`food_requirement_per_animal_per_cycle` values remain monthly allowances; one
date allocates `1 / days_in_month(year, month)` of that demand. With a fixed
population and sufficient food, a full month's daily allocations sum to the
existing monthly allowance, including leap-year February. Resource feeding
remains habitat-local and records its exact date. This is a mutating stage to
invoke once per region and date; it does not advance the calendar or complete
the day. `feed_region_food_web_for_day` now composes resource feeding, solo or
group hunting, and scavenging in that order using the same daily demand.
Survivor nutrition is rebased after predation without refunding food already
eaten. Shared meals use daily member demand, and scavengers supplement only
the remaining deficit while preserving predator first access. Both operations
are alternatives: invoke the food-web operation instead of separately invoking
resource feeding for the same date. Hunt opportunity budgets are currently
bounded by the starting predator population for each invoked round.

`resolve_region_daily_ecology` now composes daily weather selection, one day's
producer output, the daily food web, and carrion decay in that order. Weighted
weather is selected once for the region and affects both production and hunts.
Fixed or absent weather consumes no random draws. A monthly carrion loss `f`
becomes daily loss `1 - (1 - f) ** (1 / days_in_month)`, preserving the monthly
retention of unconsumed carrion. Losses of zero and one remain zero and one.
Returned evidence records the actual date and selected weather. This regional
stage replaces separate calls to production, feeding, decay, and demographics
for that date. Demographics now resolve after decay: starvation expectation is
`current population * (1 - nutrition) / month length` for definitions without
the optional nutrition model, followed by birth
expectation `surviving population * monthly birth rate * nutrition / month length`.
Fractional changes carry across dates and month boundaries in habitat-local
state (or regional state when habitats are absent). Whole animals are applied
as they accumulate; extinction clears pending fractions. These daily changes
use the current population, so they do not reproduce the legacy monthly rounding
rule. Small floating-point errors within `1e-12` of a positive whole change are
normalized before applying it. Newborns enter the healthy population and start
feeding on the next date. Injury cohorts are reconciled after starvation, and
new starvation carrion is unreserved and appears after today's decay. Legacy
definitions missing a birth rate contribute no births; missing adult mass does
not invent carcass biomass. The regional stage still does not advance the
calendar or record a completed day itself.

The four starting carnivore/scavenger definitions now opt into physiological food
reserves and recoverable nutritional condition. Storage takes actual surplus
food after daily meals; withdrawals buffer later deficits. Deficit-days govern
starvation pressure separately from health, injuries, and demographic rounding.
Caracal explicitly accepts its prey species' carrion. Snapshots and reports retain
reserve and condition evidence. See `docs/nutrition.md` for the provisional rules,
mass accounting, and three-seed comparisons; year-end guild collapse remains an
unresolved food-income problem.

The headless `run_day` orchestrator now resolves the current unresolved date
across all regions in stable order. It stages state and randomness privately,
then commits only after every region succeeds. A failed stage leaves the live
world, random stream, calendar, and completed-day history unchanged, allowing a
safe retry. Success records a `DailyCycleResult` under
`daily_history[year][month][day]` and advances the calendar exactly once. Completed
dates cannot be replayed. Region and habitat object references and immutable
history-record identities are preserved across commits. A 35-day scenario
verifies month rollover and equivalent results after pause and copied-state
resume. The legacy monthly runner remains available for untouched months and
refuses a partially completed month. Daily stepping leaves its monthly cycle
counter and monthly report history unchanged.

`summarize_month` now builds a read-only monthly summary from complete daily
history, rejecting missing dates, mismatched dates, or inconsistent region sets.
Daily records retain population, resource, carrion, and injury snapshots; the
summary takes its boundaries from the first and last saved days rather than live
world state. It sums production, births, starvation, predation, hunt outcomes,
scavenging, decay, and weather day counts. Food coverage combines daily survivor
nutrition weighted by demand. Physical resource consumption is tracked separately
from each day's stock changes and production, retaining food eaten by prey that
subsequently die. `format_monthly_ecology_report` presents this evidence without
running ecology again or drawing randomness. Summaries retain the actual dated
daily records for later event inspection.

`run_day` now automatically stores a complete month's structured report in
`monthly_summaries[year][month]` and sets `pending_month_review` when its last date
finishes. Summary generation is part of the final day's transaction: failure
leaves that date unresolved and safe to retry. The calendar points to the next
month's first unresolved date, but daily and legacy monthly advancement are
blocked until `acknowledge_month_review` releases the review pause. Acknowledging
does not resolve any ecology or consume randomness. `run_month` repeatedly invokes
daily stepping to finish the current month, retaining any already completed
prefix, and returns the stored summary. Calls while review is pending return
that same summary without advancing. Previously completed days remain committed
if a later date fails. Month advancement requires history from the month's first
date. Direct daily stepping from an initial partial month does not invent a full
report for its missing earlier dates. Legacy monthly history and cycle numbering
remain separate. The headless review flow is implemented; graphical review
controls and calendar presentation still need interface wiring.

## Habitats

- [x] A region can contain multiple terrestrial habitats
- [x] Habitats can provide different resources, shelter, and encounter conditions
- [x] Animal populations can enter accessible habitats and prefer some without being locked out of others
- [ ] Habitat use affects predator-prey encounter likelihood
- [ ] Refuge habitats can improve prey survival without guaranteeing it
- [x] Habitat state remains separate from its content definition
- [ ] No aquatic habitat is required for Playtest B

## Movement

- [x] Animals have a primary movement mode or movement profile
- [x] Base mobility remains separate from environmental mobility modifiers
- [x] Habitats can modify movement modes differently
- [x] Weather can modify movement modes differently
- [ ] Movement compatibility affects chase and escape calculations
- [x] Starting traits can reduce specific movement penalties
- [ ] Playtest B movement does not require region-to-region pathfinding

## Hunting and Predator Feeding

Jackal and Caracal now use the optional concealed-approach stage after detecting
prey. It resolves their stealth and available habitat concealment against prey
awareness, then applies a bounded chase starting-distance advantage if unnoticed.
Group awareness moves out of initial detection for opted-in hunters to avoid
counting that response twice. Producer-driven cover and physical refuge remain
unfinished. See `docs/cover-investigation.md` for rules, tests, and year-long results.

- [x] Predators select compatible prey from modular diet data
- [x] Hunting contains detection, chase, attack, and restraint or escape stages
- [ ] Each hunting stage uses relevant statistics, traits, habitat, and weather conditions
- [x] Prey power contributes to defense or breaking free after contact
- [x] A successful attack does not automatically guarantee a kill
- [ ] Prey can escape unharmed or injured
- [ ] Predators can be injured by dangerous prey
- [x] Successful kills create edible biomass
- [x] Predators consume secured prey biomass
- [x] Predator nutrition affects starvation and reproduction
- [x] Hunt results explain why each stage succeeded or failed

## Groups

- [x] Predator populations can form hunting units
- [x] Prey populations can form defensive groups or herds
- [x] Group members belong to the same species, region, and habitat
- [x] Group detection reflects predator stealth and prey awareness
- [x] Intelligence contributes to group coordination
- [x] Group power uses diminishing returns
- [x] Group kills are divided among participating predators
- [x] Group food requirements include every member
- [x] Larger prey groups gain defensive benefits and increased resource demand
- [x] Group behavior responds to ecological conditions rather than permanent pack or herd labels

The monthly hunting scheduler supports optional positive integer animal fields
`max_hunting_group_size` and `max_defensive_group_size`, both defaulting to one.
These are capability ceilings for temporary local encounters. Hunting units are
bounded by current population, remaining food demand, and the round's participant
budget. Defensive gatherings respond to the selected prey population's current
habitat nutrition. The initial balance rule is
`ceil(min(local population, defensive ceiling) * nutrition ratio)`, with at least
the targeted animal retained. Food shortages therefore disperse defensive groups
without removing animals or reducing their individual food requirements. A caller
without feeding context retains the population and capability limits. Larger
groups gain the existing coordination and defensive support benefits while every
animal still contributes to local resource demand. These formation rules remain
subject to playtest balancing. Each secured prey creates one death and a shared
meal; remaining carrion is released for scavengers.

## Injuries and Conditions

- [x] Animal populations can contain healthy and injured members
- [x] Minor and major injuries have distinguishable consequences
- [ ] Injuries can affect mobility, hunting, escape, feeding, or mortality
- [ ] Hunting can injure predators as well as prey
- [x] Injuries persist beyond the event that caused them
- [ ] Injury counts cannot exceed the relevant population
- [ ] Detailed anatomy and individual medical simulation are not required

## Carrion and Scavenging

- [x] Hunting and other deaths can create carrion biomass
- [x] Predators can leave unconsumed remains
- [x] Compatible scavengers can consume carrion
- [x] Multiple consumers can compete over a carcass
- [x] Carrion decays through a simple understandable rule
- [ ] Carrion quantities cannot become negative
- [ ] Detailed decomposition and nutrient cycling are not required

## Territorial Disputes

- [ ] Territorial pressure can arise from scarce food, shelter, carcasses, or breeding access
- [ ] Disputes can occur within the same species
- [ ] Disputes can occur between competing species
- [ ] Predators and herbivores can both participate in disputes
- [ ] Displays and retreat can resolve disputes without combat
- [ ] Escalated disputes can cause injury or displacement
- [ ] Territorial behavior responds to current conditions rather than one permanent Boolean label
- [ ] Explicit mapped territory boundaries are not required

## Weather

- [x] Active weather modifies at least producer output, visibility, or mobility
- [x] Weather effects can differ by habitat or movement mode
- [x] Weather effects are data-driven and understandable
- [ ] Weather contributes to hunting calculations where relevant
- [ ] Weather effects appear in detailed reports
- [ ] Random weather transitions are not required unless added without expanding the scope

## Structured Events and Live Updates

- [ ] Simulation systems produce structured events for meaningful changes
- [ ] Daily events record the calendar date on which they actually occur
- [x] A monthly calendar is built from actual daily event history rather than distributing monthly totals across invented dates
- [ ] Weather, interventions, hunts, major injuries, deaths, and other notable changes can appear on their resolved dates
- [ ] Production, feeding, hunts, injuries, deaths, births, carrion, and disputes can create events
- [ ] Live updates and end-of-month reports use the same underlying event data
- [ ] Common population activity is aggregated rather than printed once per animal
- [x] Important events can be filtered by category
- [ ] Faster simulation speeds reduce presentation detail without changing results
- [ ] Maximum speed can resolve a cycle without waiting for animations

## Graphical Interface

- [x] A graphical dashboard provides the Playtest B player interface
- [ ] An animated EcoSim title can be skipped or disabled
- [x] A main menu allows scenario selection
- [ ] The current month, year, weather, and activity phase are visible
- [x] The current unresolved calendar date is visually prominent while a month runs
- [ ] A progress indicator represents elapsed calendar days rather than computation or loading progress
- [x] Population and resource values can update while a cycle is presented
- [x] A recent-event feed highlights meaningful changes
- [x] Pause and simulation-speed controls operate between daily ecological steps
- [x] The normal player flow can run an entire month without requiring manual advancement of every day
- [x] Presentation speed changes how quickly completed days are shown without changing simulation outcomes
- [x] Month completion enters a stable review state until the player begins the next month
- [ ] Reduced-motion and plain-text fallbacks are available
- [x] The interface remains separate from simulation calculations

The initial desktop shell launches with `.\.venv\Scripts\python.exe playtest_b.py`.
It uses Tkinter and the existing scenario catalog, with habitat selection,
local population and injury counts, resources, carrion, weather, a prominent
unresolved date, and daily notes or the completed monthly report. A controller
invokes the existing headless daily operation once per scheduled callback.
Pause cancels the next callback; speed changes only the delay between dates.
Month-end review requires acknowledgement before either daily or month play can
continue. Latest daily notes now explain recorded ecological changes, and a
History tab browses completed dates and stored monthly reports without changing
simulation state. A selected historical date remains open across later steps;
the latest-day option follows the run. Views use saved daily evidence, including
solo and group hunt stages, contact injuries, deaths, and carrion flows. A visual
calendar grid remains pending. Supplementary-food actions now record their exact
unresolved date, selected habitat, resource, and added biomass. The desktop
requires paused play; the headless action validates all quantities and local
dietary compatibility before updating habitat and regional stocks. No ecological
step or random draw occurs when applying food. Completed daily records and monthly
reports retain these actions, and failed daily ecology can retry without applying
the food twice. Food deployment now charges IC and reserve stock atomically;
future scheduling is still deferred. This is the functional
shell; illustrated habitats and the remaining visual design are still pending. The terminal
launcher remains available independently. See `docs/desktop-shell.md`.

### Supplementary-food capacity and IC foundation

The handoff and subsequent reserve decisions supersede the earlier cost/refill
targets. These values remain provisional balancing targets:

- Global IC starts at 10, caps at 10, and recovers 2 per completed month.
  Unused IC carries forward. Balances and spending use half-point increments.
- Herbivore feed starts at and caps at 1000 kg, refilling 100 kg per month.
- Carnivore feed starts at and caps at 500 kg, refilling 50 kg per month.
- Food deployment uses positive 50 kg increments. The current shared provisional
  price is `ceil(amount_kg / 100)` IC: 50–100 kg costs 1 IC, 150–200 kg costs 2 IC,
  and 1000 kg costs 10 IC. Carnivore deployment cannot exceed its available stock.
- Separate food reserves do not determine compatibility or create carrion;
  compatible consumers must use physical habitat food through ordinary feeding.
- Slow remains the default presentation speed, independent of ecological outcomes.

`InterventionResources` is immutable global world state. Headless spending and
food-reservation helpers validate the full debit before returning replacement
state. They do not deposit food or alter ecological outcomes. Recovery happens
inside the successful final daily transaction of a complete recorded month,
before month-end review. A retained year/month stamp prevents duplicate recovery,
including further spending followed by another recovery request for that month.
Balances cap independently. Failed days and report generation leave resources
unchanged; review acknowledgement and the following month's first date do not
recover them again. An initial partial month without complete daily history does
not grant a monthly recovery event. Legacy Playtest A monthly execution is separate.
Daily results retain before/after resource snapshots for future reporting.

Add food now commits the IC debit, reserve debit, physical deposit, and dated
record together after a fresh full-action preview validates them. The desktop
starts at 50 kg, uses a 50 kg stepper, displays current IC and both reserves, and
previews cost and remaining balances. Invalid or unaffordable actions are disabled
and rejected headlessly without spending resources or drawing randomness. Each
record has a deterministic event ID, feed type, IC spent, and immutable budget
snapshots. Resource definitions opt into deployment through the validated
`supplementary_feed_type` field; ordinary diet entries still determine ecological
compatibility. Untagged resources remain valid for ordinary feeding. Existing
plant resources use the herbivore reserve. Carnivore Feed now has a resource
definition, an explicitly compatible Black-backed Jackal diet, and a controlled
Playtest B trial scenario. Aardwolf content accepts only termites; insectivore
is a descriptive diet label and does not select feeding behavior. Ordinary diet
entries enforce compatibility without species-specific branches. The trial
intentionally lacks termite supply and is not a balanced ecosystem. Meat deposits
do not create carrion or death records. Resource food
persists under the existing store/consumption rules; separate food-decay behavior
has not been invented for this slice.

Population Removal is now implemented with a global single charge, fixed 3 IC
cost, and recovery after two completed month boundaries. Recovery uses the same
exactly-once month stamp as IC and reserves. The action applies immediately on
the unresolved date while desktop play is paused. Players choose 1–10 animals
per action, limited further by local population for removal. Species definitions
need no intervention presets. This replaces the earlier species-defined counts.

The Interventions tab previews the habitat, date, chosen count, local population
change, IC cost, and charge availability before the explicit apply button.
Validation precedes all population, cohort, IC, charge, and history changes.
Removed animals leave the simulation without generating carrion or death records.
Injury cohorts are allocated proportionally among survivors; partial removal
retains aggregate fractional carry, while local extinction clears it. Daily
history and monthly reports use the same typed intervention records. Monthly
population ledgers distinguish removal from mortality and reconstruct the
pre-removal opening population for first-date actions. Scenario loading now
selects a populated habitat when one exists. See `docs/population-removal.md`.

Population Introduction is implemented at 4 IC with one
independent charge and recovery after three unique completed month boundaries.
It shares IC with other interventions but does not debit feed stocks or the
removal charge. Recovery uses the existing transactional month-completion path;
duplicate recovery requests and review actions cannot advance the cooldown.
These remain provisional balance targets. Players choose 1–10 healthy arrivals
in the Interventions tab's Introduce panel. Eligibility uses the species'
preferred_habitat_ids, including eligible species not currently present locally.
Arrivals update local and regional populations without creating births or
carrion. History and monthly reports record introductions separately from births
and removals, including reconstruction of the opening population for first-day
actions. See `docs/population-introduction.md`.

## Reporting

- [ ] Monthly summaries remain concise and readable
- [x] Players can inspect a calendar of dated weather, interventions, hunts, injuries, deaths, and other notable events
- [x] Day and night activity can be distinguished when relevant
- [ ] Hunt stages and outcomes are understandable
- [ ] Predator feeding and food shortages are understandable
- [ ] Injuries, carrion, scavenging, grouping, and disputes are summarized
- [ ] Detailed reports expose important modifiers and calculations
- [x] A complete run report can still be exported locally
- [ ] Reports include scenario, seed, build, content, and ending-state information
- [ ] Full diagnostic data preserves exact values even when the terminal rounds them

## Reliability and Performance

- [x] Playtest A behavior remains covered by regression tests
- [ ] Every Playtest B scenario can complete multiple years without crashing
- [x] The same seed, scenario, content, and settings reproduce the same results
- [ ] Simulation speed and skipped animations do not change ecological results
- [ ] Populations, group counts, injury counts, resources, and carrion cannot become negative
- [ ] Zero-population species and empty habitats do not crash a cycle
- [ ] Exported reports contain enough information to reproduce a run
- [ ] Live presentation can be disabled for automated and headless tests
- [ ] Performance is measured before increasing population detail

## Deliberately Excluded

### Individuals and Evolution

- Full individual-organism simulation
- Individual aging, sex, family relationships, and social memory
- Detailed pregnancy, egg laying, and juvenile development
- Acquired-trait counters
- Mutation-point allocation and stat redistribution
- Trait inheritance and population genetics
- Adaptation, regional divergence, and speciation
- Detailed dominance hierarchies and remembered rivals

Playtest B may track population-level condition counts and hunting units, but most animals remain aggregated populations rather than persistent individuals.

### Regions, Water, and Geography

- Multiple simultaneously simulated connected regions
- Procedural geography and world generation
- Region-to-region migration and pathfinding
- Lakes, ponds, rivers, wetlands, oceans, and aquatic ecosystems
- Changing coastlines, river courses, glaciers, or terrain
- Explicit mapped territorial boundaries
- Caves and underground regional connections

Playtest B establishes terrestrial habitats within fixed regions. Playtest C can extend the habitat foundation to basic freshwater features.

### Seasons and Advanced Environment

- Functional seasons
- Seasonal producer dormancy and reproduction
- Seasonal migration
- Seasonal day-length changes
- Latitude and hemispheres
- Dawn and dusk as separate simulation phases
- Moon phases and detailed light levels
- Long-term climate change
- Complex disturbances and disasters

Playtest B uses named months, years, and aggregated day and night phases. Seasons should first appear when they produce visible ecological consequences.

### Advanced Ecology

- Disease, parasites, and vectors
- Pollination
- Detailed decomposition and nutrient cycling
- Complex plant health and competition
- Ecosystem engineering
- Detailed territorial memory and boundary maintenance
- Sophisticated interspecific alliances
- Full life-cycle simulation
- Mass extinction and recovery

Playtest B focuses on terrestrial food-web interactions: hunting, escape, injury, groups, carrion, scavenging, habitat use, and simple disputes.

### Interface and Player Systems

- A rendered two-dimensional or three-dimensional world map
- Final graphical user interface
- Required mouse interaction
- Hover tooltips over rendered entities
- Individual animal tagging and naming
- Field Guide completion mechanics
- Save and load
- World creator
- Tutorial campaign
- Full player-intervention system
- Scheduled and automatically recurring interventions
- Final graphics, audio, and accessibility implementation

Playtest B's simple interventions occur immediately on the current unresolved calendar date. Players can pause a running month before applying an intervention, but future-date scheduling and recurring automation remain outside this playtest.

Playtest B uses a graphical player interface rather than the previously planned Rich terminal interface. Structured events, reports, calendar, and controls remain independent of presentation. Headless execution and terminal diagnostics remain available for development and automated testing.
