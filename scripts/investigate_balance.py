"""Run reproducible balance experiments without modifying saved content.

From the repository root:
    python -m scripts.investigate_balance --months 12 --seeds 104729 7 23
JSON is written to stdout; shell redirection can retain the evidence.
"""

import argparse
from copy import deepcopy
import json
from hashlib import sha256
from pathlib import Path

from core.content_catalog import build_content_registry
from simulation.activity import activity_phase_weights, calculate_activity_overlap_modifier
from simulation.monthly_cycle import run_month, acknowledge_month_review
from simulation.scenario_loader import load_scenario
from simulation.group_hunting import GroupHuntResult


PROFILES = ("legacy", "nutrition_only", "prior_encounters", "baseline", "caracal_carrion", "caracal_twilight", "caracal_both",
            "attempts_two", "scavenger_demand_half", "attempts_two_demand_half",
            "prior_cover", "dense_cover", "dense_cover_no_approach", "prior_search")


def experiment_registry(registry, profile):
    """Return a private content snapshot for one explicitly named experiment."""
    if profile not in PROFILES:
        raise ValueError("Unknown balance experiment.")
    result = deepcopy(registry)
    caracal = result.get("caracal")
    if profile in ("legacy", "nutrition_only", "prior_encounters", "prior_cover", "prior_search"):
        for definition in result.definitions_of_type("animal"):
            definition.pop("search_budget", None)
    if profile in ("legacy", "nutrition_only", "prior_encounters", "prior_cover", "dense_cover_no_approach"):
        for definition in result.definitions_of_type("animal"):
            definition.pop("approach_model", None)
    if profile in ("dense_cover", "dense_cover_no_approach"):
        result.get("open_grassland")["conditions"].update(
            openness=0.5, vegetation_density=0.7, shelter_availability=0.7)
    if profile in ("legacy", "nutrition_only", "prior_encounters"):
        for definition in result.definitions_of_type("animal"):
            definition.pop("encounter_model", None)
    if profile in ("attempts_two", "attempts_two_demand_half"):
        for definition in result.definitions_of_type("animal"):
            if definition.get("prey_diet"):
                definition.pop("search_budget", None)
                definition["hunting_attempts_per_animal"] = 2
    if profile in ("scavenger_demand_half", "attempts_two_demand_half"):
        for definition in result.definitions_of_type("animal"):
            if definition.get("scavenging_diet") and not definition.get("prey_diet"):
                definition["food_requirement_per_animal_per_cycle"] *= 0.5
    if profile == "legacy":
        for definition in result.definitions_of_type("animal"):
            definition.pop("nutrition", None)
        caracal.pop("scavenging_diet", None)
    if profile == "nutrition_only":
        caracal.pop("scavenging_diet", None)
    if profile in ("caracal_carrion", "caracal_both"):
        caracal["scavenging_diet"] = deepcopy(caracal["prey_diet"])
    if profile in ("caracal_twilight", "caracal_both"):
        caracal["activity_pattern"] = "crepuscular"
    return result


