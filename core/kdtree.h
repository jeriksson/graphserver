#ifndef KDTree
#define KDTree


#include "graph.h"


/* Used for construction */

//Hopefully this is enough to handle the size of the graph
#define VertexSize 2000000
#define MinCellSize 150
#define EstimatedNumberOfCells ((VertexSize / MinCellSize) * 2)

#define MAX_LATITUDE 42.3L
#define MAX_LONGITUDE -87.5L
#define MIN_LATITUDE 41.5L
#define MIN_LONGITUDE -88.5L

Vertex * verticesArr[VertexSize];

int cellGlobalCounter;

typedef struct _KDNode {

	double minLat;
	double maxLat;
	double minLong;
	double maxLong;
	double pivot;
	int index;
	struct _KDNode * leftChild;
	struct _KDNode * rightChild;
} KDNode;


KDNode * kdtree;

void buildKDTree(Graph * g);

void getVertexCell(Vertex * v);

KDNode * build(Vertex ** points, int size, int depth);

KDNode * buildVertexArrayAndGetTree(Graph * theGraph);

void figureOutEachVertexCell(Graph * theGraph);

void getVertexCell(Vertex * v);

int cmpLat(const void *v1, const void *v2);

int cmpLong(const void *v1, const void *v2);

void writeCellWeightsToAFileForABlock(int index);

void readCellWeightsFromFile();

/*******************************/

/* Used for Querying */

typedef struct _CellListNode {

	Vertex * vert;
	struct _CellListNode * next;

} CellListNode;

typedef struct _CellList {
	CellListNode * first;
	CellListNode * last;
	int cellWeights[EstimatedNumberOfCells];
} CellList;

CellList * cells[EstimatedNumberOfCells];

void insertVertexIntoCellList(CellList ** listPtr, Vertex * v);

/**********************************/
/* For debugging */

void printLineAsKml(double pivot, int useLat, FILE * file);

void printGridAsKml( KDNode * treeNode, int depth, FILE *file );

void printBoundingRectangles(int destIndex);

void printBoundingRectangleForCell(CellList * cell, FILE * file, int destIndex);


#endif