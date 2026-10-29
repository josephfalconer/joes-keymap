#pragma once
#include <stdint.h>

/* Central only: send persistent-layer state to both halves. UINT32_MAX resends
 * the current snapshot without replacing its layer mask. */
void imprint_indicators_sync(uint32_t persistent_layers);
