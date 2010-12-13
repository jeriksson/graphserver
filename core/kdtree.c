#include <stdlib.h>
#include <unistd.h>
#include <stdio.h>
#include "hashtable_gs.h"
#include "kdtree.h"
#include "dirfibheap.h"

//The starting point for generating the partition
void buildKDTree(Graph * theGraph)
{
	//each cell gets an id, here we initialize to 0
	cellGlobalCounter = 0;
	kdtree = buildVertexArrayAndGetTree(theGraph);
	readCellWeightsFromFile();
}

void figureOutEachVertexCell(Graph * theGraph){

	struct hashtable_itr *itr = hashtable_iterator(theGraph->vertices);
  	int next_exists = hashtable_count(theGraph->vertices);
	//iterate through the list
	while(itr && next_exists) {
	    Vertex* vtx = hashtable_iterator_value( itr );
	    getVertexCell(vtx);
	        
	    next_exists = hashtable_iterator_advance( itr );
	}
}


//Each grid block is a list of vertices. This function inserts a vertex into a list of vertices given a block address
void insertVertexIntoCellList(CellList ** listPtr, Vertex * v) {
	
	CellList * list = *listPtr;
	CellListNode * newListNode = NULL;

	if (!list) {
		list = (CellList *)malloc(sizeof(CellList));

		//lets make the distances infinity
		int i = 0; 
		for (; i < EstimatedNumberOfCells; ++i) {
			list->cellWeights[i] = INFINITY;
		}

		list->first = malloc(sizeof(CellListNode));
		newListNode = list->first;
		*listPtr = list;
	}
	else {
		
		list->last->next = malloc(sizeof(CellListNode));
                newListNode = list->last->next;
	}		
	
	newListNode->vert = v;
	newListNode->next = NULL;

	list->last = newListNode;
}

void getVertexCell(Vertex * v){
	
	KDNode * treeNode = kdtree;
	int cellIndex = -1;
	int depth = 0;
	
	while(1){
		cellIndex = treeNode->index;
		int useLat = depth % 2;	
		double comparisonDimension = 0;
		
		if (useLat)
			comparisonDimension = v->lat;	
		else
			comparisonDimension = v->lon;
			
		
		if (treeNode->leftChild &&
			comparisonDimension <= treeNode->pivot)
			treeNode = treeNode->leftChild;
		else if (treeNode->rightChild &&
			comparisonDimension > treeNode->pivot)			
			treeNode = treeNode->rightChild;
		else
			break;
			
		++depth;
	}
	v->cellNumber = cellIndex;
	insertVertexIntoCellList(&(cells[cellIndex]), v);	
}

/* This function starts by removing any vertices we don't want to consider
based on the min/max lat/long values in the header file. Then we envoke the main
build function. */
KDNode * buildVertexArrayAndGetTree(Graph * theGraph){
	
	memset(verticesArr, 0, VertexSize * sizeof(Vertex *));
	struct hashtable_itr *itr = hashtable_iterator(theGraph->vertices);
  	int next_exists = hashtable_count(theGraph->vertices);
	//iterate through the list of vertices
	while(itr && next_exists) {
	    Vertex* vtx = hashtable_iterator_value( itr );
	    if (vtx) {
			verticesArr[vtx->sequenceNumber]=vtx;
	    }    
	    
	    next_exists = hashtable_iterator_advance( itr );
	}
	
	//all vertices are now loaded...trim the ones we don't want based on Min & Max Lat/Long
	qsort(verticesArr, theGraph->sequenceCounter, sizeof(Vertex *), cmpLat);
	int i=0;
	int start=0;
	int end=0;
	
	for (;i<theGraph->sequenceCounter; ++i){
		if (verticesArr[i]->lat >= MIN_LATITUDE && start == 0) start=i;
		if (verticesArr[theGraph->sequenceCounter - (i + 1)]->lat <= MAX_LATITUDE && end == 0) end=theGraph->sequenceCounter - (i + 1);
	}
	
	qsort(verticesArr + start, end - start, sizeof(Vertex *), cmpLong);
	i=start;
	int endOfArrayCurrently=end;
	start=0;
	end=0;
	
	for (;i<endOfArrayCurrently+1; ++i){
		if (verticesArr[i]->lon >= MIN_LONGITUDE && start == 0) start=i;
		if (verticesArr[theGraph->sequenceCounter - (i + 1)]->lon <= MAX_LONGITUDE && end == 0) end=theGraph->sequenceCounter - (i + 1);
	}

	//ok, now call the REAL build function
	return build(verticesArr + start, end - start, 0);
}


