import unittest

from core.content_registry import ContentRegistry
from simulation.simulation_cycle import run_cycle
from simulation.world_state import HabitatState, RegionState, WorldState


class TestHuntingCycle(unittest.TestCase):
    def test_prey_food_shortage_reduces_defensive_group_without_reducing_demand(self):
        defenses = []
        for food, expected_members in ((8.0, 4), (4.0, 2), (0.0, 1)):
            with self.subTest(food=food):
                world, registry = self.group_world(prey_count=4)
                prey = registry.get("prey")
                prey["max_defensive_group_size"] = 4
                prey["food_requirement_per_animal_per_cycle"] = 2.0
                prey["diet"] = [{"resource_id": "leaves", "preference": 1.0}]
                prey["statistics"]["defense"] = 5.0
                registry.register({"entity_type": "resource", "id": "leaves"})
                region = world.regions["region"]
                region.resource_quantities["leaves"] = food
                region.habitats["local"].resource_quantities["leaves"] = food
                result = run_cycle(world, registry).region_results["region"]
                hunt = result.hunting_rounds["local"]["hunter"].attempts[0].hunt
                self.assertEqual(hunt.prey_change.before.group.member_count, expected_members)
                defenses.append(hunt.approach.attack.scores.effective_defense)
                # Demand is charged for all starting prey, even dispersed animals.
                self.assertEqual(region.resource_quantities["leaves"], 0.0)
                self.assertEqual(result.feeding_results["prey"].nutrition_ratio, food / 8.0)
        self.assertGreater(defenses[0], defenses[1])
        self.assertGreater(defenses[1], defenses[2])

    def test_larger_well_fed_prey_population_increases_defense_and_food_demand(self):
        from simulation.feeding import feed_region_with_habitat_results
        from simulation.hunting_cycle import run_region_hunting

        defenses, demands = [], []
        for population in (1, 4):
            world, registry = self.group_world(prey_count=population)
            prey = registry.get("prey")
            prey["max_defensive_group_size"] = 4
            prey["food_requirement_per_animal_per_cycle"] = 2.0
            prey["diet"] = [{"resource_id": "leaves", "preference": 1.0}]
            prey["statistics"]["defense"] = 5.0
            registry.register({"entity_type": "resource", "id": "leaves"})
            region = world.regions["region"]
            region.resource_quantities["leaves"] = 8.0
            region.habitats["local"].resource_quantities["leaves"] = 8.0
            _, feeding = feed_region_with_habitat_results(region, registry)
            demands.append(feeding["local"]["prey"].required_amount)
            hunting = run_region_hunting(region, registry, feeding, world.random_generator)
            hunt = hunting["local"]["hunter"].attempts[0].hunt
            self.assertEqual(hunt.prey_change.before.group.member_count, population)
            defenses.append(hunt.approach.attack.scores.effective_defense)
            self.assertEqual(region.resource_quantities["leaves"], 8.0 - demands[-1])
        self.assertEqual(demands, [2.0, 8.0])
        self.assertGreater(defenses[1], defenses[0])

    def test_defensive_groups_use_habitat_food_coverage_instead_of_regional_average(self):
        from simulation.feeding import feed_region_with_habitat_results
        from simulation.hunting_cycle import run_region_hunting

        world, registry = self.group_world(prey_count=4)
        prey = registry.get("prey")
        prey["max_defensive_group_size"] = 4
        prey["food_requirement_per_animal_per_cycle"] = 2.0
        prey["diet"] = [{"resource_id": "leaves", "preference": 1.0}]
        registry.register({"entity_type": "resource", "id": "leaves"})
        registry.register({**registry.get("local"), "id": "other"})
        region = world.regions["region"]
        region.habitats["local"].resource_quantities["leaves"] = 8.0
        region.habitats["other"] = HabitatState(
            "other", animal_populations={"hunter": 2, "prey": 4},
            resource_quantities={"leaves": 0.0},
        )
        region.animal_populations = {"hunter": 4, "prey": 8}
        region.resource_quantities["leaves"] = 8.0
        regional_feeding, feeding = feed_region_with_habitat_results(region, registry)
        self.assertEqual(regional_feeding["prey"].nutrition_ratio, 0.5)
        hunting = run_region_hunting(region, registry, feeding, world.random_generator)
        for habitat_id, expected in (("local", 4), ("other", 1)):
            hunt = hunting[habitat_id]["hunter"].attempts[0].hunt
            self.assertEqual(hunt.prey_change.before.group.member_count, expected)
            self.assertEqual(hunt.prey_change.before.group.habitat_id, habitat_id)

    def group_world(self, forage=0.0, prey_count=2):
        world, registry = self.world(forage=forage, prey_count=prey_count)
        for definition in registry.definitions_of_type("animal"):
            definition["name"] = definition["id"].title()
            definition["statistics"].setdefault("perception", 0.0)
            definition["statistics"].setdefault("stealth", 0.0)
            definition["statistics"]["intelligence"] = 5.0
        registry.get("hunter")["max_hunting_group_size"] = 2
        registry.get("prey")["max_defensive_group_size"] = 2
        region = world.regions["region"]
        region.animal_populations["hunter"] = 2
        region.habitats["local"].animal_populations["hunter"] = 2
        return world, registry

    def test_month_automatically_schedules_one_shared_group_kill(self):
        world, registry = self.group_world()
        result = run_cycle(world, registry).region_results["region"]
        hunting = result.hunting_rounds["local"]["hunter"]
        self.assertEqual(len(hunting.attempts), 1)
        hunt = hunting.attempts[0].hunt
        self.assertEqual(hunt.hunter_change.before.group.member_count, 2)
        self.assertEqual(hunt.prey_change.before.group.member_count, 2)
        self.assertEqual(result.predation_deaths, {"prey": 1})
        self.assertEqual(result.feeding_results["hunter"].consumed_amount, 6.0)
        self.assertEqual(result.ending_animal_populations, {"hunter": 2, "prey": 1})
        habitat = world.regions["region"].habitats["local"]
        self.assertEqual(len(habitat.hunt_history), 1)
        self.assertEqual(len(habitat.predation_meals), 1)
        self.assertEqual(habitat.carrion_deposits[0].available_biomass_kg, 4.0)
        other_world, other_registry = self.group_world()
        self.assertEqual(run_cycle(other_world, other_registry).region_results["region"], result)

    def test_failed_group_round_includes_smaller_final_unit(self):
        world, registry = self.group_world()
        region = world.regions["region"]
        region.animal_populations["hunter"] = 3
        region.habitats["local"].animal_populations["hunter"] = 3
        registry.get("hunter")["activity_pattern"] = "diurnal"
        registry.get("prey")["activity_pattern"] = "nocturnal"
        result = run_cycle(world, registry).region_results["region"]
        attempts = result.hunting_rounds["local"]["hunter"].attempts
        self.assertEqual([a.hunt.hunter_change.before.group.member_count for a in attempts], [2, 1])
        self.assertEqual(result.starvation_deaths["hunter"], 3)

    def test_same_species_group_sampling_does_not_duplicate_injured_participant(self):
        from simulation.condition_cohorts import InjuryCohort
        from simulation.group_hunting_cycle import run_habitat_group_hunting_round
        from simulation.injuries import create_injury_from_trauma

        world, registry = self.group_world()
        region = world.regions["region"]
        injury = create_injury_from_trauma("attack", 1.0)
        region.habitats["local"].injury_cohorts["hunter"] = (InjuryCohort((injury,), 1),)
        predator = registry.get("hunter")
        predator["prey_diet"] = [{"animal_id": "hunter", "preference": 1.0}]
        predator["max_defensive_group_size"] = 2
        result = run_habitat_group_hunting_round(
            "hunter", "local", region, registry, {}, registry.definitions_of_type("taxon"),
            (), (), {"escape": 1.0, "counterattack": 1.0}, world.random_generator,
        )
        for attempt in result.attempts:
            hunt = attempt.hunt
            participants = (hunt.hunter_change.before.member_injuries
                            + hunt.prey_change.before.member_injuries)
            self.assertEqual(len(participants), 2)
            self.assertEqual(sum(injury in injuries for injuries in participants), 1)

    def test_group_round_only_supplements_remaining_resource_deficit(self):
        world, registry = self.group_world(forage=4.0)
        result = run_cycle(world, registry).region_results["region"]
        hunting = result.hunting_rounds["local"]["hunter"]
        self.assertEqual(hunting.attempts[0].hunt.hunter_change.before.group.member_count, 1)
        self.assertEqual(hunting.meals[0].consumption.consumed_biomass_kg, 2.0)
        self.assertEqual(result.feeding_results["hunter"].resource_consumption, {"forage": 4.0, "prey": 2.0})
        self.assertEqual(result.feeding_results["hunter"].nutrition_ratio, 1.0)
        self.assertEqual(result.ending_carrion["local"][0].available_biomass_kg, 8.0)

    def test_fully_fed_groups_and_groups_without_prey_skip_random_draws(self):
        for forage, prey_count in ((6.0, 2), (0.0, 0)):
            with self.subTest(forage=forage):
                world, registry = self.group_world(forage=forage, prey_count=prey_count)
                before = world.random_generator.getstate()
                result = run_cycle(world, registry).region_results["region"]
                self.assertEqual(result.hunting_rounds["local"]["hunter"].attempts, ())
                self.assertEqual(result.predation_deaths, {})
                self.assertEqual(world.random_generator.getstate(), before)

    def test_failed_group_hunt_spends_one_opportunity_per_participant(self):
        world, registry = self.group_world()
        registry.get("hunter")["activity_pattern"] = "diurnal"
        registry.get("prey")["activity_pattern"] = "nocturnal"
        result = run_cycle(world, registry).region_results["region"]
        hunting = result.hunting_rounds["local"]["hunter"]
        self.assertEqual(len(hunting.attempts), 1)
        self.assertFalse(hunting.attempts[0].hunt.approach.detection.detected)
        self.assertEqual(result.predation_deaths, {})
        self.assertEqual(result.starvation_deaths["hunter"], 2)

    def test_defensive_group_can_face_a_solo_hunter(self):
        world, registry = self.group_world()
        registry.get("hunter")["max_hunting_group_size"] = 1
        result = run_cycle(world, registry).region_results["region"]
        hunt = result.hunting_rounds["local"]["hunter"].attempts[0].hunt
        self.assertEqual(hunt.hunter_change.before.group.member_count, 1)
        self.assertEqual(hunt.prey_change.before.group.member_count, 2)

    def test_detailed_report_includes_group_participants_and_stage_evidence(self):
        from simulation.reporting import format_cycle_report

        world, registry = self.group_world()
        registry.get("local")["name"] = "Local"
        registry.register_all([
            {"id": "region", "entity_type": "region", "name": "Test Region"},
            {"id": "forage", "entity_type": "resource", "name": "Forage", "unit": "kg"},
        ])
        report = format_cycle_report(run_cycle(world, registry), registry, include_hunt_details=True)
        self.assertIn("Participants: 2 hunters; 2 defenders.", report)
        self.assertIn("Detention: succeeded", report)
        self.assertIn("Local / Hunter: 1 secured.", report)

    def test_same_species_group_participants_are_distinct_local_animals(self):
        from simulation.group_hunting_cycle import run_habitat_group_hunting_round

        world, registry = self.group_world()
        predator = registry.get("hunter")
        predator["prey_diet"] = [{"animal_id": "hunter", "preference": 1.0}]
        predator["max_hunting_group_size"] = 5
        predator["max_defensive_group_size"] = 5
        region = world.regions["region"]
        result = run_habitat_group_hunting_round(
            "hunter", "local", region, registry, {}, registry.definitions_of_type("taxon"),
            (), (), {"escape": 1.0, "counterattack": 1.0}, world.random_generator,
        )
        self.assertTrue(result.attempts)
        for attempt in result.attempts:
            hunt = attempt.hunt
            self.assertEqual(hunt.hunter_change.before.group.member_count, 1)
            self.assertEqual(hunt.prey_change.before.group.member_count, 1)
        self.assertGreaterEqual(region.animal_populations["hunter"], 1)

    def test_report_summarizes_scavenging_and_remaining_carrion_decay(self):
        from simulation.reporting import format_cycle_report

        world, registry = self.reporting_world()
        self.add_scavenger(world, registry)
        registry.get("local")["carrion_decay_fraction_per_cycle"] = 0.25
        result = run_cycle(world, registry)
        report = format_cycle_report(result, registry)
        self.assertIn("SCAVENGING", report)
        self.assertIn("4 kg scavenged of 4 kg requested", report)
        self.assertIn("2.25 kg remaining; 0 kg reserved; 0.75 kg decayed", report)
        self.assertEqual(result.region_results["region"].ending_carrion["local"][0].available_biomass_kg, 2.25)

    def test_injury_report_counts_animals_separately_from_injury_records(self):
        from simulation.condition_cohorts import InjuryCohort
        from simulation.injuries import create_injury_from_trauma
        from simulation.reporting import format_cycle_report

        world, registry = self.reporting_world()
        region = world.regions["region"]
        region.resource_quantities["forage"] = 3.0
        habitat = region.habitats["local"]
        habitat.resource_quantities["forage"] = 3.0
        injuries = (create_injury_from_trauma("attack", 1.0),
                    create_injury_from_trauma("counterattack", 4.0))
        habitat.injury_cohorts["prey"] = (InjuryCohort(injuries, 1),)
        result = run_cycle(world, registry)
        report = format_cycle_report(result, registry)
        self.assertIn("INJURIES", report)
        self.assertIn("Local / Prey: 1 injured animal; 2 injury records.", report)
        habitat.injury_cohorts.clear()
        self.assertEqual(format_cycle_report(result, registry), report)

    def test_later_carrion_changes_do_not_rewrite_completed_report(self):
        from simulation.reporting import format_cycle_report

        world, registry = self.reporting_world()
        result = run_cycle(world, registry)
        original_report = format_cycle_report(result, registry)
        world.regions["region"].habitats["local"].carrion_deposits.clear()
        run_cycle(world, registry)
        self.assertEqual(format_cycle_report(result, registry), original_report)
        self.assertEqual(result.region_results["region"].ending_carrion["local"][0].available_biomass_kg, 7.0)

    def test_monthly_scavengers_share_limited_predator_leftovers(self):
        world, registry = self.world()
        self.add_scavenger(world, registry)
        registry.register({**registry.get("scavenger"), "id": "second_scavenger"})
        region = world.regions["region"]
        region.animal_populations["second_scavenger"] = 1
        region.habitats["local"].animal_populations["second_scavenger"] = 1
        result = run_cycle(world, registry).region_results["region"]
        for animal_id in ("scavenger", "second_scavenger"):
            self.assertEqual(result.feeding_results[animal_id].consumed_amount, 3.5)
            self.assertEqual(result.feeding_results[animal_id].nutrition_ratio, 0.875)
        self.assertEqual(region.habitats["local"].carrion_deposits, [])
    def test_starvation_creates_unreserved_local_carrion_after_decay(self):
        from simulation.deaths import DeathCause

        world, registry = self.world(prey_count=0)
        registry.get("local")["carrion_decay_fraction_per_cycle"] = 1.0
        result = run_cycle(world, registry).region_results["region"]
        record = result.starvation_death_records["local"][0]
        self.assertIs(record.cause, DeathCause.STARVATION)
        self.assertEqual(record.animal_id, "hunter")
        self.assertEqual(record.count, 1)
        carcass = world.regions["region"].habitats["local"].carrion_deposits[0]
        self.assertEqual(carcass.available_biomass_kg, 10.0)
        self.assertIsNone(carcass.first_access_consumer_id)

    def test_starvation_carcass_can_feed_scavengers_next_cycle(self):
        world, registry = self.world(prey_count=0)
        run_cycle(world, registry)
        self.add_scavenger(world, registry)
        registry.get("scavenger")["scavenging_diet"] = [{"animal_id": "hunter", "preference": 1.0}]
        result = run_cycle(world, registry).region_results["region"]
        self.assertEqual(result.scavenging_results["local"]["scavenger"].consumed_biomass_kg, 4.0)
        self.assertEqual(result.starvation_deaths["scavenger"], 0)
        self.assertEqual(result.starvation_death_records, {})
        self.assertEqual(world.regions["region"].habitats["local"].carrion_deposits[0].available_biomass_kg, 6.0)

    def test_massless_legacy_definitions_do_not_invent_carrion(self):
        world, registry = self.world(prey_count=0)
        del registry.get("hunter")["typical_adult_mass_kg"]
        result = run_cycle(world, registry).region_results["region"]
        self.assertEqual(result.starvation_deaths["hunter"], 1)
        self.assertEqual(result.starvation_death_records, {})
        self.assertEqual(world.regions["region"].habitats["local"].carrion_deposits, [])
    def test_habitat_decay_rate_validation(self):
        from pathlib import Path
        from core.content_validator import validate_entity_definition

        definition = {
            "entity_type": "habitat", "id": "local", "name": "Local",
            "description": "A terrestrial habitat.", "movement_medium": "terrestrial",
            "conditions": {key: 0.5 for key in (
                "openness", "vegetation_density", "ground_firmness",
                "shelter_availability", "terrain_ruggedness",
            )},
        }
        for fraction, error in ((0.0, None), (0.25, None), (1.0, None),
                                (True, TypeError), ("0.25", TypeError),
                                (-0.1, ValueError), (1.1, ValueError),
                                (float("inf"), ValueError), (float("nan"), ValueError)):
            with self.subTest(fraction=fraction):
                candidate = {**definition, "carrion_decay_fraction_per_cycle": fraction}
                if error:
                    with self.assertRaisesRegex(error, "carrion_decay_fraction_per_cycle"):
                        validate_entity_definition(candidate, Path("local.json"))
                else:
                    validate_entity_definition(candidate, Path("local.json"))

    def test_invalid_decay_rate_is_rejected_even_without_carrion(self):
        from simulation.carrion_cycle import decay_habitat_carrion

        habitat = HabitatState("local")
        with self.assertRaises(ValueError):
            decay_habitat_carrion(habitat, float("nan"))
        self.assertEqual(habitat.carrion_deposits, [])

    def test_monthly_decay_applies_to_unconsumed_hunt_leftovers(self):
        world, registry = self.world()
        registry.get("local")["carrion_decay_fraction_per_cycle"] = 0.25
        result = run_cycle(world, registry).region_results["region"]
        record = result.carrion_decay_results["local"][0]
        self.assertEqual(record.decayed_biomass_kg, 1.75)
        self.assertEqual(record.updated_carrion.available_biomass_kg, 5.25)
        habitat = world.regions["region"].habitats["local"]
        self.assertEqual(habitat.carrion_deposits[0].available_biomass_kg, 5.25)
        self.assertEqual(habitat.predation_meals[0].leftover_carrion.available_biomass_kg, 7.0)

    def test_monthly_decay_repeats_without_releasing_reserved_access(self):
        from simulation.carrion import CarrionDeposit

        world, registry = self.world(forage=100.0)
        registry.get("local")["carrion_decay_fraction_per_cycle"] = 0.25
        habitat = world.regions["region"].habitats["local"]
        habitat.carrion_deposits = [CarrionDeposit("prey", "local", 10.0, 10.0, "hunter")]
        run_cycle(world, registry)
        run_cycle(world, registry)
        self.assertEqual(habitat.carrion_deposits[0].available_biomass_kg, 5.625)
        self.assertEqual(habitat.carrion_deposits[0].first_access_consumer_id, "hunter")

    def test_complete_monthly_decay_removes_depleted_deposits(self):
        world, registry = self.world()
        registry.get("local")["carrion_decay_fraction_per_cycle"] = 1.0
        result = run_cycle(world, registry).region_results["region"]
        self.assertEqual(result.carrion_decay_results["local"][0].decayed_biomass_kg, 7.0)
        self.assertEqual(world.regions["region"].habitats["local"].carrion_deposits, [])
    def add_scavenger(self, world, registry, demand=4.0):
        registry.register({
            "id": "scavenger", "entity_type": "animal", "name": "Scavenger",
            "food_requirement_per_animal_per_cycle": demand,
            "birth_rate_per_animal_per_cycle": 0.0, "diet": [],
            "scavenging_diet": [{"animal_id": "prey", "preference": 1.0}],
        })
        region = world.regions["region"]
        region.animal_populations["scavenger"] = 1
        region.habitats["local"].animal_populations["scavenger"] = 1

    def test_monthly_scavenging_feeds_from_predator_leftovers(self):
        world, registry = self.world()
        self.add_scavenger(world, registry)
        registry.get("scavenger")["birth_rate_per_animal_per_cycle"] = 1.0
        result = run_cycle(world, registry).region_results["region"]
        self.assertEqual(result.scavenging_results["local"]["scavenger"].consumed_biomass_kg, 4.0)
        self.assertEqual(result.feeding_results["scavenger"].resource_consumption, {"prey": 4.0})
        self.assertEqual(result.feeding_results["scavenger"].nutrition_ratio, 1.0)
        self.assertEqual(result.starvation_deaths["scavenger"], 0)
        self.assertEqual(result.births["scavenger"], 1)
        self.assertEqual(world.regions["region"].habitats["local"].carrion_deposits[0].available_biomass_kg, 3.0)

    def test_monthly_scavenging_preserves_reserved_carcasses(self):
        from simulation.carrion import CarrionDeposit

        world, registry = self.world(forage=3.0)
        self.add_scavenger(world, registry)
        habitat = world.regions["region"].habitats["local"]
        reserved = CarrionDeposit("prey", "local", 10.0, 10.0, "hunter")
        habitat.carrion_deposits = [reserved]
        result = run_cycle(world, registry).region_results["region"]
        self.assertEqual(result.scavenging_results["local"]["scavenger"].consumed_biomass_kg, 0.0)
        self.assertEqual(result.starvation_deaths["scavenger"], 1)
        self.assertEqual(habitat.carrion_deposits, [reserved])

    def test_monthly_scavenging_only_fills_remaining_resource_demand(self):
        world, registry = self.world()
        self.add_scavenger(world, registry)
        registry.register({"id": "scraps", "entity_type": "resource"})
        registry.get("scavenger")["diet"] = [{"resource_id": "scraps", "preference": 1.0}]
        region = world.regions["region"]
        region.resource_quantities["scraps"] = 2.0
        region.habitats["local"].resource_quantities["scraps"] = 2.0
        result = run_cycle(world, registry).region_results["region"]
        self.assertEqual(result.scavenging_results["local"]["scavenger"].consumed_biomass_kg, 2.0)
        self.assertEqual(result.feeding_results["scavenger"].consumed_amount, 4.0)
        self.assertEqual(result.feeding_results["scavenger"].resource_consumption, {"scraps": 2.0, "prey": 2.0})
        self.assertEqual(region.habitats["local"].carrion_deposits[0].available_biomass_kg, 5.0)

    def reporting_world(self):
        world, registry = self.world()
        for entity_type in ("animal", "habitat", "attack_method", "taxon"):
            for definition in registry.definitions_of_type(entity_type):
                definition["name"] = definition["id"].title()
        registry.register_all([
            {"id": "region", "entity_type": "region", "name": "Test Region"},
            {"id": "forage", "entity_type": "resource", "name": "Forage", "unit": "kg"},
        ])
        return world, registry

    def test_monthly_report_formats_prey_food_and_predation_deaths(self):
        from simulation.reporting import format_cycle_report

        world, registry = self.reporting_world()
        result = run_cycle(world, registry)
        report = format_cycle_report(result, registry)
        self.assertIn("HUNTING", report)
        self.assertIn("Local / Hunter: 1 secured.", report)
        self.assertIn("-1 predation death", report)
        self.assertIn("3 kg", report)
        self.assertNotIn("Prey consumption exceeded", report)
        self.assertNotIn("Detection: succeeded", report)
        detailed = format_cycle_report(result, registry, include_hunt_details=True)
        self.assertIn("Detection: succeeded", detailed)
        self.assertIn("Detention: succeeded", detailed)
        self.assertIn("Outcome: secured.", detailed)

    def test_detailed_hunt_report_explains_early_exit(self):
        from simulation.reporting import format_cycle_report

        world, registry = self.reporting_world()
        registry.get("hunter")["activity_pattern"] = "diurnal"
        registry.get("prey")["activity_pattern"] = "nocturnal"
        result = run_cycle(world, registry)
        report = format_cycle_report(result, registry, include_hunt_details=True)
        self.assertIn("Detection: failed", report)
        self.assertIn("chance 0.0%", report)
        self.assertIn("Chase: not attempted.", report)
        self.assertIn("Outcome: not detected.", report)
        self.assertNotIn("predation death", report)

    def test_hunt_nutrition_supports_monthly_reproduction(self):
        world, registry = self.world()
        registry.get("hunter")["birth_rate_per_animal_per_cycle"] = 1.0
        result = run_cycle(world, registry).region_results["region"]
        self.assertEqual(result.births["hunter"], 1)
        self.assertEqual(result.ending_animal_populations["hunter"], 2)
        self.assertEqual(result.starvation_deaths["hunter"], 0)

    def world(self, forage=0.0, prey_count=2):
        registry = ContentRegistry()
        registry.register_all([
            {"entity_type": "taxon", "id": "root", "parent_taxon_id": None},
            {"entity_type": "attack_method", "id": "bite", "trauma_modifier": 1.0,
             "trait_effect_target": "bite_effectiveness"},
            {"entity_type": "habitat", "id": "local", "conditions": {"openness": 1.0, "vegetation_density": 0.0}},
            {"entity_type": "animal", "id": "hunter", "taxon_id": "root",
             "typical_adult_mass_kg": 10.0, "primary_movement_mode": "terrestrial",
             "available_movement_modes": ["terrestrial"], "attack_method_id": "bite",
             "prey_diet": [{"animal_id": "prey", "preference": 1.0}],
             "food_requirement_per_animal_per_cycle": 3.0, "birth_rate_per_animal_per_cycle": 0.0,
             "diet": [{"resource_id": "forage", "preference": 1.0}],
             "statistics": {"power": 8.0, "defense": 0.0, "perception": 8.0, "mobility": 8.0}},
            {"entity_type": "animal", "id": "prey", "taxon_id": "root",
             "typical_adult_mass_kg": 10.0, "primary_movement_mode": "terrestrial",
             "available_movement_modes": ["terrestrial"],
             "food_requirement_per_animal_per_cycle": 0.0, "birth_rate_per_animal_per_cycle": 0.0,
             "diet": [], "statistics": {"power": 0.0, "defense": 0.0, "stealth": 0.0, "mobility": 0.0}},
        ])
        habitat = HabitatState("local", animal_populations={"hunter": 1, "prey": prey_count},
                               resource_quantities={"forage": forage})
        region = RegionState("region", habitats={"local": habitat},
                             animal_populations=dict(habitat.animal_populations), resource_quantities={"forage": forage})
        return WorldState(random_seed=1, regions={"region": region}), registry

    def test_month_automatically_hunts_and_feeds_before_starvation(self):
        world, registry = self.world()
        result = run_cycle(world, registry).region_results["region"]
        self.assertEqual(result.predation_deaths, {"prey": 1})
        self.assertEqual(result.starvation_deaths["hunter"], 0)
        self.assertEqual(result.feeding_results["hunter"].nutrition_ratio, 1.0)
        self.assertEqual(result.ending_animal_populations, {"hunter": 1, "prey": 1})
        self.assertEqual(len(result.hunting_rounds["local"]["hunter"].attempts), 1)
        habitat = world.regions["region"].habitats["local"]
        self.assertEqual(habitat.carrion_deposits[0].available_biomass_kg, 7.0)
        next_world, next_registry = self.world()
        self.assertEqual(run_cycle(next_world, next_registry).region_results["region"], result)

    def test_resource_fed_predators_do_not_hunt(self):
        world, registry = self.world(forage=3.0)
        result = run_cycle(world, registry).region_results["region"]
        self.assertEqual(result.predation_deaths, {})
        self.assertEqual(result.hunting_rounds["local"]["hunter"].attempts, ())
        self.assertEqual(result.ending_animal_populations["prey"], 2)

    def test_no_prey_leaves_food_deficit_for_starvation(self):
        world, registry = self.world(prey_count=0)
        result = run_cycle(world, registry).region_results["region"]
        self.assertEqual(result.predation_deaths, {})
        self.assertEqual(result.starvation_deaths["hunter"], 1)
        self.assertEqual(result.ending_animal_populations["hunter"], 0)