def summarize_evidence(summary, registry):
    """Project saved results, including prey choices and sources of food."""
    regions, carrion_budgets = {}, {}
    for region_id, region in summary.region_results.items():
        species = {}
        for animal_id, feeding in sorted(region.feeding_results.items()):
            species[animal_id] = {
                "start": region.starting_state.animal_populations.get(animal_id, 0),
                "end": region.ending_state.animal_populations.get(animal_id, 0),
                "births": region.births.get(animal_id, 0),
                "starvation_deaths": region.starvation_deaths.get(animal_id, 0),
                "predation_deaths": region.predation_deaths.get(animal_id, 0),
                "required_kg": feeding.required_amount,
                "consumed_kg": feeding.consumed_amount,
                "coverage": feeding.nutrition_ratio,
                "food_sources_kg": dict(feeding.resource_consumption),
                "hunt_outcomes": {}, "prey_choices": {}, "zero_overlap_attempts": 0,
                "scavenged_kg": 0.0,
                "condition_recovery_kg": sum(day.region_results[region_id].demographics.condition_recovery_kg.get(animal_id, 0)
                                             for day in summary.days),
                "search_expected_member_opportunities": 0.0,
                "search_allocated_member_opportunities": 0,
                "reserve_kg_end": sum(states.get(animal_id).reserve_kg for states in region.ending_state.nutritional_states.values() if animal_id in states),
                "deficit_days_max_end": max((states[animal_id].deficit_days for states in region.ending_state.nutritional_states.values() if animal_id in states), default=0.0),
                "reserve_deposits_kg": 0.0,
                "stages": {name: {"reached": 0, "passed": 0, "probability_sum": 0.0}
                           for name in ("detection", "stalking", "chase", "contact", "detention")},
                "scavenged_by_source_kg": {},
                "adult_predation_deaths": 0, "juvenile_predation_deaths": 0,
                "adult_starvation_deaths": 0, "juvenile_starvation_deaths": 0,
            }
        budget = {"starting_kg": sum(d.available_biomass_kg for deposits in region.starting_state.carrion.values() for d in deposits),
                  "predation_created_kg": 0.0, "starvation_created_kg": 0.0,
                  "predator_first_meal_kg": 0.0, "scavenged_kg": 0.0, "decayed_kg": 0.0,
                  "ending_kg": sum(d.available_biomass_kg for deposits in region.ending_state.carrion.values() for d in deposits)}
        for day in summary.days:
            local = day.region_results[region_id]
            for rounds in local.food_web.hunting_rounds.values():
                for predator_id, hunting in rounds.items():
                    item = species[predator_id]
                    if hunting.search is not None:
                        item["search_expected_member_opportunities"] += hunting.search.expected_member_opportunities
                        item["search_allocated_member_opportunities"] += hunting.search.allocated_member_opportunities
                    for attempt in hunting.attempts:
                        prey = attempt.prey_selection.selected_animal_id
                        status = attempt.hunt.outcome.status.value
                        item["hunt_outcomes"][status] = item["hunt_outcomes"].get(status, 0) + 1
                        item["prey_choices"][prey] = item["prey_choices"].get(prey, 0) + 1
                        overlap = calculate_activity_overlap_modifier(
                            activity_phase_weights(registry.get(predator_id).get("activity_pattern", "flexible")),
                            activity_phase_weights(registry.get(prey).get("activity_pattern", "flexible")),
                        )
                        item["zero_overlap_attempts"] += int(overlap == 0)
                        hunt = attempt.hunt
                        detention = hunt.detention if isinstance(hunt, GroupHuntResult) else hunt.contact.detention
                        for name, stage, probability, passed in (
                            ("detection", hunt.approach.detection, "detection_probability", "detected"),
                            ("stalking", hunt.approach.stalking, "unnoticed_probability", "unnoticed"),
                            ("chase", hunt.approach.chase, "catch_probability", "caught"),
                            ("contact", hunt.approach.attack, "hit_probability", "hit"),
                            ("detention", detention, "detention_probability", "detained"),
                        ):
                            if stage is not None:
                                evidence = item["stages"][name]
                                evidence["reached"] += 1
                                evidence["passed"] += int(getattr(stage, passed))
                                evidence["probability_sum"] += getattr(stage, probability)
                    for meal in hunting.meals:
                        if meal.death.adult_count is not None:
                            species[meal.death.animal_id]["adult_predation_deaths"] += meal.death.adult_count
                            species[meal.death.animal_id]["juvenile_predation_deaths"] += meal.death.juvenile_count
                        budget["predation_created_kg"] += meal.death.count * meal.death.body_mass_kg
                        budget["predator_first_meal_kg"] += meal.consumption.consumed_biomass_kg
            for allocations in local.food_web.scavenging_results.values():
                for animal_id, record in allocations.items():
                    species[animal_id]["scavenged_kg"] += record.consumed_biomass_kg
                    budget["scavenged_kg"] += record.consumed_biomass_kg
                    for consumption in record.consumptions:
                        source = consumption.updated_carrion.source_animal_id
                        sources = species[animal_id]["scavenged_by_source_kg"]
                        sources[source] = sources.get(source, 0.0) + consumption.consumed_biomass_kg
            for deposits in local.food_web.reserve_deposits.values():
                for animal_id, (food, carrion) in deposits.items():
                    species[animal_id]["scavenged_kg"] += carrion.consumed_biomass_kg
                    species[animal_id]["reserve_deposits_kg"] += food.consumed_amount + carrion.consumed_biomass_kg
                    budget["scavenged_kg"] += carrion.consumed_biomass_kg
                    for consumption in carrion.consumptions:
                        source = consumption.updated_carrion.source_animal_id
                        sources = species[animal_id]["scavenged_by_source_kg"]
                        sources[source] = sources.get(source, 0.0) + consumption.consumed_biomass_kg
            for meals in local.food_web.growth_meals.values():
                for animal_id, meal in meals.items():
                    record = meal.carrion
                    species[animal_id]["scavenged_kg"] += record.consumed_biomass_kg
                    budget["scavenged_kg"] += record.consumed_biomass_kg
                    for consumption in record.consumptions:
                        source = consumption.updated_carrion.source_animal_id
                        sources = species[animal_id]["scavenged_by_source_kg"]
                        sources[source] = sources.get(source, 0.0) + consumption.consumed_biomass_kg
            budget["starvation_created_kg"] += sum(d.count * d.body_mass_kg
                for records in local.demographics.starvation_death_records.values() for d in records)
            for records in local.demographics.starvation_death_records.values():
                for death in records:
                    if death.adult_count is not None:
                        species[death.animal_id]["adult_starvation_deaths"] += death.adult_count
                        species[death.animal_id]["juvenile_starvation_deaths"] += death.juvenile_count
            budget["decayed_kg"] += sum(d.decayed_biomass_kg for records in local.carrion_decay.values() for d in records)
        for values in species.values():
            for cause in ("predation", "starvation"):
                unknown = values[f"{cause}_deaths"] - values[f"adult_{cause}_deaths"] - values[f"juvenile_{cause}_deaths"]
                if unknown < 0:
                    raise ValueError("Recorded death age counts exceed population deaths.")
                values[f"unclassified_{cause}_deaths"] = unknown
        budget["balance_error_kg"] = (budget["starting_kg"] + budget["predation_created_kg"] + budget["starvation_created_kg"]
                                      - budget["predator_first_meal_kg"] - budget["scavenged_kg"] - budget["decayed_kg"] - budget["ending_kg"])
        carrion_budgets[region_id] = budget
        regions[region_id] = species
    return {"year": summary.year, "month": summary.month.value, "regions": regions, "carrion_budgets": carrion_budgets}


