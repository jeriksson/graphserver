#include <cairo.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <unistd.h>
#include <math.h>
#include <time.h>
#include <sys/time.h>
#include "graph.h"
#include "explorer.h"
#include "dirfibheap.h"
#include "statetypes.h"

int
forwardDijkstra(Graph * sptForward, dirfibheap_t forward_q, WalkOptions* options, long maximumTime);

int
backwardDijkstra(Graph * sptForward, dirfibheap_t forward_q, WalkOptions* options, long maximumTime);

Vertex *
getVertexAtIndex(int i, simpleMemoryAllocator * slab);

int vertexInBlob(Vertex * v, Graph * otherSpt, long max, int index);

long timevaldiff(struct timeval *starttime, struct timeval *finishtime);

void
sptIterator(void * vertex);

int convertPointToPixel(double pt, double reference, double interval){

	return floor(fabs((reference - fabs(pt)) / interval));	
}

void paintLine(double lat1, double long1, double lat2, double long2, cairo_t * cr){
	
	cairo_set_source_rgba (cr, 1, 1, 1, 0.5);
	//move to point 1
	cairo_move_to 	(cr, 
			convertPointToPixel(long1, LONG_WEST_BOUND, LONG_INTERVAL), 
			convertPointToPixel(lat1, LAT_NORTH_BOUND, LAT_INTERVAL));

	//draw line to point 2
	cairo_line_to	(cr,
                        convertPointToPixel(long2, LONG_WEST_BOUND, LONG_INTERVAL), 
			convertPointToPixel(lat2, LAT_NORTH_BOUND, LAT_INTERVAL));

	
	cairo_stroke(cr);
}


void
makeUrbanExplorerBlob(Graph * g, char * source, char * destination, 
							State* init_state_source, State* init_state_destination, WalkOptions* options){

	double maximumTime = difftime((time_t)init_state_destination->time, (time_t)init_state_source->time);
	
	printf("max time is : %lf\n", maximumTime);
	
	struct timeval time1, time2, time3, time4;

  	gettimeofday(&time1, NULL); 


	//setup image
	cairo_surface_t *surface;
	cairo_t *cr;

	surface = cairo_image_surface_create (CAIRO_FORMAT_ARGB32, PNG_PIXELS_WIDTH, PNG_PIXELS_HEIGHT);
	cr = cairo_create (surface);
	
	cairo_set_source_rgba (cr, 0.0, 0.0, 0.0, 0.5);
	cairo_paint_with_alpha (cr, 1);
	cairo_set_line_width (cr, 18);
	cairo_set_line_cap(cr, CAIRO_LINE_CAP_ROUND);

	//Get origin vertex to make sure it exists
	Vertex* source_v = gGetVertex( g, source );
	//Get target for A*
	Vertex* destination_v = gGetVertex( g, destination );
	if( source_v == NULL || destination_v == NULL ) {
	  return;
	}
	
	//setup forward queue and backward queue
	dirfibheap_t forward_q = dirfibheap_new();
	dirfibheap_t backward_q = dirfibheap_new();
	
	//create forward spt and backward spt
  	Graph* sptForward = gNew();
  	Graph* sptBackward = gNew();
  	
  	//insert source into spt
  	gAddVertex_NoHash( sptForward, source_v )->payload = init_state_source;
  	//insert destination into spt
	gAddVertex_NoHash( sptBackward, destination_v )->payload = init_state_destination;
	
	//insert source into queue
	dirfibheap_insert_or_dec_key( forward_q, source_v, 0 );
	//insert destination in queue
	dirfibheap_insert_or_dec_key( backward_q, destination_v, 0 );
	
	int forwardIsDone = 0;
	int backwardIsDone = 0;
	int counter = 0;
	
	do{
		forwardIsDone = forwardDijkstra(sptForward, forward_q, options, maximumTime);			
			
	}while(!forwardIsDone);

	do{

		backwardIsDone = backwardDijkstra(sptBackward, backward_q, options, maximumTime );		
	}while(!backwardIsDone);
	

	gettimeofday(&time2, NULL); 

	int i = 0; 
	for (; i < sptForward->sptVertexMemoryAllocator->currentObjectsAllocated; ++i)
	{
		Vertex * vForward = getVertexAtIndex(i, sptForward->sptVertexMemoryAllocator);
		if (vForward && vForward->label && vertexInBlob(vForward, sptBackward, maximumTime, i))
		{
			//now, are edges in?
			ListNode* edges = vGetOutgoingEdgeList( vForward );
			while( edges )
			{
				Edge* edge = edges->data;
 				Vertex* edge_v = edge->to;
 				Vertex* edge_v_spt;
 				
 				if( (edge_v_spt = gGetVertex_NoHash( sptForward, edge_v )) ) //get the SPT Vertex corresponding to 'v'
			  	{        	
			    	if (vertexInBlob(edge_v_spt, sptBackward, maximumTime, edge_v_spt->sequenceNumber)){
			    		++counter;
			    		paintLine(vForward->lat, vForward->lon, edge_v_spt->lat, edge_v_spt->lon, cr);
			    	}
			    } 
			    
				edges = edges->next;
			}
			
		}
	} 

	gettimeofday(&time3, NULL); 

	printf("counter is : %d\n", counter);
	cairo_surface_write_to_png(surface, "explorerimages/blah2.png");
	
	gettimeofday(&time4, NULL); 
	
	printf("1: %ld, 2: %ld, 3: %ld\n", timevaldiff(&time1, &time2), timevaldiff(&time2, &time3), timevaldiff(&time3, &time4));
	
}

