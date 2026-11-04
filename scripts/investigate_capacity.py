"""Factorial prey/producer/guild experiments; saved scenario and content stay intact."""

import argparse
from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
from itertools import product
import json
from math import isclose, isfinite
from pathlib import Path
from tempfile import TemporaryDirectory

from core.content_catalog import build_content_registry
from scripts.investigate_balance import summarize_evidence
from simulation.monthly_cycle import run_month, acknowledge_month_review
from simulation.scenario_loader import load_scenario
from simulation.growth import adult_count, mass_units, validate_loss_phase
from scripts.growth_budget import growth_budget


GUILDS = {
    "current": {"black_backed_jackal": 4, "caracal": 2, "brown_hyena": 2, "white_backed_vulture": 3},
    "small": {"black_backed_jackal": 2, "caracal": 1, "brown_hyena": 1, "white_backed_vulture": 1},
}


@dataclass(frozen=True)
class Factors:
    hares: int
    red_grass: int
    guild: str
    opportunities: int
    abundance_search: bool = False
    reference_prey: float = 60.0
    paid_recovery: bool = False
    birth_threshold: float = 0.0
    standing_days: float = 0.0
    carrion_monthly_loss: float | None = None
    growth_days: int = 0
    growth_ration_floor: bool = False
    separate_growth_food: bool = False

    def __post_init__(self):
        if not isinstance(self.separate_growth_food, bool) or (self.separate_growth_food and (not self.growth_days or self.growth_ration_floor)):
            raise ValueError("Separate growth food requires growth days and excludes the ration floor.")
        if not isinstance(self.growth_ration_floor, bool) or (self.growth_ration_floor and not self.growth_days):
            raise ValueError("Growth ration floor requires enabled growth days and a boolean mode.")
        if isinstance(self.growth_days, bool) or not isinstance(self.growth_days, int) or self.growth_days < 0:
            raise ValueError("Growth days must be a nonnegative integer.")
        loss = self.carrion_monthly_loss
        if loss is not None and (isinstance(loss, bool) or not isinstance(loss, (int, float)) or not isfinite(loss) or not 0 <= loss <= 1):
            raise ValueError("Carrion monthly loss must be finite and between zero and one.")
        if isinstance(self.standing_days, bool) or not isinstance(self.standing_days, (int, float)) or not isfinite(self.standing_days) or self.standing_days < 0:
            raise ValueError("Standing days must be finite and nonnegative.")
        for value in (self.hares, self.red_grass, self.opportunities):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError("Capacity factors must be positive integers.")
        if self.guild not in GUILDS or self.opportunities > 8:
            raise ValueError("Unknown guild or unsupported opportunity count.")
        if not isinstance(self.paid_recovery, bool) or isinstance(self.birth_threshold, bool) or not isinstance(self.birth_threshold, (int, float)) or not isfinite(self.birth_threshold) or not 0 <= self.birth_threshold < 1:
            raise ValueError("Invalid recovery mode or birth threshold.")
        if not isinstance(self.abundance_search, bool) or isinstance(self.reference_prey, bool) or not isinstance(self.reference_prey, (int, float)) or not isfinite(self.reference_prey) or self.reference_prey <= 0:
            raise ValueError("Search reference must be finite and positive.")

    @property
    def label(self):
        return (f"hares{self.hares}_grass{self.red_grass}_{self.guild}_tries{self.opportunities}"
                + (f"_search{self.reference_prey:g}" if self.abundance_search else "")
                + ("_paid_recovery" if self.paid_recovery else "")
                + (f"_birth{self.birth_threshold:g}" if self.birth_threshold else "")
                + (f"_standing{self.standing_days:g}" if self.standing_days else "")
                + (f"_decay{self.carrion_monthly_loss:g}" if self.carrion_monthly_loss is not None else "")
                + (f"_growth{self.growth_days}" if self.growth_days else "")
                + ("_rationfloor" if self.growth_ration_floor else "")
                + ("_separate_growth" if self.separate_growth_food else ""))


