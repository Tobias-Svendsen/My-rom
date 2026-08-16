from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def add_include(path: Path):
    text = path.read_text()
    if '#include "pokemon_randomizer.h"' not in text:
        text = text.replace('#include "global.h"\n', '#include "global.h"\n#include "pokemon_randomizer.h"\n', 1)
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
            if c == '\n':
                in_line_comment = False
        elif in_block_comment:
            if c == '*' and n == '/':
                in_block_comment = False
                i += 1
        elif in_string:
            if escape:
                escape = False
            elif c == '\\':
                escape = True
            elif c == '"':
                in_string = False
        elif in_char:
            if escape:
                escape = False
            elif c == '\\':
                escape = True
            elif c == "'":
                in_char = False
        else:
            if c == '/' and n == '/':
                in_line_comment = True
                i += 1
            elif c == '/' and n == '*':
                in_block_comment = True
                i += 1
            elif c == '"':
                in_string = True
            elif c == "'":
                in_char = True
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return -1


def patch_wild():
    path = ROOT / 'src/wild_encounter.c'
    text = path.read_text()
    add_include(path)
    text = path.read_text()

    marker = 'void CreateWildMon(enum Species species, u8 level)\n{'
    start = text.find(marker)
    if start < 0:
        raise SystemExit('CreateWildMon signature not found')
    if 'PokemonRandomizer_GetSpecies(RANDOMIZER_DOMAIN_WILD' in text[start:start + 1200]:
        return

    open_pos = text.find('{', start, start + len(marker))
    close_pos = find_matching_brace(text, open_pos)
    if close_pos < 0:
        raise SystemExit('CreateWildMon end not found')

    replacement = '''void CreateWildMon(enum Species species, u8 level)\n{\n    u32 randomizerIndex = ((u32)gSaveBlock1Ptr->location.mapGroup << 24)\n                        | ((u32)gSaveBlock1Ptr->location.mapNum << 16)\n                        | ((u32)species << 4)\n                        | level;\n    species = PokemonRandomizer_GetSpecies(RANDOMIZER_DOMAIN_WILD, randomizerIndex);\n\n    ZeroEnemyPartyMons();\n    u32 personality = GetMonPersonality(species, GetSynchronizedGender(WILDMON_ORIGIN, species), PickWildMonNature(species), RANDOM_UNOWN_LETTER);\n    CreateMonWithIVs(&gParties[B_TRAINER_OPPONENT_A][0], species, level, personality, OTID_STRUCT_PLAYER_ID, USE_RANDOM_IVS);\n    GiveMonInitialMoveset(&gParties[B_TRAINER_OPPONENT_A][0]);\n}'''
    path.write_text(text[:start] + replacement + text[close_pos + 1:])


def patch_starters():
    path = ROOT / 'src/starter_choose.c'
    text = path.read_text()
    add_include(path)
    text = path.read_text()

    pattern = re.compile(r'u16 GetStarterPokemon\(u16 chosenStarterId\)\n\{.*?\n\}', re.S)
    m = pattern.search(text)
    if not m:
        raise SystemExit('GetStarterPokemon not found')
    if 'PokemonRandomizer_GetSpecies(RANDOMIZER_DOMAIN_STARTER' in m.group(0):
        return

    replacement = '''u16 GetStarterPokemon(u16 chosenStarterId)\n{\n    if (chosenStarterId >= STARTER_MON_COUNT)\n        chosenStarterId = 0;\n    return PokemonRandomizer_GetSpecies(RANDOMIZER_DOMAIN_STARTER, chosenStarterId);\n}'''
    text = text[:m.start()] + replacement + text[m.end():]
    path.write_text(text)


def patch_trainers():
    path = ROOT / 'src/battle_setup.c'
    text = path.read_text()
    add_include(path)
    text = path.read_text()

    marker = 'static void DoTrainerBattle(void)\n{'
    start = text.find(marker)
    if start < 0:
        raise SystemExit('DoTrainerBattle not found')
    open_pos = text.find('{', start, start + len(marker))
    close_pos = find_matching_brace(text, open_pos)
    if close_pos < 0:
        raise SystemExit('DoTrainerBattle end not found')

    function = text[start:close_pos + 1]
    if 'PokemonRandomizer_RandomizeTrainerParty' in function:
        return

    function = function.replace(
        'CreateNPCTrainerParty(&gParties[B_TRAINER_OPPONENT_A][0], TRAINER_BATTLE_PARAM.opponentA);',
        'CreateNPCTrainerParty(&gParties[B_TRAINER_OPPONENT_A][0], TRAINER_BATTLE_PARAM.opponentA);\n    PokemonRandomizer_RandomizeTrainerParty(&gParties[B_TRAINER_OPPONENT_A][0], TRAINER_BATTLE_PARAM.opponentA);',
        1,
    )
    function = function.replace(
        'CreateNPCTrainerParty(&gParties[B_TRAINER_OPPONENT_B][0], TRAINER_BATTLE_PARAM.opponentB);',
        'CreateNPCTrainerParty(&gParties[B_TRAINER_OPPONENT_B][0], TRAINER_BATTLE_PARAM.opponentB);\n        PokemonRandomizer_RandomizeTrainerParty(&gParties[B_TRAINER_OPPONENT_B][0], TRAINER_BATTLE_PARAM.opponentB);',
        1,
    )
    if 'PokemonRandomizer_RandomizeTrainerParty' not in function:
        raise SystemExit('Expected trainer party creation calls were not found')

    text = text[:start] + function + text[close_pos + 1:]
    path.write_text(text)


patch_wild()
patch_starters()
patch_trainers()
print('Pokemon randomizer hooks wired successfully.')
