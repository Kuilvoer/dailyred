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
TYPE_CONSTANTS = load_constants(POKEFIRERED / "include/constants/pokemon.h", "TYPE_")

def load_move_powers(filepath):
    powers = {}
    if not filepath.exists():
        return powers
    content = filepath.read_text(encoding="utf-8")
    for m in re.finditer(r"\[(MOVE_\w+)\]\s*=\s*\{([^}]+)\}", content):
        mv = m.group(1)
        body = m.group(2)
        pm = re.search(r"\.power\s*=\s*(\d+)", body)
        if pm:
            powers[mv] = int(pm.group(1))
    return powers

MOVE_POWERS = load_move_powers(POKEFIRERED / "src/data/battle_moves.h")

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

def to_hp_type_const(name):
    if not name.startswith("Hidden Power"):
        return None
    rest = name[len("Hidden Power"):].strip()
    if not rest:
        return None
    val = re.sub(r"[^A-Za-z0-9]", "_", rest).upper().strip("_")
    if val in TYPE_CONSTANTS:
        return f"TYPE_{val}"
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

def is_cb_compatible_move(mv_const):
    if mv_const == "MOVE_TRICK":
        return True
    if mv_const in ("MOVE_RAPID_SPIN", "MOVE_PURSUIT"):
        return True
    return MOVE_POWERS.get(mv_const, 0) > 0

def main():
    print("Fetching Smogon/Showdown Gen 3 randbats dataset...")
    url = "https://data.pkmn.cc/randbats/gen3randombattle.json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())

    species_roles = {}

    for name, mon_data in data.items():
        sp_const = to_species_const(name)
        if not sp_const:
            print(f"Skipping unknown species: {name}")
            continue

        default_items = []
        for it in mon_data.get("items", []):
            it_const = to_item_const(it)
            if it_const and it_const not in default_items:
                default_items.append(it_const)
        if not default_items:
            default_items = ["ITEM_LEFTOVERS"]

        roles_list = []
        for role_name, role_info in mon_data.get("roles", {}).items():
            r_items = []
            for it in role_info.get("items", []):
                it_const = to_item_const(it)
                if it_const and it_const not in r_items:
                    r_items.append(it_const)
            if not r_items:
                r_items = list(default_items)

            r_moves = []
            r_hp_types = []
            for mv in role_info.get("moves", []):
                mv_const = to_move_const(mv)
                if mv_const and mv_const not in r_moves:
                    r_moves.append(mv_const)
                hp_t = to_hp_type_const(mv)
                if hp_t and hp_t not in r_hp_types:
                    r_hp_types.append(hp_t)

            if not r_moves:
                continue

            if "ITEM_CHOICE_BAND" in r_items:
                cb_moves = [m for m in r_moves if is_cb_compatible_move(m)]
                if sp_const == "SPECIES_SHEDINJA" and len(cb_moves) < 4:
                    if "MOVE_AERIAL_ACE" not in cb_moves:
                        cb_moves.append("MOVE_AERIAL_ACE")
                if cb_moves:
                    roles_list.append({
                        "moves": cb_moves,
                        "items": ["ITEM_CHOICE_BAND"],
                        "hp_types": list(r_hp_types),
                    })
                other_items = [it for it in r_items if it != "ITEM_CHOICE_BAND"]
                if other_items:
                    roles_list.append({
                        "moves": r_moves,
                        "items": other_items,
                        "hp_types": list(r_hp_types),
                    })
            else:
                roles_list.append({
                    "moves": r_moves,
                    "items": r_items,
                    "hp_types": list(r_hp_types),
                })

        if sp_const not in species_roles:
            species_roles[sp_const] = roles_list
        else:
            species_roles[sp_const].extend(roles_list)

    print(f"Successfully processed {len(species_roles)} competitive species.")

    lines = [
        "// Generated competitive role-based movesets, items, and Hidden Power types for Daily Red (Smogon ADV / Showdown Gen 3)",
        "#ifndef GUARD_DAILYRED_COMPETITIVE_H",
        "#define GUARD_DAILYRED_COMPETITIVE_H",
        "",
        "#include \"global.h\"",
        "#include \"constants/species.h\"",
        "#include \"constants/moves.h\"",
        "#include \"constants/items.h\"",
        "#include \"constants/pokemon.h\"",
        "",
        "struct CompetitiveRole {",
        "    u8 movesCount;",
        "    const u16 *moves;",
        "    u8 itemsCount;",
        "    const u16 *items;",
        "    u8 hpTypesCount;",
        "    const u8 *hpTypes;",
        "};",
        "",
        "struct CompetitiveSpeciesEntry {",
        "    u16 species;",
        "    u8 rolesCount;",
        "    const struct CompetitiveRole *roles;",
        "};",
        ""
    ]

    sp_idx = 0
    role_idx = 0
    entries = []
    for sp_const in sorted(species_roles.keys()):
        roles = species_roles[sp_const]
        if not roles:
            continue

        role_struct_elems = []
        for r in roles:
            mv_var = f"sCompRoleMoves_{role_idx}"
            it_var = f"sCompRoleItems_{role_idx}"
            lines.append(f"static const u16 {mv_var}[] = {{ {', '.join(r['moves'])} }};")
            lines.append(f"static const u16 {it_var}[] = {{ {', '.join(r['items'])} }};")
            if r["hp_types"]:
                hp_var = f"sCompRoleHpTypes_{role_idx}"
                lines.append(f"static const u8 {hp_var}[] = {{ {', '.join(r['hp_types'])} }};")
                role_struct_elems.append(
                    f"    {{ ARRAY_COUNT({mv_var}), {mv_var}, ARRAY_COUNT({it_var}), {it_var}, ARRAY_COUNT({hp_var}), {hp_var} }},"
                )
            else:
                role_struct_elems.append(
                    f"    {{ ARRAY_COUNT({mv_var}), {mv_var}, ARRAY_COUNT({it_var}), {it_var}, 0, NULL }},"
                )
            role_idx += 1

        roles_var = f"sCompRoles_{sp_idx}"
        lines.append(f"static const struct CompetitiveRole {roles_var}[] = {{")
        lines.extend(role_struct_elems)
        lines.append("};")
        entries.append(f"    {{ {sp_const}, ARRAY_COUNT({roles_var}), {roles_var} }},")
        sp_idx += 1

    lines.append("")
    lines.append("static const struct CompetitiveSpeciesEntry sCompetitiveData[] = {")
    lines.extend(entries)
    lines.append("};")
    lines.append("")
    lines.append("#endif // GUARD_DAILYRED_COMPETITIVE_H")

    out_file = POKEFIRERED / "include/dailyred_competitive.h"
    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_file} ({len(entries)} species, {role_idx} roles)")

if __name__ == "__main__":
    main()