def configure(scenario, registry, factors, seed):
    data, content = deepcopy(scenario), deepcopy(registry)
    data["random_seed"] = seed
    region = data["regions"][0]
    region["animal_populations"]["scrub_hare"] = factors.hares
    region["animal_populations"].update(GUILDS[factors.guild])
    region["producer_populations"]["redgrass"] = factors.red_grass
    prey_ids = {entry["animal_id"] for animal in content.definitions_of_type("animal")
                for entry in animal.get("prey_diet", ())}
    if factors.carrion_monthly_loss is not None:
        for definition in content.definitions_of_type("habitat"):
            definition["carrion_decay_fraction_per_cycle"] = factors.carrion_monthly_loss
    for definition in content.definitions_of_type("producer"):
        for entry in definition["production"]:
            if factors.standing_days:
                entry["standing_capacity_per_producer"] = entry["amount_per_producer_per_day"] * factors.standing_days
            else:
                entry.pop("standing_capacity_per_producer", None)
    for definition in content.definitions_of_type("animal"):
        if factors.growth_days:
            definition["growth"] = {"days_to_adult": factors.growth_days, "newborn_mass_fraction": 0.1}
        if factors.separate_growth_food and definition["id"] in prey_ids:
            definition["growth"]["feeding_model"] = "separate"
        if factors.growth_ration_floor and definition["id"] in prey_ids:
            # A conservative experimental whole-population allowance, not an
            # age-specific feeding model. Charge food through ordinary ecology.
            floor = growth_budget(definition, 31)["monthly_food_for_target_kg"]
            definition["food_requirement_per_animal_per_cycle"] = max(
                definition["food_requirement_per_animal_per_cycle"], floor)
        if factors.birth_threshold:
            definition["reproduction_food_threshold"] = factors.birth_threshold
        else:
            definition.pop("reproduction_food_threshold", None)
        if "nutrition" in definition:
            definition["nutrition"]["recovery_requires_food"] = factors.paid_recovery
        if definition.get("prey_diet"):
            if factors.abundance_search:
                definition.pop("hunting_attempts_per_animal", None)
                definition["search_budget"] = {"max_opportunities": factors.opportunities, "reference_prey": factors.reference_prey}
            else:
                definition.pop("search_budget", None)
                definition["hunting_attempts_per_animal"] = factors.opportunities
    return data, content


def check_accounting(world, summary):
    """Fail the experiment rather than accepting a numerically invalid run."""
    for region_id, result in summary.region_results.items():
        region = world.regions[region_id]
        for animal, count in result.ending_state.animal_populations.items():
            expected = (result.starting_state.animal_populations.get(animal, 0) + result.births.get(animal, 0)
                        + result.introductions.get(animal, 0) - result.removals.get(animal, 0)
                        - result.starvation_deaths.get(animal, 0) - result.predation_deaths.get(animal, 0))
            if count != expected or count < 0:
                raise ValueError("Population ledger does not reconcile.")
            if count != sum(h.animal_populations.get(animal, 0) for h in region.habitats.values()):
                raise ValueError("Regional/local populations disagree.")
        for resource, amount in region.resource_quantities.items():
            local = sum(h.resource_quantities.get(resource, 0) for h in region.habitats.values())
            if not isfinite(amount) or amount < 0 or not isclose(amount, local, abs_tol=1e-8):
                raise ValueError("Resource totals are invalid or do not reconcile.")
        for habitat in region.habitats.values():
            for animal, phase in habitat.growth_loss_phases.items():
                validate_loss_phase(phase)
                if habitat.animal_populations.get(animal, 0) <= 0:
                    raise ValueError("Empty populations must not retain growth loss phases.")
            for animal, cohorts in habitat.growth_cohorts.items():
                adult_count(habitat.animal_populations.get(animal, 0), cohorts)
            if any(not isfinite(d.available_biomass_kg) or d.available_biomass_kg < 0 for d in habitat.carrion_deposits):
                raise ValueError("Invalid carrion quantity.")
            for animal, cohorts in habitat.injury_cohorts.items():
                if sum(c.count for c in cohorts) > habitat.animal_populations.get(animal, 0):
                    raise ValueError("Injury count exceeds population.")