int
cmpLat(const void *v1, const void *v2)
{
    /* The actual arguments to this function are "pointers to
       pointers to char", but strcmp() arguments are "pointers
       to char", hence the following cast plus dereference */

   if ( (*((const Vertex **) v1))->lat > (*((const Vertex **) v2))->lat ){
   		return 1;
   }
   else if ( (*((const Vertex **) v1))->lat < (*((const Vertex **) v2))->lat ){
   		return -1;
   }
   else {
   		return 0;
   }
}

int
cmpLong(const void *v1, const void *v2)
{
    /* The actual arguments to this function are "pointers to
       pointers to char", but strcmp() arguments are "pointers
       to char", hence the following cast plus dereference */

   if ( (*((const Vertex **) v1))->lon > (*((const Vertex **) v2))->lon ){
   		return 1;
   }
   else if ( (*((const Vertex **) v1))->lon < (*((const Vertex **) v2))->lon ){
   		return -1;
   }
   else {
   		return 0;
   }
}


/* The main recursive function that partitions the tree. The tree is 2-d so
we iterate back and forth using lat and long (%2).*/
KDNode * build(Vertex ** points, int size, int depth)
{
	if (size < MinCellSize){
		return NULL;
	}
	else{
		//create new Node
		KDNode * node = malloc(sizeof(KDNode));
		int useLat = depth % 2;	
		//sorting the points so we can get the median for the pivot point
		qsort(points, size, sizeof(Vertex *), (useLat)?cmpLat:cmpLong);
		
		if (useLat)
			node->pivot = points[size/2]->lat;
		else
			node->pivot = points[size/2]->lon;
		node->index = cellGlobalCounter++;
		
		node->leftChild = build(points, 
								size / 2,
								depth + 1);
								
		node->rightChild = build(points + size/2, 
								size / 2 + (size % 2),
								depth + 1);
		
		if (!node->leftChild && !node->rightChild){
			//this is a leaf node, add its points to it
			int i = 0;
			for (;i < size; ++i){
				points[i]->cellNumber = node->index;
				insertVertexIntoCellList(&(cells[node->index]), points[i]);
			}
		}
					
		return node;
	}
}

void printGridAsKml( KDNode * treeNode, int depth, FILE *file ) {
	if (!file){
		file = fopen("/home/tim/kdTree.kml","w+");
		fprintf(file, "\n<?xml version=\"1.0\" encoding=\"UTF-8\"?>");
		fprintf(file, "\n<kml xmlns=\"http://www.opengis.net/kml/2.2\">");
		fprintf(file, "\n<Document>");
		fprintf(file, "\n<name>KDTree</name>");
	}
	
	int useLat = depth % 2;		
	
	if (!treeNode->leftChild && !treeNode->rightChild)
		printLineAsKml(treeNode->pivot, useLat, file);
	
	if (treeNode->leftChild)
			printGridAsKml(treeNode->leftChild, depth+1, file);
	
	if (treeNode->rightChild)
			printGridAsKml(treeNode->rightChild, depth+1, file);
	
	if (depth == 0){
		fprintf(file, "\n</Document>");
		fclose(file);
	}
	
}


