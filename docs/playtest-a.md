# Playtest A

## Goal

Playtest A should communicate the basic idea of what EcoSim is and will be. It should demonstrate that species with different feeding niches can respond differently to shared ecological pressures, even before predation is introduced.

## Starting Scenario

- [x] A fixed scenario can be loaded
- [x] The scenario has a known random seed
- [x] At least one region exists
- [x] At least one weather type is active
- [x] At least two producers exist
- [x] At least two consumable resources exist
- [x] At least three herbivore species with distinct feeding niches exist
- [x] At least two herbivore species depend on the same limited resource

## Modular Content
- [x] Resource definitions load from JSON
- [x] Producer definitions load from JSON
- [x] Animal definitions load from JSON
- [x] Weather definitions load from JSON
- [x] Region definitions load from JSON
- [x] Invalid definitions produce understandable errors
- [x] New ordinary content requires no system-code changes

## World State
- [x] Entity definitions remain separate from live values
- [x] Regional populations are stored
- [x] Regional producer populations are stored
- [x] Regional resource quantities are stored
- [x] Current weather and simulation time are stored

## Simulation Cycle
- [x] Time advances
- [x] Weather is applied
- [x] Producers create resources
- [x] Herbivores consume compatible resources from their diets
- [x] Multiple herbivore species can compete for a shared resource
- [x] A herbivore with multiple compatible foods can use an available alternative
- [x] Starvation mortality is applied
- [x] Basic reproduction is applied
- [x] Multiple cycles can be run without restarting

## Reporting
- [x] The random seed is displayed
- [x] Resource changes are displayed
- [x] Population changes are displayed
- [x] Feeding, deaths, and births are understandable
- [ ] Resource competition and food shortages are understandable
- [x] Important events explain what changed
- [x] A complete run report can be exported to a local file

## Reliability
- [x] A smoke test runs one complete cycle
- [x] Populations cannot become negative
- [x] Resource quantities cannot become negative
- [x] The same seed and starting state produce the same result
- [ ] Exported reports include enough information to reproduce a run
- [x] Incomplete systems do not prevent the simulation from running

## Deliberately Excluded

### Animals and Ecology
- Predator species
- Hunting and prey selection
- Carrion and decomposition
- Scavenging
- Predator and prey grouping
- Individual organisms
- Age, sex, life stages, and family relationships
- Detailed reproduction strategies
- Advanced mortality causes
- Carrying-capacity calculations
- Population genetics and evolution
- Disease and parasites

Playtest A requires three population-level herbivore species with different feeding niches. Their diets should partially overlap so that at least two species compete for a shared resource, while at least one species can use an alternative resource. Each species must be able to eat, starve, reproduce, and change population over multiple cycles.
### Regions and World Structure
- Procedural world generation
- Multiple connected regions
- Geography and maps
- Migration
- Habitat selection
- Regional divergence
- Rivers, lakes, oceans, and aquatic ecosystems
- Region-to-region environmental effects

Playtest A uses a fixed region loaded from a known scenario
### Weather and Environment
- Seasons
- Random weather transitions
- Weather fronts moving between regions
- Long-term climate change
- Environmental state beyond the values needed by the first cycle
- Disturbances and disasters
- Complex interactions between multiple weather effects

Playtest A only requires one weather definition that can apply one understandable modifier to the simulation.
### Producers and Resources
- Complex producer health
- Producer death and reproduction
- Multiple producers competing for space
- Soil, nutrients, and water cycles
- Pollination
- Seed dispersal
- Detailed decomposition
- Resource movement between regions
- Advanced resource regeneration and decay

Playtest A requires at least two producers to create at least two consumable resources in a region. These resources should support partially overlapping herbivore diets so that competition and dietary differences can affect population outcomes.
### Interface and Game Features
- Graphical user interface
- Main menu
- World creator
- Interactive map
- Field guide
- Tooltips
- Simulation-control interface
- Save and load
- Tutorials
- Player intervention
- Final ASCII artwork, graphics, animation, and audio

Playtest A may run entirely through the terminal with a readable text report.
