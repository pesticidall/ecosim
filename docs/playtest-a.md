# Playtest A

## Goal

Playtest A should communicate the basic idea of what EcoSim is and will be. It should demonstrate that species with different feeding niches can respond differently to shared ecological pressures, even before predation is introduced.

## Starting Scenario

- [ ] A fixed scenario can be loaded
- [ ] The scenario has a known random seed
- [ ] At least one region exists
- [ ] At least one weather type is active
- [ ] At least two producers exist
- [ ] At least two consumable resources exist
- [ ] At least three herbivore species with distinct feeding niches exist
- [ ] At least two herbivore species depend on the same limited resource

## Modular Content
- [ ] Resource definitions load from JSON
- [x] Producer definitions load from JSON
- [ ] Animal definitions load from JSON
- [ ] Weather definitions load from JSON
- [ ] Region definitions load from JSON
- [ ] Invalid definitions produce understandable errors
- [ ] New ordinary content requires no system-code changes

## World State
- [ ] Entity definitions remain separate from live values
- [ ] Regional populations are stored
- [ ] Regional producer populations are stored
- [ ] Regional resource quantities are stored
- [ ] Current weather and simulation time are stored

## Simulation Cycle
- [ ] Time advances
- [ ] Weather is applied
- [ ] Producers create resources
- [ ] Herbivores consume compatible resources from their diets
- [ ] Multiple herbivore species can compete for a shared resource
- [ ] A herbivore with multiple compatible foods can use an available alternative
- [ ] Starvation mortality is applied
- [ ] Basic reproduction is applied
- [ ] Multiple cycles can be run without restarting

## Reporting
- [ ] The random seed is displayed
- [ ] Resource changes are displayed
- [ ] Population changes are displayed
- [ ] Feeding, deaths, and births are understandable
- [ ] Resource competition and food shortages are understandable
- [ ] Important events explain what changed

## Reliability
- [ ] A smoke test runs one complete cycle
- [ ] Populations cannot become negative
- [ ] Resource quantities cannot become negative
- [ ] The same seed and starting state produce the same result
- [ ] Incomplete systems do not prevent the simulation from running

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
