#include <string.h>
#include <stdlib.h>
#include <stdio.h>

#include "simpleMemoryAllocator.h"

simpleMemoryAllocator * memCreateNewAllocator(size_t objectSize, int objectsToAllocate) {
	simpleMemoryAllocator * theAllocator = malloc(sizeof(simpleMemoryAllocator));
	if (theAllocator) {
		theAllocator->objects = malloc(objectSize * objectsToAllocate);
		memset(theAllocator->objects, 0, objectSize * objectsToAllocate);
		theAllocator->sizeInObjects = objectsToAllocate;
		theAllocator->currentObjectsAllocated = 0;
		theAllocator->sizeOfType = objectSize;
		return theAllocator;
	}
	else {
		fprintf(stderr, "Malloc failed in memCreateNewAllocator\n");
		return NULL;
	}
}

int memGetCurrentIndex(simpleMemoryAllocator * this) {
	return (this->currentObjectsAllocated) ? this->currentObjectsAllocated - 1 : 0;
}

void * memRetrieveObjectByIndex(simpleMemoryAllocator * this, int index) {
	if (this && this->objects && index >= 0 && index < this->currentObjectsAllocated) 
		return (this->objects + (index * this->sizeOfType));
	else 
		return NULL;
}

void * memAllocateNew(simpleMemoryAllocator * this) {
	void * obj;
	if (this->currentObjectsAllocated < this->sizeInObjects - 1) {
		obj = this->objects + (this->currentObjectsAllocated * this->sizeOfType);
		this->currentObjectsAllocated++;
		return obj;
	}
	else
	{
		fprintf(stderr, "Ran out of memory in the allocated slab, objects allocated: %d, sizeInObjects: %d\n", this->currentObjectsAllocated, this->sizeInObjects - 1);
		return NULL;
	}
}

void * memAllocateNewFromIndex(simpleMemoryAllocator * this, int index) {
	void * obj = NULL;
	if (index < this->sizeInObjects - 1) {
		obj = this->objects + (index * this->sizeOfType);
		if (this->currentObjectsAllocated <= index)
			this->currentObjectsAllocated = index + 1;		
		return obj;
	}
	else
	{
		fprintf(stderr, "Ran out of memory in the allocated slab\n");
		return NULL;
	}
}

void memFreeObjects(simpleMemoryAllocator * this) {
	free(this->objects);
	free(this);
}

void memForEachObject(simpleMemoryAllocator * this, void (*f)(void *)) {
	int i = 0; 
	for (; i < this->currentObjectsAllocated; ++i)
	{
		(*f)(this->objects + (i * this->sizeOfType));
	}
}

void memFreeObjectsAndResources(simpleMemoryAllocator * this, void (*f)(void *)) {
        int i = 1;
        for (; i < this->currentObjectsAllocated; ++i)
        {
                (*f)(this->objects + (i * this->sizeOfType));
        }
                
        (*f)(this->objects);
        free(this->objects);
        free(this);
}

