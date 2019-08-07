import random
import re
import sys
from collections import defaultdict
from datetime import date as Date
from typing import Dict, List, Any

import requests

Spell = Dict[str, Any]


def main():
    if len(sys.argv) != 2:
        raise TypeError("Missing argument: level")
    level = int(sys.argv[1])
    all_spells = download_all_spells()
    random.seed(Date.today().isoformat())
    print(f"---Drawing random spells for level {level}---")
    sampled_spells = sample_random_spells(
        all_spells,
        spell_slots_by_level(level),
        allow_material_costs=True,
    )
    for spell in sampled_spells:
        print(spell_to_str(spell))


ALLOWED_SOURCES = [
    "Player's Handbook",
    "Guildmasters' Guide to Ravnica",
    "Sword Coast Adventurer's Guide",
    "Xanathar's Guide to Everything",
]


def download_all_spells():
    print("Checking index...")
    version_translations_response = requests.get("https://5etools.com/js/header.js")
    inv_version_translations_1 = re.findall(r'"book\.html","([^"]+)",{aHash:"([^"]+)"}',
                                            version_translations_response.text)
    inv_version_translations_2 = re.findall(r'"adventure\.html","([^"]+)",{isSide:!0,aHash:"([^"]+)"}',
                                            version_translations_response.text)
    inv_version_translations = inv_version_translations_1 + inv_version_translations_2
    version_translations = {shortname: fullname for fullname, shortname in inv_version_translations}
    index_response = requests.get("https://5etools.com/data/spells/index.json")
    all_sources: dict = index_response.json()
    all_sources = {version_translations.get(shortname, shortname): all_sources[shortname] for shortname in all_sources}
    sources = {}
    removed_sources = []
    for source in all_sources:
        if source in ALLOWED_SOURCES:
            sources[source] = all_sources[source]
        else:
            removed_sources.append(source)
    if any(removed_sources):
        print(f"Removed sources: {', '.join(s for s in removed_sources)}")
    all_spells = []
    for source in sources:
        print(f"Downloading spells from {source}...", end="")
        spells = download_spells_from_source(sources[source])
        all_spells.extend(spells)
        print(f"...Done. ({len(spells)} spells)")
    print(f"All done. ({len(all_spells)} spells)")
    return all_spells


def download_spells_from_source(source_suffix: str):
    spells_response = requests.get(f"https://5etools.com/data/spells/{source_suffix}")
    return spells_response.json()["spell"]


def sample_random_spells(
        all_spells: List[Spell],
        ssbsl: Dict[int, int],
        allow_material_costs: bool = True,
) -> List[Spell]:
    """for each spell slot, samples a random spell that fits that slot.

    :param all_spells: list of all spells in the game
    :param ssbsl: dict of spell slots by spell level, like the one returned by spell_slots_by_level()
    :param allow_material_costs: if False, will filter out all spells with material cost, consumed or not"""
    sampled_spells = []
    for spell_level, count in ssbsl.items():
        eligible_spells = [spell for spell in all_spells if spell["level"] == spell_level]
        if not allow_material_costs:
            eligible_spells = [spell for spell in eligible_spells if type(spell["components"].get("m", "")) == str]
        sampled_spells.extend(random.sample(eligible_spells, count))
    return sampled_spells


def spell_to_str(spell: Spell) -> str:
    components = [c for c in ["s", "v"] if c in spell["components"]]
    if "m" in spell["components"]:
        m = spell["components"]["m"]
        if type(m) == str:
            components.append("m")
        else:
            components.append(f'm ({m["text"]})')
    concentration = ["(C)"] if any(x.get("concentration") for x in spell["duration"]) else []
    ritual = ["(R)"] if spell.get("meta", {}).get("ritual") else []
    extras = ", ".join(concentration + ritual + components)
    # longest spell is 34 letters but I'll just 26
    return f'{spell["level"]} | {spell["name"].ljust(26)} {extras}    '


def resample_spell(spell: Spell, all_spells: List[Spell]):
    eligible_spells = [spell2 for spell2 in all_spells if spell2["level"] == spell["level"]
                       and spell2["name"] != spell["name"]]
    return random.choice(eligible_spells)


def spell_slots_by_level(level: int) -> Dict[int, int]:
    """e.g. for level 8 it will return: {0: 4, 1: 4, 2: 3, 3: 3, 4: 2}.
    Based on https://rpg.stackexchange.com/questions/144945/what-is-the-formula-behind-each-level-spell-slot-progression-that-i-can-use-in-a"""
    ssbl = defaultdict(lambda: 0)
    ssbl[0] = 3  # cantrips
    for lvl in range(1, level + 1):
        if lvl <= 11 or lvl in [13, 15, 17]:
            ssbl[(lvl + 1) // 2] += 1
        if lvl >= 18:
            ssbl[lvl - 13] += 1
        if lvl in [1, 5]:
            ssbl[(lvl + 1) // 2] += 1
        if lvl == 9:
            ssbl[4] += 1
        if lvl == 3:
            ssbl[1] += 1
            ssbl[2] += 1
        if lvl in [4, 10]:
            ssbl[0] += 1
    return dict(ssbl)


if __name__ == '__main__':
    main()
