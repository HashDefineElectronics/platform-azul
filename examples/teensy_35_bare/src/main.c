#include "MK64F12.h"

/**
 * Defines the number of loop count required to get something close to 1 second
 */
#define DELAY_1S (SystemCoreClock / 10)


void setupHardware(void) {
    
    // Regsiters for configuring the system LED

    SIM_SCGC5 |= (1 << 11); // enabled the PORTC module clock

    PORTC_PCR5 = PORT_PCR_MUX(1) | PORT_PCR_DSE(1); // set to digital pin and set to High drive strength

    GPIOC_PDDR |= (1 << 5); // set PTC5 as output 

}

int main(void) {
    volatile uint32_t Counter;    

    setupHardware();

    for(;;) {

        // Crude deplay
        for(Counter = 0; Counter < DELAY_1S; Counter++) ;

        // toggle LED
        GPIOC_PTOR |= (1 << 5);
    }

    return -1;
}