#ifndef EXPLORER_H

#define EXPLORER_H
#include "graph.h"

#define PNG_PIXELS_HEIGHT 400
#define PNG_PIXELS_WIDTH 400

#define LONG_EAST_BOUND 89.106
#define LAT_NORTH_BOUND 42.948

#define LONG_INTERVAL .0056
#define LAT_INTERVAL .0048

void 
drawSimpleImage(Graph * g, char * from, char * to, State* init_state, WalkOptions* options, long maxTime);

#endif