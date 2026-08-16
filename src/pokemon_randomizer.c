#include "global.h"
#include "pokemon_randomizer.h"

/* A small deterministic mixer. It is independent of the game's global RNG so
 * the same Trainer ID always produces the same randomized world. */
static u32 sRandomizerSeed;

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
    sRandomizerSeed = Mix(trainerId ^ 0x504B524Du);
}

u32 PokemonRandomizer_GetSeed(enum PokemonRandomizerDomain domain, u32 index)
{
    return Mix(sRandomizerSeed
        ^ ((u32)domain * 0x9E3779B9u)
        ^ (index * 0x85EBCA6Bu));
}

enum Species PokemonRandomizer_GetSpecies(enum PokemonRandomizerDomain domain, u32 index)
{
    u32 seed = PokemonRandomizer_GetSeed(domain, index);
    enum Species species;

    /* SPECIES_EGG is the first invalid/randomizable sentinel in this project.
     * Rejection keeps the result in the normal species range. */
    do
    {
        seed = Mix(seed);
        species = (enum Species)(1 + (seed % (SPECIES_EGG - 1)));
    } while (species == SPECIES_EGG);

    return species;
}