long timevaldiff(struct timeval *starttime, struct timeval *finishtime)
{
  long msec;
  msec=(finishtime->tv_sec-starttime->tv_sec)*1000;
  msec+=(finishtime->tv_usec-starttime->tv_usec)/1000;
  return msec;
}

int vertexInBlob(Vertex * v, Graph * otherSpt, long max, int index){
	int inBlob = 0;
	
	if (v && v->label){
		long vWeight = ((State*)v->payload)->weight;
		if (vWeight < max){
			Vertex * u = getVertexAtIndex(index, otherSpt->sptVertexMemoryAllocator);
			if (u && u->label && u->payload){
				//does forward + backward time exceed maximumtime
				long combinedWeight = ((State*)u->payload)->weight + vWeight;
				if (combinedWeight < max)
					inBlob = 1;
			}
		}
	}
	
	return inBlob;
}

Vertex *
getVertexAtIndex(int i, simpleMemoryAllocator * slab){
	return (Vertex *)(slab->objects + (i * slab->sizeOfType));
}

int
backwardDijkstra(Graph * sptBackward, dirfibheap_t backward_q, WalkOptions* options, long maxTime){

	int done = 0;
	Vertex * settledVertex, * spt_settledVertex, * relaxVertex, * relaxVertex_spt;
	State * settledState, * relaxedState;
	
	
	if( !dirfibheap_empty( backward_q ) )									//Is the queue empty? 
	{                  				
    	settledVertex = dirfibheap_extract_min( backward_q );                //get the lowest-weight Vertex
    	
    	spt_settledVertex = gGetVertex_NoHash( sptBackward, settledVertex );  //get corresponding SPT Vertex,
    	settledState = (State*)spt_settledVertex->payload;                   //and get State of u 'du'.
		
		if (settledState->weight > maxTime){
			return (done = 1);	
		}
		
		ListNode* edges = vGetIncomingEdgeList( settledVertex );
		while( edges ) 														//For each Edge 'edge'
		{                                 					
 		
 			Edge* edge = edges->data;
 			relaxVertex = edge->from;											//Get the destination vertex of the edge we are relaxing
 			
 			long old_w;
		  	if( (relaxVertex_spt = gGetVertex_NoHash( sptBackward, relaxVertex )) ) //get the SPT Vertex corresponding to 'v'
		  	{        	
		    	relaxedState = (State*)relaxVertex_spt->payload;            					//and its State 'dv'      
				old_w = relaxedState->weight;
		    } 
		    else 
		    {
		    	relaxedState = NULL;                                       	//which may not exist yet
		        old_w = INFINITY;
		    }
		    		
		    State *newRelaxedState = eWalkBack( edge, settledState, options );			//get the state resulting from the new edge.
 			
 			if(!newRelaxedState) {													//is it null? Then something is wrong and we should move on
		    	edges = edges->next;
		    	continue;
		    }
		    
		    if (newRelaxedState->weight < settledState->weight)					//detect negative edge weights, if negative skip it
		    {					
		    	edges = edges->next;
		    	continue;
		    }
 			
 			long new_w = newRelaxedState->weight;									//get the new weight
 			
			if( new_w < old_w ) 
			{
			  	dirfibheap_insert_or_dec_key( backward_q, relaxVertex, new_w );    	// rekey or insert using the new weight
			
			  	
			  	if( !relaxVertex_spt ) 												//this is the first time we've seen this vertex
			  	{											
			    	relaxVertex_spt = gAddVertex_NoHash( sptBackward, relaxVertex ); //add it to the shortest path tree
			    }
			
				if(relaxVertex_spt->payload)
				{
				    stateDestroy(relaxVertex_spt->payload);
				}
			  	
			  	relaxVertex_spt->payload = newRelaxedState;                      		//Set the State in the SPT to the current winner
				vSetParent( relaxVertex_spt, spt_settledVertex, edge->payload );      //Make u the parent of v in the SPT
			} 
			else 
			{
			  stateDestroy(newRelaxedState); 										//dont need it
			}
			
			edges = edges->next;
		}
	}
	else 
	{
		done = 1;
	}
	
	return done;
}


