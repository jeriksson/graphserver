all: libgraphserver.so

# to override base installation directory run
# PREFIX=... make install
PREFIX=/usr

OBJECTS= dirfibheap.o \
	edgetypes.o \
	fibheap.o \
	graph.o \
	hashtable.o \
	hashtable_gs.o \
	hashtable_itr.o \
	hashtable_utility.o \
	simpleMemoryAllocator.o \
	statetypes.o \
	explorer.o \
	kdtree.o \

# You know what? Honestly? I don't know what most of these switches do.
CFLAGS=-g -fno-strict-aliasing -fPIC -Wall
LDFLAGS= -L. -Bsymbolic-functions -Wall -ldl -lm -lc
CAIROLIB=$(shell pkg-config --cflags --libs cairo)

OS := $(shell uname)

ifeq ($(OS),Darwin)
  LDFLAGS += -dynamiclib
else
  LDFLAGS += -shared
endif

# This complicated-looking rule will autogenerate the appropriate dependancies
# for each source file, ensuring that they are recompiled when the headers
# they include change
# see: http://www.cs.berkeley.edu/~smcpeak/autodepend/autodepend.html
%.o: %.c
	cc $*.c -c -o $@ $(CFLAGS) $(CAIROLIB)
	cc $*.c -MM $(CFLAGS) $(CAIROLIB) > $*.d
	@mv -f $*.d $*.d.tmp
	@sed -e 's|.*:|$*.o:|' < $*.d.tmp > $*.d
	@sed -e 's/.*://' -e 's/\\$$//' < $*.d.tmp | fmt -1 | \
	  sed -e 's/^ *//' -e 's/$$/:/' >> $*.d
	@rm -f $*.d.tmp
-include $(OBJECTS:.o=.d)

libgraphserver.so: $(OBJECTS)
	cc -g -shared -o $@ $(OBJECTS) $(LDFLAGS) $(CAIROLIB)

install:
	cp libgraphserver.so $(PREFIX)/lib
	cp libgraphserver.so /usr/local/lib/python2.6/dist-packages/graphserver-0.1-py2.6.egg/graphserver
	mkdir -p $(PREFIX)/include/graphserver
	cp fibheap.h $(PREFIX)/include/graphserver
	cp dirfibheap.h $(PREFIX)/include/graphserver
	cp graph.h $(PREFIX)/include/graphserver
	cp hashtable_gs.h $(PREFIX)/include/graphserver
	cp hashtable_itr.h $(PREFIX)/include/graphserver
	cp edgetypes.h $(PREFIX)/include/graphserver
	cp hashtable.h $(PREFIX)/include/graphserver
	cp hashtable_utility.h $(PREFIX)/include/graphserver
	cp hashtable_private.h $(PREFIX)/include/graphserver
	cp statetypes.h $(PREFIX)/include/graphserver
	cp explorer.h $(PREFIX)/include/graphserver
	cp kdtree.h $(PREFIX)/include/graphserver
clean:
	rm -f *.o *.so *~ *.d
