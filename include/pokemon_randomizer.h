#ifndef GUARD_POKEMON_RANDOMIZER_H
#define GUARD_POKEMON_RANDOMIZER_H

#include "global.h"
#include "constants/species.h"

/* Randomizer domains are deliberately independent so adding/removing a wild
 * encounter does not reshuffle trainer or boss results. */
enum PokemonRandomizerDomain
{
    RANDOMIZER_DOMAIN_WILD = 0,
    RANDOMIZER_DOMAIN_TRAINER,
    RANDOMIZER_DOMAIN_BOSS,
    RANDOMIZER_DOMAIN_STARTER,
};

void PokemonRandomizer_Init(u32 trainerId);
u32 PokemonRandomizer_GetSeed(enum PokemonRandomizerDomain domain, u32 index);
enum Species PokemonRandomizer_GetSpecies(enum PokemonRandomizerDomain domain, u32 index);

#endif
