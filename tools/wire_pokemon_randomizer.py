from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def add_include(path: Path):
    text = path.read_text()
    if '#include "pokemon_randomizer.h"' not in text:
        text = text.replace('#include "global.h"\n', '#include "global.h"\n#include "pokemon_randomizer.h"\n', 1)
        path.write_text(text)


def patch_wild():
    path = ROOT / 'src/wild_encounter.c'
    text = path.read_text()
    add_include(path)
    text = path.read_text()

    marker = 'void CreateWildMon(enum Species species, u8 level)\n{'
    start = text.find(marker)
    if start < 0:
        raise SystemExit('CreateWildMon signature not found')
    body_end = text.find('\n}\n', start)
    if body_end < 0:
        raise SystemExit('CreateWildMon end not found')
    body_end += 3
    old = text[start:body_end]
    if 'PokemonRandomizer_GetSpecies(RANDOMIZER_DOMAIN_WILD' in old:
        return

    new = '''void CreateWildMon(enum Species species, u8 level)\n{\n    u32 randomizerIndex = ((u32)gSaveBlock1Ptr->location.mapGroup << 24)\n                        | ((u32)gSaveBlock1Ptr->location.mapNum << 16)\n                        | ((u32)species << 4)\n                        | level;\n    species = PokemonRandomizer_GetSpecies(RANDOMIZER_DOMAIN_WILD, randomizerIndex);\n\n    ZeroEnemyPartyMons();\n    u32 personality = GetMonPersonality(species, GetSynchronizedGender(WILDMON_ORIGIN, species), PickWildMonNature(species), RANDOM_UNOWN_LETTER);\n    CreateMonWithIVs(&gParties[B_TRAINER_OPPONENT_A][0], species, level, personality, OTID_STRUCT_PLAYER_ID, USE_RANDOM_IVS);\n    GiveMonInitialMoveset(&gParties[B_TRAINER_OPPONENT_A][0]);\n}\n'''
    path.write_text(text[:start] + new + text[body_end:])


def patch_starters():
    path = ROOT / 'src/starter_choose.c'
    text = path.read_text()
    add_include(path)
    text = path.read_text()

    pattern = re.compile(r'u16 GetStarterPokemon\(u16 chosenStarterId\)\n\{.*?\n\}', re.S)
    m = pattern.search(text)
    if not m:
        raise SystemExit('GetStarterPokemon not found')
    replacement = '''u16 GetStarterPokemon(u16 chosenStarterId)\n{\n    if (chosenStarterId >= STARTER_MON_COUNT)\n        chosenStarterId = 0;\n    return PokemonRandomizer_GetSpecies(RANDOMIZER_DOMAIN_STARTER, chosenStarterId);\n}'''
    if 'PokemonRandomizer_GetSpecies(RANDOMIZER_DOMAIN_STARTER' not in m.group(0):
        text = text[:m.start()] + replacement + text[m.end():]
        path.write_text(text)


def find_matching_brace(text, open_pos):
    depth = 0
    in_string = False
    in_char = False
    escape = False
    in_line_comment = False
    in_block_comment = False
    i = open_pos
    while i < len(text):
        c = text[i]
        n = text[i + 1] if i + 1 < len(text) else ''
        if in_line_comment:
            if c == '\n': in_line_comment = False
        elif in_block_comment:
            if c == '*' and n == '/':
                in_block_comment = False
                i += 1
        elif in_string:
            if escape: escape = False
            elif c == '\\': escape = True
            elif c == '"': in_string = False
        elif in_char:
            if escape: escape = False
            elif c == '\\': escape = True
            elif c == "'": in_char = False
        else:
            if c == '/' and n == '/':
                in_line_comment = True
                i += 1
            elif c == '/' and n == '*':
                in_block_comment = True
                i += 1
            elif c == '"': in_string = True
            elif c == "'": in_char = True
            elif c == '{': depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return -1


def patch_trainers():
    candidates = list((ROOT / 'src').rglob('*.c'))
    for path in candidates:
        text = path.read_text()
        m = re.search(r'(?m)^(?:static\s+)?u\d+\s+CreateNPCTrainerParty(?:FromTrainer)?\s*\([^;]*\)\s*\{', text)
        if not m:
            continue
        sig = m.group(0)
        if 'struct Pokemon *party' not in sig or 'trainerNum' not in sig:
            raise SystemExit(f'Found trainer function in {path}, but its signature does not expose party/trainerNum: {sig}')
        open_pos = text.find('{', m.start(), m.end())
        close_pos = find_matching_brace(text, open_pos)
        if close_pos < 0:
            raise SystemExit(f'Could not find end of trainer function in {path}')
        function = text[m.start():close_pos + 1]
        if 'PokemonRandomizer_GetSpecies(RANDOMIZER_DOMAIN_TRAINER' in function:
            return

        # Insert immediately before the final return in the trainer generator.
        returns = list(re.finditer(r'(?m)^\s*return\s+[^;]+;\s*$', function))
        if not returns:
            raise SystemExit(f'No return statement found in {path} trainer generator')
        ret = returns[-1]
        insertion = r'''\n\n    /* Randomizer: every NPC trainer, including gym leaders, Elite Four and\n     * Champion battles, gets a completely random species while retaining the\n     * trainer's original level.  Rebuild the initial moveset for the new\n     * species so its moves match that level. */\n    {\n        u8 randomizerSlot;\n        for (randomizerSlot = 0; randomizerSlot < PARTY_SIZE; randomizerSlot++)\n        {\n            enum Species randomizedSpecies;\n            u8 level;\n            u8 abilityNum;\n\n            if (GetMonData(&party[randomizerSlot], MON_DATA_SPECIES_OR_EGG) == SPECIES_NONE)\n                break;\n\n            level = GetMonData(&party[randomizerSlot], MON_DATA_LEVEL);\n            randomizedSpecies = PokemonRandomizer_GetSpecies(RANDOMIZER_DOMAIN_TRAINER,\n                ((u32)trainerNum << 8) | randomizerSlot);\n\n            SetMonData(&party[randomizerSlot], MON_DATA_SPECIES, &randomizedSpecies);\n            abilityNum = GetMonData(&party[randomizerSlot], MON_DATA_ABILITY_NUM);\n            if (GetAbilityBySpecies(randomizedSpecies, abilityNum) == ABILITY_NONE)\n                abilityNum = 0;\n            SetMonData(&party[randomizerSlot], MON_DATA_ABILITY_NUM, &abilityNum);\n            CalculateMonStats(&party[randomizerSlot]);\n            GiveMonInitialMoveset(&party[randomizerSlot]);\n            (void)level;\n        }\n    }\n'''
        # level is deliberately read before species replacement; CalculateMonStats keeps the level.
        insertion = insertion.replace('\\n', '\n')
        abs_ret_start = m.start() + ret.start()
        text = text[:abs_ret_start] + insertion + text[abs_ret_start:]
        add_include(path)
        path.write_text(text)
        return
    raise SystemExit('Could not find CreateNPCTrainerParty/CreateNPCTrainerPartyFromTrainer in src')


patch_wild()
patch_starters()
patch_trainers()
print('Pokemon randomizer hooks wired successfully.')
