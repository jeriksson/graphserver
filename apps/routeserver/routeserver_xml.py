#
# Modified routeserver to output XML-formatted route results.
# Author: James P. Biagioni (jbiagi1@uic.edu)
# Company: University of Illinois at Chicago
# Last modified: 4/20/10
#

from routeserver_servable import Servable
from SocketServer import ForkingMixIn
from wsgiref.simple_server import WSGIServer, make_server
from graphserver.graphdb import GraphDatabase
import cgi
from graphserver.core import State, WalkOptions
import time
import sys
import graphserver
from graphserver.util import TimeHelpers
from graphserver.ext.osm.pgosmdb import PostgresGIS_OSMDB
from graphserver.ext.gtfs.pggtfsdb import PostgresGIS_GTFSDB
from math import fmod, sin, cos, atan2, pi, degrees
from graphserver.ext.osm.vincenty import vincenty
import json

from types import *
import re
import traceback
from urlparse import urlparse

try:
    from simplejson import loads as json_loads
except ImportError:
    from json import loads as json_loads

def xstr(arg):
    if arg is None:
        return ""
    else:
        return arg.encode('utf8')

class ChicagoMap:
    bounding_lon_left=-89.106976260401382
    bounding_lat_bottom=41.028302192122915
    bounding_lon_right=-86.866313839598618
    bounding_lat_top=42.948031407877082

class WalkPath:
    def __init__(self):
        self.name = ""
        self.dep_time = ""
        self.arr_time = ""
        self.points = []
        self.length = 0.0
        self.bearing = 0.0
        self.direction = ""
        self.turn_direction = ""
        self.lastlat = 0.0
        self.lastlon = 0.0
        self.total_distance = 0.0
        self.timezone = ""

class RouteInfo:
    def __init__(self):
        self.origlat = ""
        self.origlon = ""
        self.actual_dep_time = 0
        self.dep_time_diff = 0
        self.destlat = ""
        self.destlon = ""
        self.actual_arr_time = 0
        self.arr_time_diff = 0
        self.first_edge = True
        self.last_edge = False
        self.street_mode = ""
        self.retro_route = False

class MyWSGIServer(ForkingMixIn, WSGIServer):
    pass

class RoutingException (Exception):
    pass

class RouteServer:
    DEFAULT_MIME = "text/plain"        

    def __init__(self, graphdb_filename, pgosmdb_handle, pggtfsdb_handle, event_dispatch):
        graphdb = GraphDatabase( graphdb_filename )
        self.graph = graphdb.incarnate()
        self.graph.num_agencies = 3
        self.graph.numagencies = self.graph.num_agencies
        self.event_dispatch = event_dispatch
        self.pgosmdb = pgosmdb_handle
        self.pggtfsdb = pggtfsdb_handle
    
    def run_test_server(self, port=8080):
        print "starting RouteServer on port " + str(port)
        httpd = make_server('', port, self.wsgi_app(), MyWSGIServer)
        httpd.serve_forever()
    run_test_server.serve = False
    
    def wsgi_app(self):
        """returns a wsgi app which exposes this object as a webservice"""
        
        def myapp(environ, start_response):
            
            path_info = environ['PATH_INFO']
            query_string = environ['QUERY_STRING']
            
            #if not hasattr(self, 'pattern_cache'):
            #    self.pattern_cache = [(pth, args, pfunc) for pth, args, pfunc in self.patterns()]
            self.pattern_cache = [(re.compile('/path_xml'),[],self.path_xml),(re.compile('/transit_path'),[],self.transit_path)]
            
            for ppath, pargs, pfunc in self.pattern_cache:
                if ppath.match(path_info):
                    
                    args = cgi.parse_qs(query_string)
                    args = dict( [(k,v[0]) for k,v in args.iteritems()] )
                    
                    try:
                        #use simplejson to coerce args to native types
                        #don't attempt to convert an arg 'jsoncallback'; just ignore it.
                        arglist = []
                        for k,v in args.iteritems():
                            if k=="jsoncallback":
                                arglist.append( (k,v) )
                            elif k != "_":
                                arglist.append( (k,json_loads(v)) )
                        args = dict( arglist )
                        
                        if hasattr(pfunc, 'mime'):
                            mime = pfunc.mime
                        else:
                            mime = self.DEFAULT_MIME
                        
                        start_response('200 OK', [('Content-type', mime)])
                        #try:
