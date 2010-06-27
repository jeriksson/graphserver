
import atexit
from ctypes import cdll, CDLL, pydll, PyDLL, CFUNCTYPE
from ctypes import string_at, byref, c_int, c_long, c_float, c_size_t, c_char_p, c_double, c_void_p, py_object
from ctypes import Structure, pointer, cast, POINTER, addressof
from ctypes.util import find_library

import os
import sys

# The libgraphserver.so object:
lgs = None

# Try loading from the source tree. If that doesn't work, fall back to the installed location.
_dlldirs = [os.path.dirname(os.path.abspath(__file__)),
            os.path.dirname(os.path.abspath(__file__)) + '/../../core',
            '/usr/lib',
            '/usr/local/lib']

for _dlldir in _dlldirs:
    _dllpath = os.path.join(_dlldir, 'libgraphserver.so')
    if os.path.exists(_dllpath):
        print _dllpath
        print 'here'
	lgs = PyDLL( _dllpath )
        break

if not lgs:
    raise ImportError("unable to find libgraphserver shared library in the usual locations: %s" % "\n".join(_dlldirs))

libc = cdll.LoadLibrary(find_library('c'))


class _EmptyClass(object):
    pass

def instantiate(cls):
    """instantiates a class without calling the constructor"""
    ret = _EmptyClass()
    ret.__class__ = cls
    return ret

def cleanup():
    """ Perform any necessary cleanup when the library is unloaded."""
    pass

atexit.register(cleanup)

class CShadow(object):
    """ Base class for all objects that shadow a C structure."""
    @classmethod
    def from_pointer(cls, ptr):
        if ptr is None:
            return None
        
        ret = instantiate(cls)
        ret.soul = ptr
        return ret
        
    def check_destroyed(self):
        if self.soul is None:
            raise Exception("You are trying to use an instance that has been destroyed")

def pycapi(func, rettype, cargs=None):
    """Convenience function for setting arguments and return types."""
    func.restype = rettype
    if cargs:
        func.argtypes = cargs


def caccessor(cfunc, restype, ptrclass=None):
    """Wraps a C data accessor in a python function.
       If a ptrclass is provided, the result will be converted to by the class' from_pointer method."""
    cfunc.restype = restype
    cfunc.argtypes = [c_void_p]
    if ptrclass:
        def prop(self):
            self.check_destroyed()
            ret = cfunc( c_void_p( self.soul ) )
            return ptrclass.from_pointer(ret)
    else:
        def prop(self):
            self.check_destroyed()
            return cfunc( c_void_p( self.soul ) )
    return prop

def cmutator(cfunc, argtype, ptrclass=None):
    """Wraps a C data mutator in a python function.  
       If a ptrclass is provided, the soul of the argument will be used."""
    cfunc.argtypes = [c_void_p, argtype]
    if ptrclass:
        def propset(self, arg):
            cfunc( self.soul, arg.soul )
    else:
        def propset(self, arg):
            cfunc( self.soul, arg )
    return propset

def cproperty(cfunc, restype, ptrclass=None, setter=None):
    """if restype is c_null_p, specify a class to convert the pointer into"""
    if not setter:
        return property(caccessor(cfunc, restype, ptrclass))
    return property(caccessor(cfunc, restype, ptrclass),
                    cmutator(setter, restype, ptrclass))

def ccast(func, cls):
    """Wraps a function to casts the result of a function (assumed c_void_p)
       into an object using the class's from_pointer method."""
    func.restype = c_void_p
    def _cast(self, *args):
        return cls.from_pointer(func(*args))
    return _cast

