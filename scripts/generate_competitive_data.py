import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POKEFIRERED = ROOT / "pokefirered"

# Load FireRed constant names
def load_constants(filepath, prefix):
    names = set()
    if not filepath.exists():
        return names
    content = filepath.read_text(encoding="utf-8")
    for m in re.finditer(rf"#define\s+{prefix}(\w+)\s+", content):
        names.add(m.group(1))
    return names

SPECIES_CONSTANTS = load_constants(POKEFIRERED / "include/constants/species.h", "SPECIES_")
MOVE_CONSTANTS = load_constants(POKEFIRERED / "include/constants/moves.h", "MOVE_")
ITEM_CONSTANTS = load_constants(POKEFIRERED / "include/constants/items.h", "ITEM_")

def to_species_const(name):
    clean = name.replace("’", "").replace("'", "")
    if clean.startswith("Deoxys"):
        return "SPECIES_DEOXYS"
    if clean == "Nidoran-F":
        return "SPECIES_NIDORAN_F"
    if clean == "Nidoran-M":
        return "SPECIES_NIDORAN_M"
    if clean == "Mr. Mime":
        return "SPECIES_MR_MIME"
    if clean == "Farfetchd":
        return "SPECIES_FARFETCHD"
    
    val = re.sub(r"[^A-Za-z0-9]", "_", clean).upper()
    val = re.sub(r"_+", "_", val).strip("_")
    if val in SPECIES_CONSTANTS:
        return f"SPECIES_{val}"
    return None

def to_move_const(name):
    if name.startswith("Hidden Power"):
        return "MOVE_HIDDEN_POWER"
    special = {
        "Ancient Power": "ANCIENT_POWER",
        "Double-Edge": "DOUBLE_EDGE",
        "Hi Jump Kick": "HIGH_JUMP_KICK",
        "High Jump Kick": "HIGH_JUMP_KICK",
        "Self-Destruct": "SELF_DESTRUCT",
        "Soft-Boiled": "SOFT_BOILED",
        "Poison Powder": "POISON_POWDER",
        "Solar Beam": "SOLAR_BEAM",
        "Feint Attack": "FAINT_ATTACK",
        "Smelling Salts": "SMELLING_SALT",
        "Sonic Boom": "SONIC_BOOM",
        "Dynamic Punch": "DYNAMIC_PUNCH",
        "Thunder Punch": "THUNDER_PUNCH",
        "Fire Punch": "FIRE_PUNCH",
        "Ice Punch": "ICE_PUNCH",
        "Vice Grip": "VICE_GRIP",
        "Bubble Beam": "BUBBLE_BEAM",
    }
    if name in special:
        return f"MOVE_{special[name]}"
    val = re.sub(r"[^A-Za-z0-9]", "_", name).upper()
    val = re.sub(r"_+", "_", val).strip("_")
    if val in MOVE_CONSTANTS:
        return f"MOVE_{val}"
    return None

def to_item_const(name):
    special = {
        "Leftovers": "LEFTOVERS",
        "Choice Band": "CHOICE_BAND",
        "Lum Berry": "LUM_BERRY",
        "Salac Berry": "SALAC_BERRY",
        "Liechi Berry": "LIECHI_BERRY",
        "Petaya Berry": "PETAYA_BERRY",
        "White Herb": "WHITE_HERB",
        "Silk Scarf": "SILK_SCARF",
        "Thick Club": "THICK_CLUB",
        "Light Ball": "LIGHT_BALL",
        "Twisted Spoon": "TWISTED_SPOON",
        "Soul Dew": "SOUL_DEW",
        "Stick": "STICK",
        "Shell Bell": "SHELL_BELL",
        "Quick Claw": "QUICK_CLAW",
        "Focus Band": "FOCUS_BAND",
        "Scope Lens": "SCOPE_LENS",
    }
    if name in special and special[name] in ITEM_CONSTANTS:
        return f"ITEM_{special[name]}"
    val = re.sub(r"[^A-Za-z0-9]", "_", name).upper()
    val = re.sub(r"_+", "_", val).strip("_")
    if val in ITEM_CONSTANTS:
        return f"ITEM_{val}"
    return None

def main():
    print("Fetching Smogon/Showdown Gen 3 randbats dataset...")
    url = "https://data.pkmn.cc/randbats/gen3randombattle.json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())

    species_dict = {}

    for name, mon_data in data.items():
        sp_const = to_species_const(name)
        if not sp_const:
            print(f"Skipping unknown species: {name}")
            continue

        moves = set()
        items = set()

        for it in mon_data.get("items", []):
            it_const = to_item_const(it)
            if it_const:
                items.add(it_const)

        for role_name, role_info in mon_data.get("roles", {}).items():
            for it in role_info.get("items", []):
                it_const = to_item_const(it)
                if it_const:
                    items.add(it_const)
            for mv in role_info.get("moves", []):
                mv_const = to_move_const(mv)
                if mv_const:
                    moves.add(mv_const)

        if not items:
            items.add("ITEM_LEFTOVERS")

        if sp_const not in species_dict:
            species_dict[sp_const] = {"moves": sorted(list(moves)), "items": sorted(list(items))}
        else:
            species_dict[sp_const]["moves"] = sorted(list(set(species_dict[sp_const]["moves"] + list(moves))))
            species_dict[sp_const]["items"] = sorted(list(set(species_dict[sp_const]["items"] + list(items))))

    print(f"Successfully processed {len(species_dict)} competitive species.")

    # Generate C header
    lines = [
        "// Generated competitive movesets and items for Daily Red (Smogon ADV / Showdown Gen 3)",
        "#ifndef GUARD_DAILYRED_COMPETITIVE_H",
        "#define GUARD_DAILYRED_COMPETITIVE_H",
        "",
        "#include \"global.h\"",
        "#include \"constants/species.h\"",
        "#include \"constants/moves.h\"",
        "#include \"constants/items.h\"",
        "",
        "struct CompetitiveSpeciesEntry {",
        "    u16 species;",
        "    u8 movesCount;",
        "    const u16 *moves;",
        "    u8 itemsCount;",
        "    const u16 *items;",
        "};",
        ""
    ]

    # Write move and item arrays
    idx = 0
    entries = []
    for sp_const, val in sorted(species_dict.items()):
        mv_list = val["moves"]
        it_list = val["items"]
        if not mv_list:
            continue
        mv_var = f"sCompMoves_{idx}"
        it_var = f"sCompItems_{idx}"
        
        lines.append(f"static const u16 {mv_var}[] = {{ {', '.join(mv_list)} }};")
        lines.append(f"static const u16 {it_var}[] = {{ {', '.join(it_list)} }};")
        entries.append(f"    {{ {sp_const}, ARRAY_COUNT({mv_var}), {mv_var}, ARRAY_COUNT({it_var}), {it_var} }},")
        idx += 1

    lines.append("")
    lines.append(f"static const struct CompetitiveSpeciesEntry sCompetitiveData[] = {{")
    lines.extend(entries)
    lines.append("};")
    lines.append("")
    lines.append("#endif // GUARD_DAILYRED_COMPETITIVE_H")

    out_file = POKEFIRERED / "include/dailyred_competitive.h"
    out_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_file} ({len(entries)} entries)")

if __name__ == "__main__":
    main()
