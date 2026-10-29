#pragma once
#include <stdint.h>

/* Central only: send persistent-layer state to both halves. */
void imprint_indicators_sync(uint32_t persistent_layers);
