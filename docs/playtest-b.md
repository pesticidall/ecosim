# Playtest B

## Goal

Playtest B should turn EcoSim's producer-herbivore resource model into an observable terrestrial food web. It should demonstrate that predators, prey, scavengers, groups, traits, habitats, movement, time of day, weather, and simple territorial pressure can interact without requiring species-specific system code.

## Starting Scenarios

- [ ] At least three scenarios are available from the main menu
- [ ] Playtest A - Balanced Beginnings remains available as a comparison scenario
- [ ] The comparison scenario preserves its Playtest A behavior during Playtest B
- [ ] A predator-focused scenario demonstrates hunting, injury, carrion, and scavenging
- [ ] A habitat-focused scenario demonstrates refuge, movement differences, and territorial pressure
- [ ] Every scenario has a known random seed
- [ ] Every scenario explains which Playtest B systems it is intended to demonstrate

## Expanded Modular Content

- [ ] Additional animal definitions load without system-code changes
- [ ] Predator and scavenger species are represented
- [ ] Additional herbivores fill distinct ecological niches
- [ ] Additional producer and resource definitions are represented
- [ ] Additional terrestrial habitats and weather types are represented
- [ ] Optional creator attribution can be stored in entity definitions
- [ ] Creator attribution is informational and has no simulation effect
- [ ] Invalid Playtest B entity fields produce understandable errors

## Animal Statistics and Size

- [ ] Species definitions provide the statistics required by hunting and defense
- [ ] Power, defense, health, mobility, perception, stealth, and intelligence have distinct purposes
- [ ] General body-size categories establish base stat totals
- [ ] Weight classes remain separate from general body-size categories
- [ ] Larger animals are not universally superior to smaller animals
- [ ] Species-level statistics remain separate from live population conditions

## Taxonomy

- [ ] Taxonomic groups are defined as modular JSON content
- [ ] Taxonomic definitions identify their rank and parent taxon
- [ ] Animal definitions can reference their lowest defined taxon
- [ ] EcoSim can resolve an animal's taxonomic lineage
- [ ] Missing parents and circular taxonomic relationships are rejected
- [ ] The first required mammalian lineages are represented
- [ ] Taxonomy supplies overridable biological defaults rather than rigid behavior
- [ ] Taxonomy can organize species information without determining ecological success

## Traits

- [ ] A small catalog of mechanically meaningful starting traits exists
- [ ] Taxonomic groups can provide default starting traits
- [ ] Species can add starting traits of their own
- [ ] Species can override inappropriate taxonomic defaults
- [ ] Traits modify specific simulation calculations rather than acting as decorative labels
- [ ] Trait effects are visible in detailed reports
- [ ] Traits do not provide unexplained universal stat bonuses

## Calendar and Activity Phases

- [ ] Simulation time advances through named months and years
- [ ] Twelve monthly cycles advance the year
- [ ] Every month contains an aggregated day activity phase
- [ ] Every month contains an aggregated night activity phase
- [ ] Animal definitions can describe diurnal, nocturnal, crepuscular, or flexible activity
- [ ] Activity overlap influences ecological encounters
- [ ] Simulation results do not depend on presentation or animation speed
- [ ] Seasons are not presented as functional until they have ecological effects

## Habitats

- [ ] A region can contain multiple terrestrial habitats
- [ ] Habitats can provide different resources, shelter, and encounter conditions
- [ ] Animal populations can occupy compatible habitats within a region
- [ ] Habitat use affects predator-prey encounter likelihood
- [ ] Refuge habitats can improve prey survival without guaranteeing it
- [ ] Habitat state remains separate from its content definition
- [ ] No aquatic habitat is required for Playtest B

## Movement

- [ ] Animals have a primary movement mode or movement profile
- [ ] Base mobility remains separate from environmental mobility modifiers
- [ ] Habitats can modify movement modes differently
- [ ] Weather can modify movement modes differently
- [ ] Movement compatibility affects chase and escape calculations
- [ ] Starting traits can reduce specific movement penalties
- [ ] Playtest B movement does not require region-to-region pathfinding

## Hunting and Predator Feeding

