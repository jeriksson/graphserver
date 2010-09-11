#include <cairo.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <math.h>
#include "graph.h"
#include "explorer.h"

int convertPointToPixel(double pt, double reference, double interval){

	return floor(fabs((reference - fabs(pt)) / interval));	
}

void paintLine(double lat1, double long1, double lat2, double long2, cairo_t * cr){
	
	cairo_set_source_rgb (cr, 0.0, 0.0, 0.0);
	//move to point 1
	cairo_move_to 	(cr, 
			convertPointToPixel(long1, LONG_EAST_BOUND, LONG_INTERVAL), 
			convertPointToPixel(lat1, LAT_NORTH_BOUND, LAT_INTERVAL));

	//draw line to point 2
	cairo_line_to	(cr,
                        convertPointToPixel(long2, LONG_EAST_BOUND, LONG_INTERVAL), 
			convertPointToPixel(lat2, LAT_NORTH_BOUND, LAT_INTERVAL));

	
	cairo_stroke(cr);
}

void
drawSimpleImage(Graph * g, char * source, char * destination, State* init_state, WalkOptions* options, long maxTime){
	
	
	//get vertices
	//Get origin vertex to make sure it exists
	Vertex* origin_v = gGetVertex( g, source );
	//Get target for A*
	Vertex* target_v = gGetVertex( g, destination );
	if( origin_v == NULL || target_v == NULL ) {
	  return;
	}

	
	cairo_surface_t *surface;
	cairo_t *cr;

	surface = cairo_image_surface_create (CAIRO_FORMAT_ARGB32, PNG_PIXELS_WIDTH, PNG_PIXELS_HEIGHT);
	cr = cairo_create (surface);
	
	cairo_set_source_rgb (cr, 0.0, 0.0, 0.0);
	cairo_paint_with_alpha (cr, 0.3);
	cairo_set_line_width (cr, 1.2);	

	printf("test %lf\n", origin_v->lat);
	paintLine(origin_v->lat, origin_v->lon, target_v->lat, target_v->lon, cr);

	cairo_surface_write_to_png(surface, "explorerimages/blah.png");
		
}

/*void 
explorerGetPossibleVertices(Graph * g, char * source, char * destination, State* init_state, WalkOptions* options long maxTime){

	//Get origin vertex to make sure it exists
	Vertex* source_v = gGetVertex( g, origin );
	//Get target for A*
	Vertex* destination_v = gGetVertex( g, target );
	if( origin_v == NULL || target_v == NULL ) {
	  return NULL;
	}
	
	//setup forward queue and backward queue
	dirfibheap_t forward_q = dirfibheap_new();
	dirfibheap_t backward_q = dirfibheap_new();
	
	while(){
		
	}
}

void
explorerFinished(){
		
}*/