# GRAPH API        
pycapi(lgs.gNew, c_void_p)
pycapi(lgs.gDestroy, c_void_p, [c_void_p,c_int,c_int])
pycapi(lgs.gDestroy_NoHash, c_void_p, [c_void_p])
pycapi(lgs.gAddVertex, c_void_p, [c_void_p, c_char_p, c_float, c_float])
pycapi(lgs.gRemoveVertex, c_void_p, [c_void_p, c_char_p, c_int, c_int])
pycapi(lgs.gGetVertex, c_void_p, [c_void_p, c_char_p])
pycapi(lgs.gAddEdge, c_void_p, [c_void_p, c_char_p, c_char_p, c_void_p])
pycapi(lgs.gVertices, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.gShortestPathTree, c_void_p, [c_void_p, c_char_p, c_char_p, c_void_p, c_void_p, c_long])
pycapi(lgs.gShortestPathTreeRetro, c_void_p, [c_void_p, c_char_p, c_char_p, c_void_p, c_void_p, c_long])
pycapi(lgs.gSize,c_void_p, [c_long])
pycapi(lgs.sptPathRetro,c_void_p, [c_void_p, c_void_p, c_void_p])
pycapi(lgs.gSetVertexEnabled,c_void_p, [c_void_p, c_char_p, c_int])
pycapi(lgs.gAddVertices, c_void_p, [c_void_p, c_char_p, c_void_p, c_void_p, c_int])
pycapi(lgs.gSetThicknesses, c_void_p, [c_void_p, c_char_p])

# SERVICE PERIOD API 
pycapi(lgs.spNew, c_void_p, [c_long, c_long, c_int, c_void_p])
pycapi(lgs.spRewind, c_void_p, [c_void_p])
pycapi(lgs.spFastForward, c_void_p, [c_void_p])
pycapi(lgs.spDatumMidnight, c_long, [c_void_p, c_int])
pycapi(lgs.spNormalizeTime, c_long, [c_void_p, c_int, c_long])
pycapi(lgs.spBeginTime, c_long, [c_void_p])
pycapi(lgs.spEndTime, c_long, [c_void_p])
pycapi(lgs.spNextPeriod, c_void_p, [c_void_p])
pycapi(lgs.spPreviousPeriod, c_void_p, [c_void_p])
pycapi(lgs.spServiceIds, c_void_p, [c_void_p, c_void_p])

# SERVICE CALENDAR API
pycapi(lgs.scNew, c_void_p, [])
pycapi(lgs.scPeriodOfOrAfter, c_void_p, [c_void_p, c_int])
pycapi(lgs.scPeriodOfOrBefore, c_void_p, [c_void_p, c_int])
pycapi(lgs.scAddPeriod, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.scGetServiceIdInt, c_int, [c_void_p, c_char_p])
pycapi(lgs.scGetServiceIdString, c_char_p, [c_void_p, c_int])
pycapi(lgs.scDestroy, c_void_p, [c_void_p])
pycapi(lgs.scHead, c_void_p, [c_void_p])

# TIMEZONE PERIOD API
pycapi(lgs.tzpNew, c_void_p, [c_long, c_long, c_int])
pycapi(lgs.tzpDestroy, None, [c_void_p])
pycapi(lgs.tzpUtcOffset, c_int, [c_void_p])
pycapi(lgs.tzpBeginTime, c_long, [c_void_p])
pycapi(lgs.tzpEndTime, c_long, [c_void_p])
pycapi(lgs.tzpNextPeriod, c_void_p, [c_void_p])
pycapi(lgs.tzpTimeSinceMidnight, c_int, [c_void_p, c_long])

# TIMEZONE API
pycapi(lgs.tzNew, c_void_p, [])
pycapi(lgs.tzAddPeriod, c_void_p, [c_void_p])
pycapi(lgs.tzPeriodOf, c_void_p, [c_void_p, c_long])
pycapi(lgs.tzUtcOffset, c_int, [c_void_p, c_long])
pycapi(lgs.tzHead, c_void_p, [c_void_p])
pycapi(lgs.tzDestroy, c_void_p, [c_void_p])
pycapi(lgs.tzTimeSinceMidnight, c_int, [c_void_p, c_long])

# STATE API
pycapi(lgs.stateNew, c_void_p, [c_int, c_long])
pycapi(lgs.stateDup, c_void_p)
pycapi(lgs.stateDestroy, c_void_p)
pycapi(lgs.stateServicePeriod, c_void_p, [c_int])
pycapi(lgs.stateGetNumAgencies, c_int, [c_void_p])
pycapi(lgs.stateGetTripId, c_char_p, [c_void_p])
pycapi(lgs.stateSetDistWalked, c_void_p, [c_void_p, c_double])
pycapi(lgs.stateSetNumTransfers, c_void_p, [c_void_p, c_int])
pycapi(lgs.stateSetPrevEdge, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.stateSetServicePeriod, c_void_p, [c_void_p, c_int, c_void_p])
pycapi(lgs.stateSetTime, c_void_p, [c_void_p, c_long])
pycapi(lgs.stateSetWeight, c_void_p, [c_void_p, c_long])