#                        for value in pfunc(**args):
#                            rr = xstr( value )
                        #except TypeError:
                        #    problem = "Arguments different than %s"%str(pargs)
                        #    start_response('500 Internal Error', [('Content-type', 'text/plain'),('Content-Length', str(len(problem)))])
                        #    return [problem]
                        
                        return pfunc(**args)
                    except:
                        problem = traceback.format_exc()
                        start_response('500 Internal Error', [('Content-type', 'text/plain'),('Content-Length', str(len(problem)))])
                        return [problem]
                        
            # no match:
            problem = "No method corresponds to path '%s'"%environ['PATH_INFO']
            start_response('404 Not Found', [('Content-type', 'text/plain'),('Content-Length', str(len(problem)))])
            return [problem]
            
        return myapp
    
    def transit_path(self, trip_id, board_stop_id, alight_stop_id, origlon=0, origlat=0, destlon=0, destlat=0):
        
        sys.stderr.write("[transit_path_entry_point," + str(time.time()) + "]\n")
        
        ret_string = '<transit trip_id="' + str(trip_id) + '" board_stop_id="' + str(board_stop_id) + '" alight_stop_id="' + str(alight_stop_id) + '">'
        ret_string += '<points>'
        
        sys.stderr.write("[get_transit_path_points," + str(time.time()) + "]\n")
        for point in self.pggtfsdb.get_transit_path_points(trip_id, board_stop_id, alight_stop_id):
            ret_string += '<point lat="' + point[0:point.index(',')] + '" lon="' + point[point.index(',')+1:] + '" />'
        
        ret_string += '</points>'
        ret_string += '</transit>'
        
        sys.stderr.write("[transit_path_exit_point," + str(time.time()) + "]\n")
        yield ret_string
        return
        
    transit_path.mime = "text/xml"
    
    def shortest_path(self, origin, dest, dep_time, wo):
        
        # flag for retro-routes
        retro_route = False
        
        # generate shortest path tree based on departure time
        sys.stderr.write("[shortest_path_tree," + str(time.time()) + "]\n")
        spt = self.graph.shortest_path_tree( origin, dest, State(self.graph.num_agencies,dep_time), wo )
        
        # if there is no shortest path tree (i.e., there is no path between the origin and destination)
        if (spt is None):
            raise RoutingException
        
        # get path based on departure time
        dep_vertices, dep_edges = spt.path( dest )
        
        # if there are no edges or vertices (i.e., there is no path found)
        if ((dep_edges is None) or (dep_vertices is None)):
            raise RoutingException
        
        # grab soonest arrival time
        soonest_arr_time = dep_vertices[-1].payload.time
        
        # re-run query using soonest arrival time
        sys.stderr.write("[shortest_path_tree_retro," + str(time.time()) + "]\n")
        arr_spt = self.graph.shortest_path_tree_retro( origin, dest, State(self.graph.num_agencies,soonest_arr_time), wo )
        
        # if there is no shortest path tree (i.e., there is no path between the origin and destination)
        if (arr_spt is None):
            raise RoutingException
        
        # get path based on soonest arrival time
        arr_vertices, arr_edges = arr_spt.path_retro( origin )
        
        # if route based on soonest arrival time departs in the past, return the original departure-time based route
        if (arr_vertices[0].payload.time < dep_time):
            
            # destroy arrival-time based shortest path tree
            if (arr_spt is not None):
                arr_spt.destroy()
            
            # set vertices and edges
            vertices = dep_vertices
            edges = dep_edges
            
        else:
            # destroy departure-time based shortest path tree
            if (spt is not None):
                spt.destroy()
            
            # point spt at arrival-time based shortest path tree for proper cleanup
            spt = arr_spt
            
            # set vertices and edges
            vertices = arr_vertices
            edges = arr_edges
            
            # set retro-route flag
            retro_route = True
            
        return (spt, edges, vertices, retro_route)
    
    def shortest_path_retro(self, origin, dest, arr_time, wo):
        
        # flag for retro-routes
        retro_route = True
        
        # generate shortest path tree based on arrival time
        sys.stderr.write("[shortest_path_tree_retro," + str(time.time()) + "]\n")
        spt = self.graph.shortest_path_tree_retro( origin, dest, State(self.graph.num_agencies,arr_time), wo )
        
        # if there is no shortest path tree (i.e., there is no path between the origin and destination)
        if (spt is None): 
            raise RoutingException
        
        # get path based on arrival time
        arr_vertices, arr_edges = spt.path_retro( origin )
        
        # if there are no edges or vertices (i.e., there is no path found)
        if ((arr_edges is None) or (arr_vertices is None)):
            raise RoutingException
        
        # grab latest departure time
        latest_dep_time = arr_vertices[0].payload.time
        
        # re-run query using latest departure time
        sys.stderr.write("[shortest_path_tree," + str(time.time()) + "]\n")
        dep_spt = self.graph.shortest_path_tree( origin, dest, State(self.graph.num_agencies,latest_dep_time), wo )
        
        # if there is no shortest path tree (i.e., there is no path between the origin and destination)
        if (dep_spt is None):
            raise RoutingException
        
        # get path based on latest departure time
        dep_vertices, dep_edges = dep_spt.path( dest )
        
        # if route based on latest departure time arrives later than requested arrival time, return the original arrival-time based route
        if (dep_vertices[-1].payload.time > arr_time):
            
            # destroy departure-time based shortest path tree
            if (dep_spt is not None): 
                dep_spt.destroy()
            
            # set vertices and edges
            vertices = arr_vertices
            edges = arr_edges
            
        else:
            # destroy departure-time based shortest path tree
            if (spt is not None): spt.destroy()
            
            # point spt at departure-time based shortest path tree for proper cleanup
            spt = dep_spt
            
            # set vertices and edges
            vertices = dep_vertices
            edges = dep_edges
            
            # set retro-route flag
            retro_route = False
            
        return (spt, edges, vertices, retro_route) 	
    
    def path_xml(self, origlon, origlat, destlon, destlat, dep_time=0, arr_time=0, max_results=1, timezone="", transfer_penalty=100, walking_speed=1.0, walking_reluctance=1.0, max_walk=10000, walking_overage=0.1, seqno=0, street_mode="walk", less_walking="False", udid="", version="2.0"):
        
        sys.stderr.write("[xml_path_entry_point," + str(time.time()) + "] \"origlon=" + str(origlon) + "&origlat=" + str(origlat) + "&destlon=" + str(destlon) + "&destlat=" + str(destlat) + "&dep_time=" + str(dep_time) + "&arr_time=" + str(arr_time) + "&timezone=" + str(timezone) + "&transfer_penalty=" + str(transfer_penalty) + "&walking_speed=" + str(walking_speed) + "&walking_reluctance=" + str(walking_reluctance) + "&max_walk=" + str(max_walk) + "&walking_overage=" + str(walking_overage) + "&seqno=" + str(seqno) + "&street_mode=\"" + str(street_mode) + "\"&less_walking=\"" + str(less_walking) + "\"&udid=\"" + str(udid) + "\"&version=" + str(version) + "\"\n")
        
        if (origlon <= ChicagoMap.bounding_lon_left or origlon >= ChicagoMap.bounding_lon_right or 
            origlat <= ChicagoMap.bounding_lat_bottom or origlat >= ChicagoMap.bounding_lat_top or 
            destlon <= ChicagoMap.bounding_lon_left or destlon >= ChicagoMap.bounding_lon_right or 
            destlat <= ChicagoMap.bounding_lat_bottom or destlat >= ChicagoMap.bounding_lat_top):
            
            sys.stderr.write("[exit_outside_bounding_box," + str(time.time()) + "]\n")
            raise RoutingException
            #return '<?xml version="1.0"?><routes></routes>'
        
        # initialize spt to 'None' object
        spt = None
        
        try:
            # if the departure time is not specified, set it
            if (dep_time == 0):
                dep_time = int(time.time())
            
            # if the timezone is not specified, default to "America/Chicago"
            if (timezone == ""):
                timezone = "America/Chicago"
            
            # get origin and destination nodes from osm map
            sys.stderr.write("[get_osm_vertex_from_coords," + str(time.time()) + "]\n")
            orig_osm, orig_osm_dist = self.pgosmdb.get_osm_vertex_from_coords(origlon, origlat)
            dest_osm, dest_osm_dist = self.pgosmdb.get_osm_vertex_from_coords(destlon, destlat)
            
            #print "\nOrigin OSM: " + str(orig_osm) + " (" + str(orig_osm_dist) + ")"
            #print "Destination OSM: " + str(dest_osm) + " (" + str(dest_osm_dist) + ")\n"
            
            # get origin and destination nodes from gtfs database
            sys.stderr.write("[get_station_vertex_from_coords," + str(time.time()) + "]\n")
            orig_sta, orig_sta_dist = self.pggtfsdb.get_station_vertex_from_coords(origlon, origlat)
            dest_sta, dest_sta_dist = self.pggtfsdb.get_station_vertex_from_coords(destlon, destlat)
            
            #print "Origin STA: " + str(orig_sta) + " (" + str(orig_sta_dist) + ")"
            #print "Destination STA: " + str(dest_sta) + " (" + str(dest_sta_dist) + ")\n"
            
            # get coordinates for origin node
            if (orig_osm_dist < orig_sta_dist):
                origin = orig_osm
                sys.stderr.write("[get_coords_for_osm_vertex," + str(time.time()) + "]\n")
                orig_node_lat, orig_node_lon = self.pgosmdb.get_coords_for_osm_vertex(origin)
            else:
                origin = orig_sta
                sys.stderr.write("[get_coords_for_station_vertex," + str(time.time()) + "]\n")
                orig_node_lat, orig_node_lon = self.pggtfsdb.get_coords_for_station_vertex(origin)
                
            # get coordinates for destination node
            if (dest_osm_dist < dest_sta_dist):
                dest = dest_osm
                sys.stderr.write("[get_coords_for_osm_vertex," + str(time.time()) + "]\n")
                dest_node_lat, dest_node_lon = self.pgosmdb.get_coords_for_osm_vertex(dest)
            else:
                dest = dest_sta
                sys.stderr.write("[get_coords_for_station_vertex," + str(time.time()) + "]\n")
                dest_node_lat, dest_node_lon = self.pggtfsdb.get_coords_for_station_vertex(dest)
            
            #print "Origin: " + str(origin)
            #print "Destination: " + str(dest) + "\n"
            
            #print "Origin coords: " + str(orig_node_lat) + ", " + str(orig_node_lon)
            #print "Destination coords: " + str(dest_node_lat) + ", " + str(dest_node_lon)
            
            # determine distance from actual origin/destination to osm nodes
            orig_distance = vincenty(float(origlat), float(origlon), orig_node_lat, orig_node_lon)
            dest_distance = vincenty(dest_node_lat, dest_node_lon, float(destlat), float(destlon))
            
            #print "Origin distance: " + str(orig_distance)
            #print "Destination distance: " + str(dest_distance)
            
            # calculate time to origin and destination nodes (seconds)
            time_to_orig = int(round(float( float(orig_distance) / float(walking_speed) )))
            time_to_dest = int(round(float( float(dest_distance) / float(walking_speed) )))
            
            #print "Origin time: " + str(time_to_orig)
            #print "Destination time: " + str(time_to_dest)
            
            # adjust departure time by time needed to reach origin node
            dep_time = (dep_time + time_to_orig)
            
            # adjust arrival time by time needed to reach destination node
            if (arr_time != 0):
                arr_time = (arr_time - time_to_dest)
            
            #print "Adjusted departure time: " + str(dep_time)
            
            wo = WalkOptions()
            wo.transfer_penalty=transfer_penalty
            wo.walking_speed=walking_speed
            wo.walking_reluctance=walking_reluctance
            wo.max_walk=max_walk
            wo.walking_overage=walking_overage
            
            # check for less_walking flag
            if (less_walking == "True"):
                wo.walking_reluctance *= 10.0
            
            # check for bike street_mode
            if (street_mode == "bike"):
                wo.transfer_penalty *= 10
            
            # create RouteInfo object
            route_info = RouteInfo()
            route_info.origlat = origlat
            route_info.origlon = origlon
            route_info.dep_time_diff = time_to_orig
            route_info.destlat = destlat
            route_info.destlon = destlon
            route_info.arr_time_diff = time_to_dest
            route_info.street_mode = street_mode
            
            yield "--multipart-path_xml-boundary1234\n";
            
			# loop to create multiple responses
            for q in range(max_results): 
                route_info.last_edge = False
                
                # initialize return string
                ret_string = 'Content-Type: text/xml\n\n<?xml version="1.0"?><routes>'
                
                if (arr_time == 0):
                    (spt, edges, vertices, route_info.retro_route) = self.shortest_path(origin,dest,dep_time,wo)
                else:
                    (spt, edges, vertices, route_info.retro_route) = self.shortest_path_retro(origin,dest,arr_time,wo)
                
                # if there are no edges or vertices (i.e., there is no path found)
                if ((edges is None) or (vertices is None)): raise RoutingException
                
                # create WalkPath object
                walk_path = WalkPath()
                walk_path.lastlat = origlat
                walk_path.lastlon = origlon
                walk_path.timezone = timezone
                
                # string to store returned route
                curr_route = ""
                
                route_info.actual_dep_time = vertices[0].payload.time - time_to_orig
                route_info.actual_arr_time = vertices[-1].payload.time + time_to_dest
                
                # iterate through all edges in the route
                sys.stderr.write("[edges_loop," + str(time.time()) + "]\n")
                
                # determine the number of edges
                edges_len = len(edges)            
                for i in range(edges_len):
                    
                    if (i == (edges_len-1)):
                        route_info.last_edge = True
                    elif (i == (edges_len-2) and edges[i+1].payload.__class__ == graphserver.core.Link):
                        route_info.last_edge = True
                    elif (i == (edges_len-3) and edges[i+1].payload.__class__ == graphserver.core.Link and edges[i+2].payload.__class__ == graphserver.core.Link):
                        route_info.last_edge = True
                    
                    edgetype = edges[i].payload.__class__
                    if edgetype in self.event_dispatch:
                        (new_event, walk_path, route_info) = self.event_dispatch[ edges[i].payload.__class__ ]( vertices[i], edges[i], vertices[i+1], walk_path, route_info)
                        curr_route += new_event
                
                ret_string += '<route dep_time="' + str(route_info.actual_dep_time) + '" req_dep_time="' + str(dep_time - time_to_orig) + '" arr_time="' + str(route_info.actual_arr_time) + '" req_arr_time="' + str(arr_time) + '" timezone="' + timezone + '" total_time="' + str(route_info.actual_arr_time - route_info.actual_dep_time) + '" total_walk_distance="' + str(int(round(walk_path.total_distance)) + int(round(orig_distance)) + int(round(dest_distance))) + '" walking_speed="' + str(walking_speed) + '" seqno="' + str(seqno) + '" version="' + str(version) + '">' + curr_route + '</route>'
                
                # close return string
                ret_string += '</routes>\n\n--multipart-path_xml-boundary1234\n'
                sys.stderr.write("[xml_path_exit_point," + str(time.time()) + "]\n")
                
                # return routes xml
                yield xstr(str(ret_string))
                
                if arr_time == 0: 
                    dep_time = route_info.actual_dep_time + time_to_orig + 60
                else:
                    arr_time = route_info.actual_arr_time - time_to_dest - 60
                
        except RoutingException:
            yield '\n\n--multipart-path_xml-boundary1234\nContent-Type: text/xml\n\n<?xml version="1.0"?><routes></routes>--multipart-path_xml-boundary1234--\n\n '
        finally:
            yield '\n\n--multipart-path_xml-boundary1234--\n\n'
            # destroy WalkOptions object
            wo.destroy()
            
            # destroy shortest path tree
            if (spt is not None):
                spt.destroy()
        
    path_xml.mime = 'multipart/x-mixed-replace; boundary="--multipart-path_xml-boundary1234"'