void printBoundingRectangles(int destIndex){
	
	int i = 0;
	
	FILE * file = fopen("/home/tim/kdTree.kml","w+");
	fprintf(file, "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
	fprintf(file, "<kml xmlns=\"http://www.opengis.net/kml/2.2\">\n");
	fprintf(file, "<Document>\n");
	fprintf(file, "<Style id=\"ourStyle\">\n<PolyStyle>\n<color>edff9999</color>\n<outline>1</outline>\n</PolyStyle>");
	fprintf(file, "\n<LineStyle>\n<color>edee0000</color>\n<width>3</width>\n</LineStyle>\n</Style>");

	fprintf(file, "\n<name>KDTree</name>");
	int counter = 0;
	
	for (;i < EstimatedNumberOfCells; ++i){
			
			if (cells[i]){
				printBoundingRectangleForCell(cells[i], file, destIndex);
				++counter;
			}
	}
	
	printf("Total cell count: %d \n", counter);
	fprintf(file, "</Document>\n");
	fprintf(file, "</kml>\n");
	fclose(file);	
}

void printBoundingRectangleForCell(CellList * cell, FILE * file, int destIndex){
		double minLat = 1000;
		double maxLat = 0;
		double minLong = 0;
		double maxLong = -1000;
		
		CellListNode * nodePtr = cell->first;
		
		while(nodePtr){
			
			Vertex * v = nodePtr->vert;
			if (v){
				if (v->lat > maxLat && v->lat <= MAX_LATITUDE) maxLat = v->lat;
				if (v->lat < minLat && v->lat >= MIN_LATITUDE) minLat = v->lat;
				if (v->lon > maxLong && v->lon <= MAX_LONGITUDE) maxLong = v->lon;
				if (v->lon < minLong && v->lon >= MIN_LONGITUDE) minLong = v->lon;
			}
			nodePtr = nodePtr->next;
		}
		
		if (maxLat != 0 && minLong != 0 && minLat != 0 && maxLong != -1000){
			fprintf(file, "<Placemark>\n");
			fprintf(file, "<description>CellIndex: %d, Distance To Index : %d</description>", cell->first->vert->cellNumber,
					cells[cell->first->vert->cellNumber]->cellWeights[destIndex]);
			fprintf(file, "<styleUrl>#ourStyle</styleUrl>");
			fprintf(file, "<Polygon>\n");
			fprintf(file, "<outerBoundaryIs>\n");
			fprintf(file, "<LinearRing>\n");
			fprintf(file, "<coordinates>\n");
			fprintf(file, "%lf,%lf\n", minLong,maxLat);
			fprintf(file, "%lf,%lf\n", minLong,minLat);
			fprintf(file, "%lf,%lf\n", maxLong,minLat);
			fprintf(file, "%lf,%lf\n", maxLong,maxLat);
			fprintf(file, "</coordinates>\n");
			fprintf(file, "</LinearRing>\n");
			fprintf(file, "</outerBoundaryIs>\n");
			fprintf(file, "</Polygon>\n");
			fprintf(file, "</Placemark>\n");
		}
		
}

void printLineAsKml(double pivot, int useLat, FILE * file){

	fprintf(file, "\n<Placemark>");
	fprintf(file, "\n<LineString>");
	
	if (useLat){
		fprintf(file, "\n<coordinates>-87.5,%lf -88.5,%lf</coordinates>", pivot, pivot);
	}
	else{
		fprintf(file, "\n<coordinates>%lf,42.3 %lf,41.5</coordinates>", pivot, pivot);
	}	
	fprintf(file, "\n</LineString>");	
	fprintf(file, "\n</Placemark>");
}


void readCellWeightsFromFile(){

	FILE * file;
	char fileName[40];
	char str[25];
	char delims[] = ":";
	char * token = NULL;
	int currentIndex,targetIndex,weight,counter, index;
	//we need to loop through all the files that contain grid distances
	for (index=0; index < EstimatedNumberOfCells; ++index){
		sprintf(fileName, "/home/tim/graphserver/kdtreeInput/cellDistances%d", index);
		file = fopen(fileName,"r");
		if (file){
			//now that we have the file, start parsing it.
			while (fgets ( str, 26, file )) {
				token = strtok( str, delims );
				counter = 0;
				while (token){
					switch (counter){
						case 0 : currentIndex = atoi(token);
							 break;						
						case 1 : targetIndex = atoi(token);
							 break;
						case 2 : weight = atoi(token);
							 break;
					}
					counter++;
					token = strtok( NULL, delims );
				}
				
				cells[currentIndex]->cellWeights[targetIndex] = weight;
			}
			cells[currentIndex]->cellWeights[currentIndex] = 0;
			fclose(file);
		}
	}	

}


void writeCellWeightsToAFileForABlock(int index){
	int k;
	FILE *file;
	char fileName[30];
	sprintf(fileName, "~/graphserver/kdtreeInput/cellDistances%d", index);
	file = fopen(fileName,"w+");

	for (k = 0; k < EstimatedNumberOfCells; ++k) {
		if (cells[index] && cells[index]->cellWeights[k] < INFINITY)
			fprintf(file, "%6d:%6d:%10d ", index, k, cells[index]->cellWeights[k]);
	}	
	fclose(file);
}

void
gShortestPathForKDTree( Graph* this, State* init_state, WalkOptions* options, long maxtime, int index) {

  //create the spt
  Graph* spt = gNew();
  //create the fib heap
  dirfibheap_t q = dirfibheap_new();
  //first add all the vertices to the spt and the priority queue
  CellList * list = cells[index];
  if (list) {
  	CellListNode * listIterator = list->first;
   	while (listIterator) {
		//insert into the shortest path tree
	  	gAddVertex_NoHash( spt, listIterator->vert )->payload = init_state;
		//insert into the priority queue with a key of zero
	  	dirfibheap_insert_or_dec_key( q, listIterator->vert, 0 );
	    listIterator = listIterator->next;
  	}
  //Iteration Variables
  Vertex *u, *v;
  Vertex *spt_u, *spt_v;
  State *du, *dv;
  int count = 1;

  while( !dirfibheap_empty( q ) ) {                  //Until the priority queue is empty:
    u = dirfibheap_extract_min( q );                 //get the lowest-weight Vertex 'u',
    spt_u = gGetVertex_NoHash( spt, u );             //get corresponding SPT Vertex,
    
    du = (State*)spt_u->payload;                     //and get State of u 'du'.

    ListNode* edges = vGetOutgoingEdgeList( u );

    while( edges ) {                                 //For each Edge 'edge' connecting u
    	Edge* edge = edges->data;

      	v = edge->to;                                  //to Vertex v:

      	long old_w;
      	if( (spt_v = gGetVertex_NoHash( spt, v )) ) {        //get the SPT Vertex corresponding to 'v'
			dv = (State*)spt_v->payload;                     //and its State 'dv'      
			old_w = dv->weight;
      	} 
      	else {
			dv = NULL;                                       //which may not exist yet
			old_w = INFINITY;
      	}

      	State *new_dv = eWalk( edge, du, options );

      	// When an edge leads nowhere (as indicated by returning NULL), the iteration is over.
      	if(!new_dv) {
			edges = edges->next;
			continue;
      	}

      	// States cannot have weights lower than their parent State.
      	if(new_dv->weight < du->weight) {
			fprintf(stderr, "Negative weight (%s(%ld) -> %s(%ld))\n",edge->from->label, du->weight, edge->to->label, new_dv->weight);
			edges = edges->next;
			continue;
      	}

      	long new_w = new_dv->weight;
      	// If the new way of getting there is better,
      	if( new_w < old_w ) {
			dirfibheap_insert_or_dec_key( q, v, new_w );    // rekey v in the priority queue
			if (new_w < cells[index]->cellWeights[v->cellNumber]) {
				cells[index]->cellWeights[v->cellNumber] = new_w;
			}

			// If this is the first time v has been reached
			if( !spt_v ) {
	  			spt_v = gAddVertex_NoHash( spt, v );        //Copy v over to the SPT
	  			count++;
	  		}

			if(spt_v->payload){
			    stateDestroy(spt_v->payload);	
			}
			spt_v->payload = new_dv;                      //Set the State of v in the SPT to the current winner

			vSetParent( spt_v, spt_u, edge->payload );      //Make u the parent of v in the SPT
      	} 
      	else {
			stateDestroy(new_dv); //new_dv will never be used; merge it with the infinite.
      	}
      	edges = edges->next;
    }
  }
	  
	  printf("total vertices visited....%d\n", count);
	  
	  writeCellWeightsToAFileForABlock(index);
	  dirfibheap_delete( q );
	  gDestroy_NoHash( spt );

  }

}