# VERTEX API
pycapi(lgs.vNew, c_void_p, [c_char_p, c_float, c_float])
pycapi(lgs.vDestroy, c_void_p, [c_void_p,c_int,c_int])
pycapi(lgs.vDegreeIn, c_int, [c_void_p])
pycapi(lgs.vDegreeOut, c_int, [c_void_p])
pycapi(lgs.vGetOutgoingEdgeList, c_void_p, [c_void_p])
pycapi(lgs.vGetIncomingEdgeList, c_void_p, [c_void_p])
pycapi(lgs.vGetLabel, c_char_p, [c_void_p])
pycapi(lgs.vGetLat, c_float, [c_void_p])
pycapi(lgs.vGetLon, c_float, [c_void_p])
pycapi(lgs.vPayload, c_void_p, [c_void_p])

# EDGE API
pycapi(lgs.eNew, c_void_p, [c_void_p, c_void_p, c_void_p])
pycapi(lgs.eGetFrom, c_void_p, [c_void_p])
pycapi(lgs.eGetTo, c_void_p, [c_void_p])
pycapi(lgs.eGetPayload, c_void_p, [c_void_p])
pycapi(lgs.eWalk, c_void_p, [c_void_p, c_void_p, c_int])
pycapi(lgs.eWalkBack, c_void_p, [c_void_p, c_void_p, c_int])
pycapi(lgs.eSetEnabled, c_void_p, [c_void_p, c_int])
pycapi(lgs.eSetThickness, c_void_p, [c_void_p, c_long])

# EDGEPAYLOAD API
pycapi(lgs.epGetType, c_int, [c_void_p])
pycapi(lgs.epWalk, c_void_p, [c_void_p, c_void_p, c_int])
pycapi(lgs.epWalkBack, c_void_p, [c_void_p, c_void_p, c_int])

# LINKNODE API
pycapi(lgs.linkNew, c_void_p)
pycapi(lgs.linkDestroy, c_void_p)
pycapi(lgs.linkWalk, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.linkWalkBack, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.linkGetName, c_char_p, [c_void_p])

# LIST NODE API
pycapi(lgs.liGetData, c_void_p, [c_void_p])
pycapi(lgs.liGetNext, c_void_p, [c_void_p])

# STREET API
pycapi(lgs.streetNew, c_void_p, [c_char_p, c_double])
pycapi(lgs.streetNewElev, c_void_p, [c_char_p, c_double, c_float, c_float])
pycapi(lgs.streetDestroy, c_void_p)
pycapi(lgs.streetWalk, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.streetWalkBack, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.streetGetFall, c_float, [c_void_p])
pycapi(lgs.streetGetLength, c_double, [c_void_p])
pycapi(lgs.streetGetName, c_char_p, [c_void_p])
pycapi(lgs.streetGetRise, c_float, [c_void_p])
pycapi(lgs.streetSetSlog, c_void_p, [c_void_p, c_float])
pycapi(lgs.streetSetWay, c_void_p, [c_void_p, c_long])

# EGRESS API
pycapi(lgs.egressNew, c_void_p, [c_char_p, c_double])
pycapi(lgs.egressDestroy, c_void_p)
pycapi(lgs.egressWalk, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.egressWalkBack, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.egressGetLength, c_double, [c_void_p])
pycapi(lgs.egressGetName, c_char_p, [c_void_p])