import sys
if __name__ == '__main__':
    usage = "python routeserver_xml.py graphdb_filename pgosmdb_connect_string pggtfsdb_connect_string port_number"
    
    if len(sys.argv) < 5:
        print usage
        exit()
        
    graphdb_filename = sys.argv[1]
    pgosmdb_connect_string = sys.argv[2]
    pggtfsdb_connect_string = sys.argv[3]
    port_number = int(sys.argv[4])
    
    pgosmdb = PostgresGIS_OSMDB( pgosmdb_connect_string )
    pggtfsdb = PostgresGIS_GTFSDB( pggtfsdb_connect_string )

    def _path_bearing(path_points):
    
        # get first two points along path
        #point1 = path_points[0]
        #point2 = path_points[1]
        
        # get first and last points along path
        point1 = path_points[0]
        point2 = path_points[-1]
        
        # get latitude and longitude components
        lat1 = float(point1[point1.index(' ')+1:])
        lon1 = float(point1[0:point1.index(' ')])
        lat2 = float(point2[point2.index(' ')+1:])
        lon2 = float(point2[0:point2.index(' ')])
        
        # calculate bearing
        bearing = fmod(degrees(atan2(cos(lat1)*sin(lat2)-sin(lat1)*cos(lat2)*cos(lon2-lon1), sin(lon2-lon1)*cos(lat2))) + 270.0, 360.0)
        
        # return bearing
        return bearing
    
    def _print_dest_path(route_info, fromlat, fromlon):
        
        # find distance between last point and destination point
        path_length = vincenty(fromlat, fromlon, route_info.destlat, route_info.destlon)
        
        # determine path bearing
        path_bearing = _path_bearing([str(fromlon) + ' ' + str(fromlat), str(route_info.destlon) + ' ' + str(route_info.destlat)])
        
        # build destination string
        ret_string = '<end length="' + str(int(round(path_length))) + '" bearing="' + str(int(round(path_bearing))) + '" dep_time="' + str(route_info.actual_arr_time - route_info.arr_time_diff) + '" arr_time="' + str(route_info.actual_arr_time) + '">'
        ret_string += '<points>'
        ret_string += '<point lat="' + str(fromlat) + '" lon="' + str(fromlon) + '" />'
        ret_string += '<point lat="' + str(route_info.destlat) + '" lon="' + str(route_info.destlon) + '" />'
        ret_string += '</points>'
        ret_string += '</end>'
        
        return ret_string
    
    def _print_orig_path(route_info, tolat, tolon):
        
        # find distance between origin point and first point
        path_length = vincenty(route_info.origlat, route_info.origlon, tolat, tolon)
        
        # determine path bearing
        path_bearing = _path_bearing([str(route_info.origlon) + ' ' + str(route_info.origlat), str(tolon) + ' ' + str(tolat)])
        
        # build origin string
        ret_string = '<start length="' + str(int(round(path_length))) + '" bearing="' + str(int(round(path_bearing))) + '" dep_time="' + str(route_info.actual_dep_time) + '" arr_time="' + str(route_info.actual_dep_time + route_info.dep_time_diff) + '">'
        ret_string += '<points>'
        ret_string += '<point lat="' + str(route_info.origlat) + '" lon="' + str(route_info.origlon) + '" />'
        ret_string += '<point lat="' + str(tolat) + '" lon="' + str(tolon) + '" />'
        ret_string += '</points>'
        ret_string += '</start>'
        
        return ret_string
    
    def _print_walk_path(walk_path, route_info):
        ret_string = ""
        
        # find distances between first and last point from last point on previous walk path
        first_pt_dist = vincenty(_get_lat_lon(walk_path.points[0])[0], _get_lat_lon(walk_path.points[0])[1], walk_path.lastlat, walk_path.lastlon)
        last_pt_dist = vincenty(_get_lat_lon(walk_path.points[-1])[0], _get_lat_lon(walk_path.points[-1])[1], walk_path.lastlat, walk_path.lastlon)
        
        # if the first point is closer to the last point on the previous walk path, reverse the order of the points
        if (first_pt_dist > last_pt_dist):
            walk_path.points.reverse()
        
        # determine current walk path's bearing
        walk_path.bearing = _path_bearing(walk_path.points)
        
        # if this is the first edge in the route
        if (route_info.first_edge):
            lat, lon = _get_lat_lon(walk_path.points[0])
            ret_string += _print_orig_path(route_info, lat, lon)
            route_info.first_edge = False
        
        # build return string
        ret_string += '<street name="' + walk_path.name + '" length="' + str(int(round(walk_path.length))) + '" bearing="' + str(int(round(walk_path.bearing))) + '" dep_time="' + walk_path.dep_time + '" arr_time="' + walk_path.arr_time + '">'
        ret_string += '<points>'
        
        for point in walk_path.points:
            ret_string += '<point lat="' + point[point.index(' ')+1:] + '" lon="' + point[0:point.index(' ')] + '" />'
        
        ret_string += '</points>'
        ret_string += '</street>'
        
        return ret_string
    
    def _get_lat_lon(point):
        return (float(point[point.index(' ')+1:]), float(point[0:point.index(' ')]))
    
    def board_event_xml(vertex1, edge, vertex2, walk_path, route_info):
        ret_string = ""
        
        if (len(walk_path.points) > 0):
            walk_path.arr_time = str(vertex1.payload.time)
            ret_string += _print_walk_path(walk_path, route_info)
            #ret_string += '</walk>'
            ret_string += '</' + route_info.street_mode + '>'
            walk_path.name = ""
            walk_path.points = []
    
        event_time = vertex2.payload.time
        trip_id = vertex2.payload.trip_id
        stop_id = vertex1.label.split("-")[-1]
        
        route_desc = list( pggtfsdb.execute( "SELECT routes.route_id, routes.route_long_name, routes.route_short_name, routes.route_type FROM routes, trips WHERE routes.route_id=trips.route_id AND trip_id='" + trip_id + "'") )
        stop_desc = list( pggtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id='" + stop_id + "'") )[0][0]
        lat, lon = list( pggtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id='" + stop_id + "'") )[0]
        stop_headsign = list( pggtfsdb.execute( "SELECT stop_headsign FROM stop_times WHERE trip_id='" + trip_id + "' AND stop_id='" + stop_id + "'") )[0][0]
        agency_id = list( pggtfsdb.execute( "SELECT agency_id FROM routes WHERE route_id='" + str(route_desc[0][0]) + "'") )[0][0]
        
        boardtime = str(event_time) #str(TimeHelpers.unix_to_localtime( event_time, "America/Chicago" ))
        
        boardtime_struct = time.localtime(event_time)
        start_of_day = time.mktime([boardtime_struct.tm_year, boardtime_struct.tm_mon, boardtime_struct.tm_mday, 0, 0, 0, boardtime_struct.tm_wday, boardtime_struct.tm_yday, -1])
        
        boardtime_offsets_list = []
        
        if (route_info.retro_route is True):
            vertex1_edge_list = vertex1.incoming
        else:
            vertex1_edge_list = vertex1.outgoing
        
        for curr_edge in vertex1_edge_list:
            for i in range(curr_edge.payload.num_boardings):
                alt_boardtime = (curr_edge.payload.get_boarding(i)[1] + start_of_day)
                if (alt_boardtime >= (event_time - 900) and alt_boardtime <= (event_time + 3600)):
                    boardtime_offsets_list.append(int(alt_boardtime - event_time))
        
        boardtime_offsets_list.sort()
        boardtime_offsets = ",".join(["%s" % bt for bt in boardtime_offsets_list])
        
        #stop_desc = stop_desc.replace("&","&amp;")
        stop_desc = stop_desc.replace("&","and")
        
        # if this is the first edge in the route
        if (route_info.first_edge):
            #ret_string += '<walk>'
            ret_string += '<' + route_info.street_mode + '>'
            ret_string += _print_orig_path(route_info, lat, lon)
            #ret_string += '</walk>'
            ret_string += '</' + route_info.street_mode + '>'
            route_info.first_edge = False
        
        route_id = str(route_desc[0][0])
        if ("PACE_" in route_id):
            route_id = str(route_desc[0][2])
        
        ret_string += '<transit agency_id="' + str(agency_id) + '" route_type="' + str(route_desc[0][3]) + '" route_id="' + str(route_id) + '" route_long_name="' + str(route_desc[0][1]) + '" trip_id="' + str(trip_id) + '" board_stop_id="' + str(stop_id) + '" board_stop="' + str(stop_desc) + '" board_stop_headsign="' + str(stop_headsign) + '" board_time="' + str(boardtime) + '" board_time_offsets="' + str(boardtime_offsets) + '" board_lat="' + str(lat) + '" board_lon="' + str(lon) + '"'
        
        return (ret_string, walk_path, route_info)
    
    def alight_event_xml(vertex1, edge, vertex2, walk_path, route_info):
        event_time = vertex1.payload.time
        stop_id = vertex2.label.split("-")[-1]
        
        stop_desc = list( pggtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id='" + stop_id + "'") )[0][0]
        lat, lon = list( pggtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id='" + stop_id + "'") )[0]
        
        walk_path.lastlat = lat
        walk_path.lastlon = lon
        
        alighttime = str(event_time) #str(TimeHelpers.unix_to_localtime( event_time, "America/Chicago" ))
        #stop_desc = stop_desc.replace("&","&amp;")
        stop_desc = stop_desc.replace("&","and")
        
        ret_string = ' alight_stop_id="' + str(stop_id) + '" alight_stop="' + str(stop_desc) + '" alight_time="' + str(alighttime) + '" alight_lat="' + str(lat) + '" alight_lon="' + str(lon) + '" />'
        
        # if this is the last edge in the route
        if (route_info.last_edge):
            #ret_string += '<walk>'
            ret_string += '<' + route_info.street_mode + '>'
            ret_string += _print_dest_path(route_info, lat, lon)
            #ret_string += '</walk>'
            ret_string += '</' + route_info.street_mode + '>'
        
        return (ret_string, walk_path, route_info)
    
    def headwayboard_event_xml(vertex1, edge, vertex2, walk_path, route_info):
        ret_string = ""
        
        if (len(walk_path.points) > 0):
            walk_path.arr_time = str(vertex1.payload.time)
            ret_string += _print_walk_path(walk_path, route_info)
            #ret_string += '</walk>'
            ret_string += '</' + route_info.street_mode + '>'
            walk_path.name = ""
            walk_path.points = []
            
        event_time = vertex2.payload.time
        trip_id = vertex2.payload.trip_id
        stop_id = vertex1.label.split("-")[-1]
        
        route_desc = list( pggtfsdb.execute( "SELECT routes.route_id, routes.route_long_name, routes.route_type FROM routes, trips WHERE routes.route_id=trips.route_id AND trip_id='" + trip_id + "'") )
        stop_desc = list( pggtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id='" + stop_id + "'") )[0][0]
        lat, lon = list( pggtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id='" + stop_id + "'") )[0]
        stop_headsign = list( pggtfsdb.execute( "SELECT stop_headsign FROM stop_times WHERE trip_id='" + trip_id + "' AND stop_id='" + stop_id + "'") )[0][0]
        agency_id = list( pggtfsdb.execute( "SELECT agency_id FROM routes WHERE route_id='" + str(route_desc[0][0]) + "'") )[0][0]
        
        boardtime = str(event_time) #str(TimeHelpers.unix_to_localtime( event_time, "America/Chicago" ))
        
        boardtime_struct = time.localtime(event_time)
        start_of_day = time.mktime([boardtime_struct.tm_year, boardtime_struct.tm_mon, boardtime_struct.tm_mday, 0, 0, 0, boardtime_struct.tm_wday, boardtime_struct.tm_yday, -1])
        
        boardtime_offsets_list = []
        
        if (route_info.retro_route is True):
            vertex1_edge_list = vertex1.incoming
        else:
            vertex1_edge_list = vertex1.outgoing
        
        for curr_edge in vertex1_edge_list:
            for i in range(curr_edge.payload.num_boardings):
                alt_boardtime = (curr_edge.payload.get_boarding(i)[1] + start_of_day)
                if (alt_boardtime >= (event_time - 900) and alt_boardtime <= (event_time + 3600)):
                    boardtime_offsets_list.append(int(alt_boardtime - event_time))
        
        boardtime_offsets_list.sort()
        boardtime_offsets = ",".join(["%s" % bt for bt in boardtime_offsets_list])
        
        #stop_desc = stop_desc.replace("&","&amp;")
        stop_desc = stop_desc.replace("&","and")
        
        # if this is the first edge in the route
        if (route_info.first_edge):
            #ret_string += '<walk>'
            ret_string += '<' + route_info.street_mode + '>'
            ret_string += _print_orig_path(route_info, lat, lon)
            #ret_string += '</walk>'
            ret_string += '</' + route_info.street_mode + '>'
            route_info.first_edge = False
        
        ret_string += '<transit agency_id="' + str(agency_id) + '" route_type="' + str(route_desc[0][2]) + '" route_id="' + str(route_desc[0][0]) + '" route_long_name="' + str(route_desc[0][1]) + '" trip_id="' + str(trip_id) + '" board_stop_id="' + str(stop_id) + '" board_stop="' + str(stop_desc) + '" board_stop_headsign="' + str(stop_headsign) + '" board_time="' + str(boardtime) + '" board_time_offsets="' + str(boardtime_offsets) + '" board_lat="' + str(lat) + '" board_lon="' + str(lon) + '"'
        
        return (ret_string, walk_path, route_info)
    
    def headwayalight_event_xml(vertex1, edge, vertex2, walk_path, route_info):
        event_time = vertex1.payload.time
        stop_id = vertex2.label.split("-")[-1]
        
        stop_desc = list( pggtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id='" + stop_id + "'") )[0][0]
        lat, lon = list( pggtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id='" + stop_id + "'") )[0]
        
        walk_path.lastlat = lat
        walk_path.lastlon = lon
        
        alighttime = str(event_time) #str(TimeHelpers.unix_to_localtime( event_time, "America/Chicago" ))
        #stop_desc = stop_desc.replace("&","&amp;")
        stop_desc = stop_desc.replace("&","and")
        
        ret_string = ' alight_stop_id="' + str(stop_id) + '" alight_stop="' + str(stop_desc) + '" alight_time="' + str(alighttime) + '" alight_lat="' + str(lat) + '" alight_lon="' + str(lon) + '" />'
        
        # if this is the last edge in the route
        if (route_info.last_edge):
            #ret_string += '<walk>'
            ret_string += '<' + route_info.street_mode + '>'
            ret_string += _print_dest_path(route_info, lat, lon)
            #ret_string += '</walk>'
            ret_string += '</' + route_info.street_mode + '>'
        
        return (ret_string, walk_path, route_info)
    
    def _insert_or_append(path_str_list, full_path):
        if (len(full_path) == 0):
            for point in path_str_list:
                full_path.append(point)
        
        elif (path_str_list[0] == full_path[0]):
            path_str_list.remove(path_str_list[0])
            for point in path_str_list:
                full_path.insert(0, point)
        
        elif (path_str_list[0] == full_path[-1]):
            path_str_list.remove(path_str_list[0])
            for point in path_str_list:
                full_path.append(point)
        
        elif (path_str_list[-1] == full_path[0]):
            path_str_list.remove(path_str_list[-1])
            path_str_list.reverse()
            for point in path_str_list:
                full_path.insert(0, point)
        
        elif (path_str_list[-1] == full_path[-1]):
            path_str_list.remove(path_str_list[-1])
            path_str_list.reverse()
            for point in path_str_list:
                full_path.append(point)
        
    
    def street_event_xml(vertex1, edge, vertex2, walk_path, route_info):
        # initialize return string to empty
        ret_string = ""
        
        # get street name and path geometry from edge
        (street_name, path_str) = pgosmdb.get_street_name_and_path_geometry_from_edge(edge.payload.name)
        
        if (walk_path.name == ""):
            walk_path.name = street_name
            walk_path.dep_time = str(vertex1.payload.time)
            walk_path.points = []
            walk_path.length = 0.0
            walk_path.direction = ""
            #ret_string += '<walk>'
            ret_string += '<' + route_info.street_mode + '>'
        
        elif (walk_path.name != street_name):
            walk_path.arr_time = str(vertex1.payload.time)
            ret_string += _print_walk_path(walk_path, route_info)
            
            (walk_path.lastlat, walk_path.lastlon) = _get_lat_lon(walk_path.points[-1])
            walk_path.name = street_name
            walk_path.dep_time = str(vertex1.payload.time)
            walk_path.points = []
            walk_path.length = 0.0
        
        # add length of edge to walk path length
        walk_path.length += edge.payload.length
        
        # add length of edge to total walk distance
        walk_path.total_distance += edge.payload.length

        # clean up path string
        path_str = path_str.replace('LINESTRING(','').replace(')','')
        
        # create list out of path string
        path_str_list = path_str.split(',')
        
        # insert or append current walk path
        _insert_or_append(path_str_list, walk_path.points)
        
        # if this is the last edge in the route
        if (route_info.last_edge):
            walk_path.arr_time = str(vertex2.payload.time)
            ret_string += _print_walk_path(walk_path, route_info)
            
            lat, lon = _get_lat_lon(walk_path.points[-1])
            ret_string += _print_dest_path(route_info, lat, lon)
            #ret_string += '</walk>'
            ret_string += '</' + route_info.street_mode + '>'
        
        return (ret_string, walk_path, route_info)
        
        
    event_dispatch = {graphserver.core.TripBoard:board_event_xml,
                      graphserver.core.Alight:alight_event_xml,
                      graphserver.core.Street:street_event_xml,
                      graphserver.core.HeadwayBoard:headwayboard_event_xml,
                      graphserver.core.HeadwayAlight:headwayalight_event_xml}
    
    gc = RouteServer(graphdb_filename, pgosmdb, pggtfsdb, event_dispatch)
    gc.run_test_server(port_number)
