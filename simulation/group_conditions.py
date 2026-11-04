from dataclasses import dataclass

from simulation.condition_cohorts import InjuryCohort, healthy_population, transition_injury_cohorts
from simulation.groups import GroupParticipants
from simulation.world_state import RegionState
from simulation.growth import plan_growth_loss, commit_growth_loss


@dataclass(frozen=True)
class GroupConditionChange:
    """Record participant condition and casualties explicitly resolved by context."""

    before: GroupParticipants
    after: GroupParticipants
    dead_member_indices: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if self.before.group != self.after.group:
            raise ValueError("Condition changes must retain the same group membership.")
        if not isinstance(self.dead_member_indices, tuple):
            raise TypeError("Casualty indices must be a tuple.")
        for index in self.dead_member_indices:
            if isinstance(index, bool) or not isinstance(index, int):
                raise TypeError("Casualty index must be an integer.")
            if not 0 <= index < self.before.group.member_count:
                raise ValueError("Casualty index must identify an existing participant.")
        if len(set(self.dead_member_indices)) != len(self.dead_member_indices):
            raise ValueError("Casualty indices must not contain duplicates.")
        for injuries in self.before.member_injuries + self.after.member_injuries:
            if not isinstance(injuries, tuple):
                raise TypeError("Member injuries must be tuples.")
            if injuries:
                InjuryCohort(injuries, 1)


def apply_group_condition_changes(
    region: RegionState, changes: tuple[GroupConditionChange, ...],
) -> None:
    """Commit condition and explicit casualties after validating distinct members.

    Injury severity never selects casualties. All starting members are removed
    from temporary pools before survivors return. Death records and carrion
    remain the calling context's responsibility.
    """
    pools = {}
    populations = {}
    starting_populations = {}
    deaths_by_key = {}
    for index, change in enumerate(changes):
        group = change.before.group
        if group.region_id != region.definition_id or group.habitat_id not in region.habitats:
            raise ValueError("Condition group must belong to this region and habitat.")
        habitat = region.habitats[group.habitat_id]
        if any(previous is change for previous in habitat.group_condition_history) or any(
            previous is change for previous in changes[:index]
        ):
            raise ValueError("This group condition change has already been applied.")
        key = (group.habitat_id, group.animal_id)
        deaths_by_key[key] = deaths_by_key.get(key, 0) + len(change.dead_member_indices)
        if key not in pools:
            populations[key] = habitat.animal_populations.get(group.animal_id, 0)
            starting_populations[key] = populations[key]
            pools[key] = habitat.injury_cohorts.get(group.animal_id, ())
            healthy_population(populations[key], pools[key])
        for injuries in change.before.member_injuries:
            pools[key] = transition_injury_cohorts(
                populations[key], pools[key], injuries, (), survived=False,
            )
            populations[key] -= 1
    counts_by_key = {
        key: {cohort.injuries: cohort.count for cohort in cohorts}
        for key, cohorts in pools.items()
    }
    for change in changes:
        group = change.after.group
        counts = counts_by_key[(group.habitat_id, group.animal_id)]
        for member_index, injuries in enumerate(change.after.member_injuries):
            if injuries and member_index not in change.dead_member_indices:
                counts[injuries] = counts.get(injuries, 0) + 1
    updated = {}
    for key, counts in counts_by_key.items():
        updated[key] = tuple(InjuryCohort(injuries, count) for injuries, count in counts.items() if count)
        healthy_population(starting_populations[key] - deaths_by_key[key], updated[key])
    growth_plans = {
        key: plan_growth_loss(region.habitats[key[0]], key[1], deaths_by_key[key])
        for key in updated
    }
    for (habitat_id, animal_id), cohorts in updated.items():
        commit_growth_loss(region.habitats[habitat_id], animal_id, growth_plans[(habitat_id, animal_id)])
        region.habitats[habitat_id].injury_cohorts[animal_id] = cohorts
        region.habitats[habitat_id].animal_populations[animal_id] = (
            starting_populations[(habitat_id, animal_id)] - deaths_by_key[(habitat_id, animal_id)]
        )
    for animal_id in {animal_id for _, animal_id in updated}:
        region.animal_populations[animal_id] = sum(
            habitat.animal_populations.get(animal_id, 0) for habitat in region.habitats.values()
        )
    for change in changes:
        region.habitats[change.before.group.habitat_id].group_condition_history.append(change)
