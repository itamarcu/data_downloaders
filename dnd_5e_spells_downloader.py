import json
import random
import re
import sys
from collections import defaultdict
from datetime import date as Date
from typing import Dict, List, Any

import requests

Spell = Dict[str, Any]


def main():
    usage_string = f"Usage: {sys.argv[0]} level [--no-material-cost | --no-consumable-material-cost]"
    if not 2 <= len(sys.argv) <= 3:
        raise TypeError(usage_string)
    level = int(sys.argv[1])
    allowed_material_costs = "all"
    if len(sys.argv) == 3:
        if sys.argv[2] == "--no-material-cost":
            allowed_material_costs = "none"
        elif sys.argv[2] == "--no-consumable-material-cost":
            allowed_material_costs = "only non-consumable costs"  # e.g. scrying is allowed but illusory script isn't
        else:
            raise TypeError(usage_string)
    all_spells = download_all_spells()
    random.seed(Date.today().isoformat())
    print(f"---Drawing random spells for level {level}---")
    sampled_spells = sample_random_spells(
        all_spells,
        spell_slots_by_level(level),
        allowed_material_costs=allowed_material_costs,
    )
    for spell in sampled_spells:
        print(spell_to_str(spell))


ALLOWED_SOURCES = [
    "Player's Handbook",
    "Guildmasters' Guide to Ravnica",
    "Sword Coast Adventurer's Guide",
    "Xanathar's Guide to Everything",
    "Explorer's Guide to Wildemount",
    "UA2020PsionicOptionsRevisited", "UASorcererAndWarlock", "UA2020SpellsAndMagicTattoos"
]


def download_all_spells():
    print("Checking version...")
    get_5e_tools = requests.get("https://get.5e.tools/")
    latest_version = re.search(r"release/5eTools.(.*?).zip", get_5e_tools.text).group(1)
    with open("dnd_5etools_metadata.json") as file:
        metadata = json.load(file)
        downloaded_version = metadata["version"]
    file_path = "dnd_5e_all_spells.json"
    if downloaded_version == latest_version:
        print(f"Already got latest 5etools version ({latest_version}).")
        print(f"Reading data from {file_path}")
        with open(file_path, encoding="utf8") as file:
            data = json.load(file)
            all_sources = data["all_sources"]
            all_spells = data["all_spells"]
            source_map = data["source_map"]
    else:
        print(f"Local version is {downloaded_version} but server has version {latest_version}. Updating local data...")
        source_map_response = requests.get("https://5etools.com/js/header.js")
        inv_source_map_1 = re.findall(r'"book\.html","([^"]+)",{aHash:"([^"]+)"}',
                                      source_map_response.text)
        inv_source_map_2 = re.findall(r'"adventure\.html","([^"]+)",{isSide:!0,aHash:"([^"]+)"}',
                                      source_map_response.text)
        inv_source_map = inv_source_map_1 + inv_source_map_2
        source_map = {shortname: fullname for fullname, shortname in inv_source_map}
        index_response = requests.get("https://5etools.com/data/spells/index.json")
        all_sources: dict = index_response.json()  # will map long names to short names
        all_sources = {full_source(source_map, shortname): all_sources[shortname] for shortname in all_sources}
        all_spells = []
        for source_name in all_sources:
            print(f"Downloading spells from {source_name}...", end="")
            spells = download_spells_from_source(all_sources[source_name])
            all_spells.extend(spells)
            print(f"...Done. ({len(spells)} spells)")
        print(f"Saving data to {file_path}...")
        data = {
            "all_sources": all_sources,
            "all_spells": all_spells,
            "source_map": source_map,
        }
        with open(file_path, "w", encoding="utf8") as file:
            with open("dnd_5etools_metadata.json", "w") as meta_file:
                file.write(json.dumps(data, indent=2, ensure_ascii=False))
                metadata["version"] = latest_version
                meta_file.write(json.dumps(metadata, indent=2, ensure_ascii=False))
    allowed_sources = []
    removed_sources = []
    for source in all_sources:
        (allowed_sources if source in ALLOWED_SOURCES else removed_sources).append(source)
    print(f"Allowed sources: {', '.join(s for s in allowed_sources)}")
    if any(removed_sources):
        print(f"Removed sources: {', '.join(s for s in removed_sources)}")
    allowed_sources = set(allowed_sources)
    all_allowed_spells = [spell for spell in all_spells if full_source(source_map, spell["source"]) in allowed_sources]
    print(f"All done. ({len(all_allowed_spells)}/{len(all_spells)} spells)")
    return all_allowed_spells


def download_spells_from_source(source_suffix: str):
    spells_response = requests.get(f"https://5etools.com/data/spells/{source_suffix}")
    return spells_response.json()["spell"]


def full_source(source_map: dict, short_source_name: str) -> str:
    return source_map.get(short_source_name, short_source_name)


def sample_random_spells(
        all_spells: List[Spell],
        ssbsl: Dict[int, int],
        allowed_material_costs: str = "all",
) -> List[Spell]:
    """for each spell slot, samples a random spell that fits that slot.

    :param all_spells: list of all spells in the game
    :param ssbsl: dict of spell slots by spell level, like the one returned by spell_slots_by_level()
    :param allowed_material_costs: filter out material cost. can be "all", "none", or "only non-consumable costs"."""
    sampled_spells = []
    for spell_level, count in ssbsl.items():
        eligible_spells = [spell for spell in all_spells if spell["level"] == spell_level]
        if allowed_material_costs == "all":
            pass
        elif allowed_material_costs == "none":
            eligible_spells = [spell for spell in eligible_spells if material_component_type(spell) in ["no", "free"]]
        elif allowed_material_costs == "only non-consumable costs":
            eligible_spells = [spell for spell in eligible_spells if material_component_type(spell) != "consumed"]
        else:
            raise ValueError("")
        sampled_spells.extend(random.sample(eligible_spells, count))
    return sampled_spells


def material_component_type(spell: Spell) -> str:
    if "m" not in spell["components"]:
        return "no"  # no material component; e.g. Catapult
    m = spell["components"]["m"]
    if type(m) == str:
        mm = m
    else:
        mm = m["text"]
    if "worth" not in mm:
        return "free"  # flavor-text material component; e.g. Fireball, "a tiny ball of bat guano and sulfur"
    if "consume" not in mm:
        return "pricey"  # pricey yet one-time-cost component; e.g. Chromatic Orb, "a diamond worth at least 50 gp"
    return "consumed"  # consumed per casting; e.g. Ceremony, "25 gp worth of powdered silver, which the spell consumes"


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
    Based on https://rpg.stackexchange.com/questions/144945"""
    ssbl = defaultdict(lambda: 0)
    ssbl[0] = 4  # cantrips; if you want Wizard-like, decrease this to 3
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
