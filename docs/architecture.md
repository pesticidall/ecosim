# EcoSim Architecture

## Project Purpose

EcoSim is intended to be an ecological simulator with as much meaningful realism as possible without making it overly complicated for the player. The simulation should prioritize ecological relationships and understandable cause and effect instead of complexity for its own sake.

EcoSim will be built around modular content. Players and developers should be able to add animals, regions, weather types, resources, and producers without entering the simulation's system files or refactoring existing logic.

What should make EcoSim different from other ecological simulators is its accessibility. A player should be able to run and enjoy a simulation without already understanding ecological terminology. Players who want to learn more should be supported by features such as tooltips, summarized definitions, a Species Library, and eventual explanations of why ecological events occurred.

## Content and Behavior

EcoSim primarily uses JSON files to describe its animals, producers, resources, weather types, and regions. These are the five initial modular content categories, although more may be added later.

JSON describes what an entity is. Python implements the rules that determine how entities behave and interact.

Entity-definition JSON should never contain live values such as a species' current regional population, a region's current weather, or the current quantity of a resource. Those values belong to a scenario, generated world, or saved world state.

Generic Python systems must not contain behavior written for one specific entity. Code such as the following should be avoided:

```python
if species_id == "ridgeback_hunter":
    perform_pack_hunt()
```

Instead, systems should interpret the entity's data, traits, needs, and current environmental pressures.

## Definitions, Scenarios, World Generation, and World State

An entity definition describes what an entity is. For example, an animal definition may describe its size, diet, movement types, preferences, tolerances, and base statistics. It does not decide how many members of that animal currently exist.

A scenario describes an intentional starting configuration used for playtests, demonstrations, and focused simulations. Scenario data may include starting regions, populations, producers, resources, weather, and a random seed.

World generation will eventually create an initial world from a seed. It may use region size, habitat suitability, climate, resource availability, population density, and carrying capacity when deciding initial conditions. Full procedural world generation is not required for Playtest A.

World state records what is currently true in a running simulation. It may include:

- Current simulation time and cycle
- Regions that exist in the world
- Regional animal and producer populations
- Regional resource quantities
- Current weather and environmental conditions
- Other values that change while the simulation runs

Entity definitions should remain reusable and unchanged while world state changes around them.

## Modular Content

EcoSim's animals, resources, producers, weather types, and regions should be modular and as simple to implement as reasonably possible. This supports both continued development and future player-created content.

Each content definition should have a stable, unique ID. References between definitions should use these IDs rather than duplicating another entity's complete data.

The content loader should automatically discover supported JSON files, identify their entity types, validate their fields, and register valid definitions. Loading order should not determine whether references work.

Invalid content should produce a clear error that identifies the file and problem. One malformed content file should not silently corrupt the simulation.

No player should have to modify EcoSim's primary systems to implement an ordinary new animal, producer, resource, weather type, or region.

## System Boundaries

Each Python system should have one clear ecological responsibility. Examples include producer growth, feeding, mortality, reproduction, weather, hunting, grouping, and migration.

A system should clearly define:

- What information it reads
- What world state it may change
- What result or events it returns
- What assumptions and invariants it requires

Systems should communicate through explicit data and world state rather than hidden global side effects. The main simulation entry point should coordinate completed systems but should not contain their internal ecological logic.

An unfinished system should remain outside the active simulation cycle until its focused tests pass and its required inputs and outputs are understood.

## Import Safety

Importing a Python module may define functions, classes, constants, and other reusable structures. Importing must not run a simulation, alter populations, consume resources, perform hunts, select weather, or execute mutation tests.

Executable entry-point behavior should be protected with:

```python
if __name__ == "__main__":
    ...
```

Focused tests should live in test files rather than at the bottom of importable simulation modules.

## Always-Runnable Development

EcoSim should remain runnable throughout development. Every completed milestone should leave a valid path from loading content to producing visible output.

New systems should be built and tested independently before being connected to the main cycle. Integrating a new system should add one understood stage to a simulation that already runs, rather than requiring several unfinished systems to become functional at once.

The project should maintain a small smoke test that confirms:

- Content can load
- A world or scenario can be created
- One simulation cycle can complete
- Populations and resource quantities remain valid
- The same seed reproduces the same result

## Randomness and Reproducibility

Random behavior should use a simulation-owned random-number generator rather than uncontrolled global randomness.

A simulation started from the same content, initial state, configuration, and seed should produce the same result. Reports should record the seed so unexpected outcomes can be reproduced and investigated.

Deterministic tests should not occasionally pass or fail because of uncontrolled random rolls.

## Collaboration and Code Ownership

Codex may edit EcoSim files only when explicitly told to do so. Files must not be automatically changed, refactored, or optimized without the developer's approval.

Codex may suggest code and architecture. Suggestions should be explained clearly enough for the developer to understand their purpose, inputs, outputs, and tradeoffs.

The developer should primarily type and add code to EcoSim's systems. Codex may help automate tests when requested, but a failed test does not authorize Codex to modify the implementation. Codex should first explain why the test failed and describe the smallest sensible correction.

## Playtest A Boundary

Playtest A should demonstrate the general concept of EcoSim without becoming so complicated that playtesters cannot understand what is happening.

Playtest A should demonstrate:

- JSON definitions for animals, producers, resources, weather types, and regions
- Automatic content loading and understandable validation errors
- A fixed starting scenario with a known random seed
- Separate entity definitions and live world state
- At least one region and weather condition
- Producers creating resources
- At least one herbivore consuming resources
- Basic starvation mortality and reproduction
- Multiple simulation cycles
- A readable report of important changes
- Reproducible results when the same seed is reused
- The ability to add ordinary modular content without changing system logic

Features deliberately excluded from Playtest A may include:

- Predator and prey dynamic grouping
- Full procedural world generation
- Freshwater lakes, rivers, and ponds and the animals that primarily inhabit them
- Sophisticated hunting, migration, evolution, and population structure
- Other features not required to demonstrate the first complete ecological loop
