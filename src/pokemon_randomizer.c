#include "global.h"
#include "pokemon_randomizer.h"
#include "new_game.h"
#include "pokemon.h"

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

void PokemonRandomizer_RandomizeTrainerParty(struct Pokemon *party, u16 trainerId)
{
    u8 slot;

    for (slot = 0; slot < PARTY_SIZE; slot++)
    {
        enum Species oldSpecies = GetMonData(&party[slot], MON_DATA_SPECIES_OR_EGG);
        enum Species randomizedSpecies;
        u8 abilityNum;
        u8 level;

        if (oldSpecies == SPECIES_NONE || oldSpecies == SPECIES_EGG)
            break;

        level = GetMonData(&party[slot], MON_DATA_LEVEL);
        randomizedSpecies = PokemonRandomizer_GetSpecies(RANDOMIZER_DOMAIN_TRAINER,
            ((u32)trainerId << 8) | slot);

        SetMonData(&party[slot], MON_DATA_SPECIES, &randomizedSpecies);
        abilityNum = GetMonData(&party[slot], MON_DATA_ABILITY_NUM);
        if (GetAbilityBySpecies(randomizedSpecies, abilityNum) == ABILITY_NONE)
            abilityNum = 0;
        SetMonData(&party[slot], MON_DATA_ABILITY_NUM, &abilityNum);
        CalculateMonStats(&party[slot]);
        GiveMonInitialMoveset(&party[slot]);
        (void)level;
    }
}
