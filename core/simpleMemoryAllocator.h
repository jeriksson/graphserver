#ifndef MemoryAllocator
#define MemoryAllocator

#define USE_ALLOCATOR

#include <string.h>

typedef struct _simpleMemoryAllocator {
	void * objects;				//Pointer to all the memory we have
	int sizeInObjects;			//Total size of the slab we are allocating
	int currentObjectsAllocated;		//The total number of objects allocated thus far
	int sizeOfType;				//The size of the type in this slab
} simpleMemoryAllocator;


/*Functions for dealing with a memory allocator */

extern simpleMemoryAllocator * memCreateNewAllocator(size_t objectSize, int objectsToAllocate);

extern void * memAllocateNew(simpleMemoryAllocator * this);

extern void * memAllocateNewFromIndex(simpleMemoryAllocator * this, int index);

extern void memFreeObjectsAndResources(simpleMemoryAllocator * this, void (*f)(void *));

extern void memFreeObjects(simpleMemoryAllocator * this);

extern int memGetCurrentIndex(simpleMemoryAllocator * this);

extern void memForEachObject(simpleMemoryAllocator * this, void (*f)(void *));

extern void * memRetrieveObjectByIndex(simpleMemoryAllocator * this, int index);
#endif
