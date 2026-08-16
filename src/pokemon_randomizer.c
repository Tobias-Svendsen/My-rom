#include "global.h"
#include "pokemon_randomizer.h"
#include "new_game.h"

/* The save's Trainer ID is the seed. Reading it directly means the same
 * randomized world is reproduced after closing/reopening the game. */
static u32 Mix(u32 x)
{
    x ^= x >> 16;
    x *= 0x7feb352d;
    x ^= x >> 15;
    x *= 0x846ca68b;
    x ^= x >> 16;
    return x;
}

void PokemonRandomizer_Init(u32 trainerId)
{
    (void)trainerId;
}

u32 PokemonRandomizer_GetSeed(enum PokemonRandomizerDomain domain, u32 index)
{
    u32 trainerId = GetTrainerId(gSaveBlock2Ptr->playerTrainerId);
    return Mix(Mix(trainerId ^ 0x504B524Du)
        ^ ((u32)domain * 0x9E3779B9u)
        ^ (index * 0x85EBCA6Bu));
}

enum Species PokemonRandomizer_GetSpecies(enum PokemonRandomizerDomain domain, u32 index)
{
    u32 seed = PokemonRandomizer_GetSeed(domain, index);
    enum Species species;

    do
    {
        seed = Mix(seed);
        species = (enum Species)(1 + (seed % (SPECIES_EGG - 1)));
    } while (species == SPECIES_EGG);

    return species;
}
