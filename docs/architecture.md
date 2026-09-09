# EcoSim Architecture
## Project Purpose
EcoSim is intended to be an ecological simulator with as much realism as possible without making it overly complicated for the player. This simulator is also going to be built on the philosophy of modularization, so that players (and the developer) can easily add new animals, regions, weather types, resources, and producers without having to go into the various system files and refactoring everything.
What makes EcoSim's approach potentially different from other ecological simulators should be its accessibility. If a player so chose, they could run a simulation without ever having to manage it or know what any of the terms mean. If they chose to learn what the various terms meant, eventually there would be features to teach them such as hovering their mouse over a term and a tool tip with a summarized definition would pop up.
## Content and behavior
Because EcoSim is built on modularity, it primarily uses JSON files to describe its resources, animals, producers, weather types, and regions. These are the five core staples of what should belong in JSON, though more things may be added to that list later down the line.
The actual systems are what belong in Python. A JSON file should never hardcode any population counts or anything of a similar variety. Those should be procedurally generated based on preferred region types, climate types, and region size (which would determine population density and regional carrying capacity).
## Definitions and world state
An entity definition is pretty self explantory, its a definition that describes what an animal is. That's it. It doesnt decide how many spawn upon world creation, as that sort of information would be determined on world creation based on a prodcedurally generated seed.
A life simulation state determines how many of what entity spawns, what regions spawn, and what weather types are most common depending on a procedurally generated seed
## Modular Content
EcoSim's animals, resources, producers, weather, and regions should be completely modular with as simple implentation as possible. This would make it incredibly easy not just for the developer to implement new features, but also for future players looking to add their own content as well.
No player should have to modify any of the games primary systems in order to implement their own creations, the game should be able to automatically discover, read, and implement their creations.
## Collaboration and code ownership
Codex may edit files when explicitly told to do so. I, the developer of EcoSim, do not want files being automatically changed, refactored, or optimized without my personal approval.
That said, when coding I do permit suggestions, and for those suggestions to be explained in full so that I may understand the purpose for said suggestions.
I, the developer of EcoSim should be the one primarily typing and adding code to EcoSim's systems. I will also test normal implementations, though I may rely on Codex more for those so that it's more automated. This however does not permit Codex to automatically fix a failed system should a test come back failed. Instead, Codex should explain why the test failed and how to fix it.
## Playtest A boundary
Playtest A should demonstrate the idea of what EcoSim is, without it being overly complicated so that playtesters can understand what is going on.
Features that could be deliberately excluded are:
Prey and Predator dynamic grouping
Fresh water lakes, rivers, and ponds as well as animals that would primarily call these areas home.
Other currently unspecified features