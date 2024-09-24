#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>

static uint64_t seed;

uint64_t next_cypher(uint64_t range) 
{ 
    seed =(seed * 25214903917 + 11) % (uint64_t) (pow(2,48));
    return seed;
}

uint64_t _hash(char *str) 
{
    uint64_t len = strlen(str);
    uint64_t hash = 0;
    for (int i = 0; i < len; i++) {
        hash += str[i] * pow(2, i);
    }
    return hash;
}

int main(int argc, char *argv[]) 
{
//    char *flag = "flag{praise_rnjesus}";
    char *flag = "flag{xxxxxxxxxxxxxx}";
    seed = _hash(flag);
    int start = seed;

    printf("----Totally Random Number Generator----\n");
    printf("Press ENTER to continue");
    fflush(stdout);
    
    for (size_t i = 0; i < 16; i++) {
        getchar();
        printf("4\n");
        fflush(stdout);
    } 
    

    while (1) {
        getchar();
        printf("%d\n", next_cypher(UINT32_MAX));
        fflush(stdout);
    } 
    return 0;
}