def run_experiment(project_root, profile, seed, months):
    if isinstance(months, bool) or not isinstance(months, int) or months < 1:
        raise ValueError("Experiment months must be a positive integer.")
    registry = experiment_registry(build_content_registry(project_root / "content"), profile)
    world = load_scenario(project_root / "scenarios" / "playtest_b_food_web.json", registry)
    world.random_seed = seed
    world.random_generator.seed(seed)
    evidence = []
    for _ in range(months):
        summary = run_month(world, registry)
        evidence.append(summarize_evidence(summary, registry))
        acknowledge_month_review(world)
    return {"profile": profile, "seed": seed, "months": evidence,
            "ending_populations": {key: dict(region.animal_populations) for key, region in world.regions.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--months", type=int, default=12)
    parser.add_argument("--seeds", type=int, nargs="+", default=[104729, 7, 23])
    parser.add_argument("--profiles", choices=PROFILES, nargs="+", default=list(PROFILES))
    args = parser.parse_args()
    if args.months < 1:
        parser.error("--months must be positive")
    root = Path(__file__).resolve().parents[1]
    fingerprints = {}
    for folder, pattern in (("content", "*.json"), ("simulation", "*.py"), ("scenarios", "*.json")):
        digest = sha256()
        for path in sorted((root / folder).rglob(pattern)):
            digest.update(path.relative_to(root).as_posix().encode("utf-8") + b"\0")
            digest.update(path.read_bytes() + b"\0")
        fingerprints[folder] = digest.hexdigest()
    print(json.dumps({"scenario": "playtest_b_food_web", "input_fingerprints_sha256": fingerprints, "runs": [
        run_experiment(root, profile, seed, args.months)
        for profile in args.profiles for seed in args.seeds
    ]}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