# HEADWAY API
pycapi(lgs.headwayWalk, c_void_p, [c_void_p, c_void_p, c_int])
pycapi(lgs.headwayWalkBack, c_void_p, [c_void_p, c_void_p, c_int])
pycapi(lgs.headwayAgency, c_int, [c_void_p])
pycapi(lgs.headwayBeginTime, c_int, [c_void_p])
pycapi(lgs.headwayCalendar, c_void_p, [c_void_p])
pycapi(lgs.headwayEndTime, c_int, [c_void_p])
pycapi(lgs.headwayNew, c_void_p, [c_int, c_int, c_int, c_int, c_char_p, c_void_p, c_void_p, c_int, c_int])
pycapi(lgs.headwayServiceId, c_int, [c_void_p])
pycapi(lgs.headwayTimezone, c_void_p, [c_void_p])
pycapi(lgs.headwayTransit, c_int, [c_void_p])
pycapi(lgs.headwayTripId, c_char_p, [c_void_p])
pycapi(lgs.headwayWaitPeriod, c_int, [c_void_p])

# HEADWAY ALIGHT API
pycapi(lgs.haDestroy, c_void_p, [c_void_p])
pycapi(lgs.haGetAgency, c_int, [c_void_p])
pycapi(lgs.haGetRouteType, c_int, [c_void_p])
pycapi(lgs.haGetCalendar, c_void_p, [c_void_p])
pycapi(lgs.haGetEndTime, c_int, [c_void_p])
pycapi(lgs.haGetHeadwaySecs, c_int, [c_void_p])
pycapi(lgs.haGetServiceId, c_int, [c_void_p])
pycapi(lgs.haGetStartTime, c_int, [c_void_p])
pycapi(lgs.haGetTimezone, c_void_p, [c_void_p])
pycapi(lgs.haGetTripId, c_char_p, [c_void_p])
pycapi(lgs.haNew, c_void_p, [c_int, c_void_p, c_void_p, c_int, c_int, c_char_p, c_int, c_int, c_int])

# HEADWAY BOARD API
pycapi(lgs.hbDestroy, c_void_p, [c_void_p])
pycapi(lgs.hbGetAgency, c_int, [c_void_p])
pycapi(lgs.hbGetRouteType, c_int, [c_void_p])
pycapi(lgs.hbGetCalendar, c_void_p, [c_void_p])
pycapi(lgs.hbGetEndTime, c_int, [c_void_p])
pycapi(lgs.hbGetHeadwaySecs, c_int, [c_void_p])
pycapi(lgs.hbGetServiceId, c_int, [c_void_p])
pycapi(lgs.hbGetStartTime, c_int, [c_void_p])
pycapi(lgs.hbGetTimezone, c_void_p, [c_void_p])
pycapi(lgs.hbGetTripId, c_char_p, [c_void_p])
pycapi(lgs.hbNew, c_void_p, [c_int, c_void_p, c_void_p, c_int, c_int, c_char_p, c_int, c_int, c_int])

# TRIPBOARD API
pycapi(lgs.tbNew, c_void_p, [c_int, c_void_p, c_void_p, c_int, c_int])
pycapi(lgs.tbWalk, c_void_p, [c_void_p, c_void_p, c_int])
pycapi(lgs.headwayWalk, c_void_p, [c_void_p, c_void_p, c_int])
pycapi(lgs.tbAddBoarding, c_void_p, [c_void_p, c_char_p, c_int])
pycapi(lgs.tbGetBoardingTripId, c_char_p, [c_void_p, c_int])
pycapi(lgs.tbGetBoardingDepart, c_int, [c_void_p, c_int])
pycapi(lgs.tbDestroy, c_void_p, [c_void_p])
pycapi(lgs.tbGetAgency, c_int, [c_void_p])
pycapi(lgs.tbGetCalendar, c_void_p, [c_void_p])
pycapi(lgs.tbGetNextBoardingIndex, c_int, [c_void_p, c_int])
pycapi(lgs.tbGetNumBoardings, c_int, [c_void_p])
pycapi(lgs.tbGetOverage, c_int, [c_void_p])
pycapi(lgs.tbGetRouteType, c_int, [c_void_p])
pycapi(lgs.tbGetServiceId, c_int, [c_void_p])
pycapi(lgs.tbGetTimezone, c_void_p, [c_void_p])
pycapi(lgs.tbSearchBoardingsList, c_int, [c_void_p, c_int])