- [ ] Predators select compatible prey from modular diet data
- [ ] Hunting contains detection, chase, attack, and restraint or escape stages
- [ ] Each hunting stage uses relevant statistics, traits, habitat, and weather conditions
- [ ] Prey power contributes to defense or breaking free after contact
- [ ] A successful attack does not automatically guarantee a kill
- [ ] Prey can escape unharmed or injured
- [ ] Predators can be injured by dangerous prey
- [ ] Successful kills create edible biomass
- [ ] Predators consume secured prey biomass
- [ ] Predator nutrition affects starvation and reproduction
- [ ] Hunt results explain why each stage succeeded or failed

## Groups

- [ ] Predator populations can form hunting units
- [ ] Prey populations can form defensive groups or herds
- [ ] Group members belong to the same species, region, and habitat
- [ ] Group detection reflects predator stealth and prey awareness
- [ ] Intelligence contributes to group coordination
- [ ] Group power uses diminishing returns
- [ ] Group kills are divided among participating predators
- [ ] Group food requirements include every member
- [ ] Larger prey groups gain defensive benefits and increased resource demand
- [ ] Group behavior responds to ecological conditions rather than permanent pack or herd labels

## Injuries and Conditions

- [ ] Animal populations can contain healthy and injured members
- [ ] Minor and major injuries have distinguishable consequences
- [ ] Injuries can affect mobility, hunting, escape, feeding, or mortality
- [ ] Hunting can injure predators as well as prey
- [ ] Injuries persist beyond the event that caused them
- [ ] Injury counts cannot exceed the relevant population
- [ ] Detailed anatomy and individual medical simulation are not required

## Carrion and Scavenging

- [ ] Hunting and other deaths can create carrion biomass
- [ ] Predators can leave unconsumed remains
- [ ] Compatible scavengers can consume carrion
- [ ] Multiple consumers can compete over a carcass
- [ ] Carrion decays through a simple understandable rule
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

- [ ] Active weather modifies at least producer output, visibility, or mobility
- [ ] Weather effects can differ by habitat or movement mode
- [ ] Weather effects are data-driven and understandable
- [ ] Weather contributes to hunting calculations where relevant
- [ ] Weather effects appear in detailed reports
- [ ] Random weather transitions are not required unless added without expanding the scope

## Structured Events and Live Updates

- [ ] Simulation systems produce structured events for meaningful changes
- [ ] Production, feeding, hunts, injuries, deaths, births, carrion, and disputes can create events
- [ ] Live updates and end-of-month reports use the same underlying event data
- [ ] Common population activity is aggregated rather than printed once per animal
- [ ] Important events can be filtered by category
- [ ] Faster simulation speeds reduce presentation detail without changing results
- [ ] Maximum speed can resolve a cycle without waiting for animations

## Terminal Interface

- [ ] Rich provides the first styled terminal interface
- [ ] An animated EcoSim title can be skipped or disabled
- [ ] A main menu allows scenario selection
- [ ] The current month, year, weather, and activity phase are visible
- [ ] A progress bar represents progress through the current month
- [ ] Population and resource values can update while a cycle is presented
- [ ] A recent-event feed highlights meaningful changes
- [ ] Pause and simulation-speed controls are available
- [ ] Reduced-motion and plain-text fallbacks are available
- [ ] The interface remains separate from simulation calculations

## Reporting

- [ ] Monthly summaries remain concise and readable
- [ ] Day and night activity can be distinguished when relevant
- [ ] Hunt stages and outcomes are understandable
- [ ] Predator feeding and food shortages are understandable
- [ ] Injuries, carrion, scavenging, grouping, and disputes are summarized
- [ ] Detailed reports expose important modifiers and calculations
- [ ] A complete run report can still be exported locally
- [ ] Reports include scenario, seed, build, content, and ending-state information
- [ ] Full diagnostic data preserves exact values even when the terminal rounds them

## Reliability and Performance

- [ ] Playtest A behavior remains covered by regression tests
- [ ] Every Playtest B scenario can complete multiple years without crashing
- [ ] The same seed, scenario, content, and settings reproduce the same results
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
- Final graphics, audio, and accessibility implementation

Playtest B's interface remains terminal-based. Its structured events, reports, and controls should be reusable by future graphical interfaces rather than coupled to Rich.
