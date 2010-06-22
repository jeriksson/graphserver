
#include "dirfibheap.h"

dirfibheap_t 
dirfibheap_new()
{
  dirfibheap_t ret = (dirfibheap_t)malloc( sizeof(struct dirfibheap) );
  ret->heap = fibheap_new();
  //ret->dir = create_hashtable_string(initSize);
  return ret;
}

fibnode_t
dirfibheap_insert_or_dec_key( dirfibheap_t self, Vertex* vtx, fibheapkey_t priority )
{
  char* key = vtx->label;
  
  //fibnode_t fibnode2 = hashtable_search( self->dir, key );
  fibnode_t fibnode = (vtx->heapIndex >= 0) ? memRetrieveObjectByIndex(self->heap->nodeMemoryAllocator, vtx->heapIndex) : NULL;

  if( fibnode ) {
    fibheap_replace_key( self->heap, fibnode, priority );
  } else {
    fibnode = fibheap_insert( self->heap, priority, (void*)vtx );
    vtx->heapIndex = fibnode->index;
    //hashtable_insert_string(self->dir, key, fibnode);

  }
  return fibnode;
}

Vertex*
dirfibheap_extract_min( dirfibheap_t self )
{
  Vertex* best = (Vertex*)fibheap_extract_min( self->heap );
  if(best) {
    //hashtable_remove(self->dir, best->label);
    best->heapIndex = -1;
  }
  return best;
}


int
dirfibheap_empty( dirfibheap_t self ) {
  int tmp = fibheap_empty( self->heap );
   return tmp;
}

void
dirfibheap_delete( dirfibheap_t self )
{
  //hashtable_destroy( self->dir, 0 ); //do not delete values in queue
  fibheap_delete( self->heap );
  free( self );
}