# ALIGHT API
pycapi(lgs.alGetAlightingTripId, c_char_p, [c_void_p, c_int])
pycapi(lgs.alGetAlightingArrival, c_int, [c_void_p, c_int])
pycapi(lgs.alAddAlighting, c_void_p, [c_void_p, c_char_p, c_int])
pycapi(lgs.alDestroy, c_void_p, [c_void_p])
pycapi(lgs.alGetAgency, c_int, [c_void_p])
pycapi(lgs.alGetCalendar, c_void_p, [c_void_p])
pycapi(lgs.alGetLastAlightingIndex, c_int, [c_void_p, c_int])
pycapi(lgs.alGetNumAlightings, c_int, [c_void_p])
pycapi(lgs.alGetRouteType, c_int, [c_void_p])
pycapi(lgs.alGetServiceId, c_int, [c_void_p])
pycapi(lgs.alGetTimezone, c_void_p, [c_void_p])
pycapi(lgs.alNew, c_void_p, [c_int, c_void_p, c_void_p, c_int, c_int])
pycapi(lgs.alSearchAlightingsList, c_int, [c_void_p, c_int])

# ELAPSE TIME API
pycapi(lgs.elapseTimeNew, c_void_p, [c_long])
pycapi(lgs.elapseTimeDestroy, c_void_p)
pycapi(lgs.elapseTimeWalk, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.elapseTimeWalkBack, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.elapseTimeGetSeconds, c_long, [c_void_p])

# CUSTOM PAYLOAD API
pycapi(lgs.cpDestroy, c_void_p, [c_void_p])
pycapi(lgs.cpNew, c_void_p, [c_void_p, c_void_p])

# CROSSING API
pycapi(lgs.crDestroy, c_void_p, [c_void_p])
pycapi(lgs.crGetCrossingTime, c_int, [c_void_p])
pycapi(lgs.crNew, c_void_p, [c_int])

# WAIT API
pycapi(lgs.waitDestroy, c_void_p, [c_void_p])
pycapi(lgs.waitGetEnd, c_long, [c_void_p])
pycapi(lgs.waitGetTimezone, c_void_p, [c_void_p])
pycapi(lgs.waitNew, c_void_p, [c_long, c_void_p])
pycapi(lgs.waitWalk, c_void_p, [c_void_p, c_void_p, c_void_p])
pycapi(lgs.waitWalkBack, c_void_p, [c_void_p, c_void_p, c_void_p])

# WALK OPTIONS API
pycapi(lgs.woDestroy, c_void_p, [c_void_p])
pycapi(lgs.woNew, c_void_p)
pycapi(lgs.woSetDownhillFastness, c_void_p, [c_void_p, c_float])
pycapi(lgs.woSetHillReluctance, c_void_p, [c_void_p, c_float])
pycapi(lgs.woSetMaxWalk, c_void_p, [c_void_p, c_int])
pycapi(lgs.woSetTransferPenalty, c_void_p, [c_void_p, c_int])
pycapi(lgs.woSetTurnPenalty, c_void_p, [c_void_p, c_int])
pycapi(lgs.woSetUphillSlowness, c_void_p, [c_void_p, c_float])
pycapi(lgs.woSetWalkingOverage, c_void_p, [c_void_p, c_float])
pycapi(lgs.woSetWalkingReluctance, c_void_p, [c_void_p, c_float])
pycapi(lgs.woSetWalkingSpeed, c_void_p, [c_void_p, c_float])
pycapi(lgs.woGetTransitTypes, c_int, [c_void_p])
pycapi(lgs.woSetTransitTypes, c_void_p, [c_void_p, c_int])

# LIBC API
pycapi(libc.free, c_void_p, [c_void_p])

# CUSTOM TYPE API
class PayloadMethodTypes:
    """ Enumerates the ctypes of the function pointers."""
    destroy = CFUNCTYPE(c_void_p, py_object)
    walk = CFUNCTYPE(c_void_p, py_object, c_void_p, c_void_p)
    walk_back = CFUNCTYPE(c_void_p, py_object, c_void_p, c_void_p)
    
pycapi(lgs.cpSoul, py_object, [c_void_p])
# args are not specified to allow for None
lgs.defineCustomPayloadType.restype = c_void_p