int
forwardDijkstra(Graph * sptForward, dirfibheap_t forward_q, WalkOptions* options, long maxTime){

	int done = 0;
	Vertex * settledVertex, * spt_settledVertex, * relaxVertex, * relaxVertex_spt;
	State * settledState, * relaxedState;
	
	
	if( !dirfibheap_empty( forward_q ) )									//Is the queue empty? 
	{                  				
    	settledVertex = dirfibheap_extract_min( forward_q );                //get the lowest-weight Vertex
    	
    	spt_settledVertex = gGetVertex_NoHash( sptForward, settledVertex );  //get corresponding SPT Vertex,
    	settledState = (State*)spt_settledVertex->payload;                   //and get State of u 'du'.
		
		if (settledState->weight > maxTime){
			return (done = 1);	
		}
		
		ListNode* edges = vGetOutgoingEdgeList( settledVertex );
		while( edges ) 														//For each Edge 'edge'
		{                                 					
 		
 			Edge* edge = edges->data;
 			relaxVertex = edge->to;											//Get the destination vertex of the edge we are relaxing
 			

 			long old_w;
		  	if( (relaxVertex_spt = gGetVertex_NoHash( sptForward, relaxVertex )) ) //get the SPT Vertex corresponding to 'v'
		  	{        	
		    	relaxedState = (State*)relaxVertex_spt->payload;            					//and its State 'dv'      
				old_w = relaxedState->weight;
		    } 
		    else 
		    {
		    	relaxedState = NULL;                                       	//which may not exist yet
		        old_w = INFINITY;
		    }
		    		
		    State *newRelaxedState = eWalk( edge, settledState, options );			//get the state resulting from the new edge.
 			
 			if(!newRelaxedState) {													//is it null? Then something is wrong and we should move on
		    	edges = edges->next;
		    	continue;
		    }
		    
		    if (newRelaxedState->weight < settledState->weight)					//detect negative edge weights, if negative skip it
		    {					
		    	edges = edges->next;
		    	continue;
		    }
 			
 			long new_w = newRelaxedState->weight;									//get the new weight
 			
			if( new_w < old_w ) 
			{
			  	dirfibheap_insert_or_dec_key( forward_q, relaxVertex, new_w );    	// rekey or insert using the new weight
			
			  	
			  	if( !relaxVertex_spt ) 												//this is the first time we've seen this vertex
			  	{											
			    	relaxVertex_spt = gAddVertex_NoHash( sptForward, relaxVertex ); //add it to the shortest path tree
			    }
			
				if(relaxVertex_spt->payload)
				{
				    stateDestroy(relaxVertex_spt->payload);
				}
			  	
			  	relaxVertex_spt->payload = newRelaxedState;                      		//Set the State in the SPT to the current winner
				vSetParent( relaxVertex_spt, spt_settledVertex, edge->payload );      //Make u the parent of v in the SPT
			} 
			else 
			{
			  stateDestroy(newRelaxedState); 										//dont need it
			}
			
			edges = edges->next;
		}
	}
	else 
	{
		done = 1;
	}
	
	return done;
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

	surface = cairo_image_surface_create (CAIRO_FORMAT_A1, PNG_PIXELS_WIDTH, PNG_PIXELS_HEIGHT);
	cr = cairo_create (surface);
	
	cairo_set_source_rgba (cr, 1, 1, 1, 0.0);
	cairo_set_line_width (cr, 1.2);	

	paintLine(origin_v->lat, origin_v->lon, target_v->lat, target_v->lon, cr);

	cairo_surface_write_to_png(surface, "explorerimages/blah.png");
		
}
