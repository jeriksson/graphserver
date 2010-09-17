#ifndef EXPLORER_H

#define EXPLORER_H
#include "graph.h"

#define LAT_DISTANCE 213.5

#define LONG_DISTANCE ((187.9 + 182.3) / 2)

#define DISTANCE_RATIO (LONG_DISTANCE / LAT_DISTANCE)

#define PNG_PIXELS_HEIGHT 4000
#define PNG_PIXELS_WIDTH (PNG_PIXELS_HEIGHT * DISTANCE_RATIO)

#define LONG_EAST_BOUND 86.866
#define LAT_NORTH_BOUND 42.948
#define LONG_WEST_BOUND 89.106
#define LAT_SOUTH_BOUND 41.028


#define LONG_INTERVAL 	((LONG_WEST_BOUND - LONG_EAST_BOUND) / PNG_PIXELS_WIDTH)
#define LAT_INTERVAL	((LAT_NORTH_BOUND - LAT_SOUTH_BOUND) / PNG_PIXELS_HEIGHT)

void 
drawSimpleImage(Graph * g, char * from, char * to, State* init_state, WalkOptions* options, long maxTime);

void
makeUrbanExplorerBlob(Graph * g, char * source, char * destination, 
							State* init_state_source, State* init_state_destination, WalkOptions* options);

#endif