def run_case(project_root, factors, seed, months):
    if isinstance(months, bool) or not isinstance(months, int) or months < 1:
        raise ValueError("Months must be a positive integer.")
    original = json.loads((project_root / "scenarios" / "playtest_b_food_web.json").read_text(encoding="utf-8"))
    data, registry = configure(original, build_content_registry(project_root / "content"), factors, seed)
    # Exercise the actual scenario loader, including local producer allocation.
    with TemporaryDirectory(prefix=".balance-", dir=project_root) as folder:
        path = Path(folder) / "scenario.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        world = load_scenario(path, registry)
    records, extinct = [], {}
    for index in range(months):
        summary = run_month(world, registry)
        check_accounting(world, summary)
        evidence = summarize_evidence(summary, registry)
        budgets = evidence["carrion_budgets"]
        for day in summary.days:
            for local in day.region_results.values():
                for changes in local.demographics.growth_changes.values():
                    for change in changes.values():
                        expected = change.starting_biomass_kg - change.starvation_biomass_kg + change.growth_biomass_kg + change.newborn_biomass_kg
                        if not isclose(expected, change.ending_biomass_kg, abs_tol=1e-8):
                            raise ValueError("Daily growth biomass ledger does not reconcile.")
        if any(abs(b["balance_error_kg"]) > 1e-8 for b in budgets.values()):
            raise ValueError("Carrion ledger does not reconcile.")
        if factors.growth_days:
            for region_id, result in summary.region_results.items():
                def biomass(snapshot):
                    return sum(mass_units(count, tuple(c for local in snapshot.growth_cohorts.values()
                        for c in local.get(animal, ()))) * registry.get(animal)["typical_adult_mass_kg"]
                        for animal, count in snapshot.animal_populations.items())
                added = sum(change.growth_biomass_kg + change.newborn_biomass_kg
                    for day in summary.days for changes in day.region_results[region_id].demographics.growth_changes.values()
                    for change in changes.values())
                budget = budgets[region_id]
                expected = biomass(result.starting_state) + added - budget["predation_created_kg"] - budget["starvation_created_kg"]
                if not isclose(expected, biomass(result.ending_state), abs_tol=1e-8):
                    raise ValueError("Monthly live biomass ledger does not reconcile.")
        regional = {}
        for region_id, result in summary.region_results.items():
            species = evidence["regions"][region_id]
            regional[region_id] = {
                "species": {animal: {key: values[key] for key in (
                    "start", "end", "births", "starvation_deaths", "predation_deaths", "coverage",
                    "required_kg", "consumed_kg", "condition_recovery_kg", "scavenged_kg", "scavenged_by_source_kg", "hunt_outcomes",
                    "adult_predation_deaths", "juvenile_predation_deaths", "adult_starvation_deaths", "juvenile_starvation_deaths",
                    "unclassified_predation_deaths", "unclassified_starvation_deaths")}
                    for animal, values in species.items()},
                "resources": {resource: {"start_kg": result.starting_state.resource_quantities.get(resource, 0),
                    "produced_kg": result.production_changes.get(resource, 0),
                    "consumed_kg": result.resource_consumption.get(resource, 0),
                    "end_kg": result.ending_state.resource_quantities.get(resource, 0)}
                    for resource in result.resource_consumption},
                "carrion": budgets[region_id],
                "growth_food": {animal: {
                    "required_kg": sum(meal.feeding.required_amount for day in summary.days
                        for meals in day.region_results[region_id].food_web.growth_meals.values()
                        for key, meal in meals.items() if key == animal),
                    "consumed_kg": sum(meal.feeding.consumed_amount for day in summary.days
                        for meals in day.region_results[region_id].food_web.growth_meals.values()
                        for key, meal in meals.items() if key == animal),
                } for animal in species if registry.get(animal).get("growth", {}).get("feeding_model") == "separate"},
                "recruitment": {animal: {
                    "adults_at_start": adult_count(result.starting_state.animal_populations.get(animal, 0), tuple(c
                        for local in result.starting_state.growth_cohorts.values() for c in local.get(animal, ()))),
                    "adults_at_end": adult_count(result.ending_state.animal_populations.get(animal, 0), tuple(c
                        for local in result.ending_state.growth_cohorts.values() for c in local.get(animal, ()))),
                    "juveniles_at_end": sum(c.count for local in result.ending_state.growth_cohorts.values() for c in local.get(animal, ())),
                } for animal in species if "growth" in registry.get(animal)},
                "growth": {animal: {field: sum(getattr(change, field)
                    for day in summary.days for changes in day.region_results[region_id].demographics.growth_changes.values()
                    for key, change in changes.items() if key == animal)
                    for field in ("growth_biomass_kg", "newborn_biomass_kg", "starvation_biomass_kg")}
                    for animal in species if "growth" in registry.get(animal)},
            }
            for animal in GUILDS[factors.guild]:
                if result.ending_state.animal_populations[animal] == 0:
                    extinct.setdefault(animal, index + 1)
        records.append({"year": summary.year, "month": summary.month.value, "regions": regional})
        acknowledge_month_review(world)
    endings = {key: dict(region.animal_populations) for key, region in world.regions.items()}
    return {"case": factors.label, "factors": asdict(factors), "seed": seed,
            "extinction_month_index": extinct, "ending_populations": endings,
            "all_guild_species_present": not extinct,
            "growth_budgets": {definition["id"]: {str(days): growth_budget(definition, days) for days in (28, 29, 30, 31)}
                for definition in registry.definitions_of_type("animal") if "growth" in definition},
            "monthly": records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--months", type=int, default=12)
    parser.add_argument("--seeds", nargs="+", type=int, default=[104729, 7, 23])
    parser.add_argument("--hares", nargs="+", type=int, default=[60, 300])
    parser.add_argument("--grass", nargs="+", type=int, default=[500, 2000])
    parser.add_argument("--guilds", nargs="+", choices=GUILDS, default=list(GUILDS))
    parser.add_argument("--opportunities", nargs="+", type=int, default=[1, 2])
    parser.add_argument("--abundance-search", action="store_true")
    parser.add_argument("--reference-prey", type=float, default=60.0)
    parser.add_argument("--paid-recovery", action="store_true")
    parser.add_argument("--birth-thresholds", nargs="+", type=float, default=[0.0])
    parser.add_argument("--standing-days", nargs="+", type=float, default=[0.0])
    parser.add_argument("--growth-days", nargs="+", type=int, default=[0],
                        help="Experimental juvenile maturation days; zero preserves existing content.")
    parser.add_argument("--growth-ration-modes", nargs="+", choices=("existing", "floor", "separate"), default=["existing"],
                        help="Use existing prey rations, a whole-population floor, or separate juvenile growth meals.")
    parser.add_argument("--carrion-monthly-loss", nargs="+", type=float, default=[None],
                        help="Override habitat monthly fractional carrion loss (0–1); omission preserves content.")
    args = parser.parse_args()
    if args.months < 1:
        parser.error("--months must be positive")
    root = Path(__file__).resolve().parents[1]
    factors = [Factors(*values, args.abundance_search, args.reference_prey, args.paid_recovery, threshold, standing, loss, growth, mode == "floor", mode == "separate")
               for values in product(args.hares, args.grass, args.guilds, args.opportunities)
               for threshold in args.birth_thresholds for standing in args.standing_days
               for loss in args.carrion_monthly_loss for growth in args.growth_days
               for mode in args.growth_ration_modes]
    fingerprints = {}
    for folder, pattern in (("content", "*.json"), ("simulation", "*.py"), ("scenarios", "*.json"), ("scripts", "*.py")):
        digest = sha256()
        for path in sorted((root / folder).rglob(pattern)):
            digest.update(path.relative_to(root).as_posix().encode("utf-8") + b"\0" + path.read_bytes() + b"\0")
        fingerprints[folder] = digest.hexdigest()
    runs = [run_case(root, case, seed, args.months) for case in factors for seed in args.seeds]
    print(json.dumps({"scenario": "playtest_b_food_web", "input_fingerprints_sha256": fingerprints,
                      "months_per_run": args.months, "runs": runs}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
