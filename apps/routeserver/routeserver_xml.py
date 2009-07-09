#
# Modified routeserver to output XML-formatted route results.
# Author: James P. Biagioni (jbiagi1@uic.edu)
# Company: University of Illinois at Chicago
# Last modified: 6/8/09
#

from servable import Servable
from graphserver.graphdb import GraphDatabase
import cgi
from graphserver.core import State, WalkOptions
import time
import sys
import graphserver
from graphserver.util import TimeHelpers
from graphserver.ext.gtfs.gtfsdb import GTFSDatabase
from graphserver.ext.osm.pgosmdb import PostgresGIS_OSMDB
from graphserver.ext.gtfs.pggtfsdb import PostgresGIS_GTFSDB
from math import fmod, sin, cos, atan2, pi, degrees
from graphserver.ext.osm.vincenty import vincenty
import json

class WalkPath:
    def __init__(self):
        self.name = ""
        self.points = []
        self.length = 0.0
        self.lastlat = 0.0
        self.lastlon = 0.0

class RouteServer(Servable):
    def __init__(self, graphdb_filename, pgosmdb_handle, pggtfsdb_handle, event_dispatch):
        graphdb = GraphDatabase( graphdb_filename )
        self.graph = graphdb.incarnate()
        self.event_dispatch = event_dispatch
        self.pgosmdb = pgosmdb_handle
        self.pggtfsdb = pggtfsdb_handle
    
    def transit_path(self, trip_id, board_stop_id, alight_stop_id):
        ret_string = '<transit trip_id="' + str(trip_id) + '" board_stop_id="' + str(board_stop_id) + '" alight_stop_id="' + str(alight_stop_id) + '">'
        ret_string += '<points>'
        
        for point in self.pggtfsdb.get_transit_path_points(trip_id, board_stop_id, alight_stop_id):
            ret_string += '<point lat="' + point[0:point.index(',')] + '" lon="' + point[point.index(',')+1:] + '" />'
        
        ret_string += '</points>'
        ret_string += '</transit>'
        
        return ret_string
    transit_path.mime = "text/xml"
    
    def path_xml(self, origlon, origlat, destlon, destlat, currtime=0, transfer_penalty=0, walking_speed=1.0):
        
        # if the current time is not specified, set it
        if (currtime == 0):
            currtime = int(time.time())
        
        origin = self.pgosmdb.get_osm_vertex_from_coords(origlon, origlat)
        dest = self.pgosmdb.get_osm_vertex_from_coords(destlon, destlat)
                
        wo = WalkOptions()
        wo.transfer_penalty=transfer_penalty
        wo.walking_speed=walking_speed
        spt = self.graph.shortest_path_tree( origin, dest, State(1,currtime), wo )

        wo.destroy()

        vertices, edges = spt.path( dest )
        
        # if there are no edges (i.e., there is no path found)
        if (edges is None):
            return '<?xml version="1.0"?><routes></routes>'
        
        ret_string = '<?xml version="1.0"?><routes><route currtime="' + str(currtime) + '">'
        
        # create WalkPath object
        walk_path = WalkPath()
        walk_path.lastlat = origlat
        walk_path.lastlon = origlon
        
        # determine the number of edges
        edges_len = len(edges)
        
        for i in range(edges_len):
            
            if (i == (edges_len-1)):
                last_edge = True
            else:
                last_edge = False
        	
            edgetype = edges[i].payload.__class__
            if edgetype in self.event_dispatch:
                (new_event, walk_path) = self.event_dispatch[ edges[i].payload.__class__ ]( vertices[i], edges[i], vertices[i+1], walk_path, last_edge)
                ret_string += new_event
        
        ret_string += '</route></routes>'
        
        spt.destroy()
        
        return str(ret_string)
    path_xml.mime = "text/xml"


import sys
if __name__ == '__main__':
    usage = "python routeserver_xml.py graphdb_filename gtfsdb_filename pgosmdb_connect_string pggtfsdb_connect_string"
    
    if len(sys.argv) < 5:
        print usage
        exit()
        
    graphdb_filename = sys.argv[1]
    gtfsdb_filename = sys.argv[2]
    pgosmdb_connect_string = sys.argv[3]
    pggtfsdb_connect_string = sys.argv[4]
    
    gtfsdb = GTFSDatabase( gtfsdb_filename )
    pgosmdb = PostgresGIS_OSMDB( pgosmdb_connect_string )
    pggtfsdb = PostgresGIS_GTFSDB( pggtfsdb_connect_string )

    def _path_bearing(path_points):
    
        # get start and end points along path
        point1 = path_points[0]
        point2 = path_points[1]
        
        # get latitude and longitude components
        lat1 = float(point1[point1.index(' ')+1:])
        lon1 = float(point1[0:point1.index(' ')])
        lat2 = float(point2[point2.index(' ')+1:])
        lon2 = float(point2[0:point2.index(' ')])
        
        # calculate bearing
        bearing = fmod(degrees(atan2(cos(lat1)*sin(lat2)-sin(lat1)*cos(lat2)*cos(lon2-lon1), sin(lon2-lon1)*cos(lat2))) + 270.0, 360.0)
        
        # return bearing
        return bearing
    
    def _print_path_points(path_points):
        ret_string = ""

        ret_string += '<points>'
        
        for point in path_points:
            ret_string += '<point lat="' + point[point.index(' ')+1:] + '" lon="' + point[0:point.index(' ')] + '" />'
        
        ret_string += '</points>'

        return ret_string
    
    def _get_lat_lon(point):
        return (float(point[point.index(' ')+1:]), float(point[0:point.index(' ')]))
    
    def board_event_xml(vertex1, edge, vertex2, walk_path, last_edge):
        ret_string = ""
        
        if (len(walk_path.points) > 0):
            first_pt_dist = vincenty(_get_lat_lon(walk_path.points[0])[0], _get_lat_lon(walk_path.points[0])[1], walk_path.lastlat, walk_path.lastlon)
            last_pt_dist = vincenty(_get_lat_lon(walk_path.points[-1])[0], _get_lat_lon(walk_path.points[-1])[1], walk_path.lastlat, walk_path.lastlon)
            
            if (first_pt_dist > last_pt_dist):
                walk_path.points.reverse()
            
            ret_string += '<street name="' + walk_path.name + '" length="' + str(int(round(walk_path.length))) + '" bearing="' + str(int(round(_path_bearing(walk_path.points)))) + '">'
            ret_string += _print_path_points(walk_path.points)
            ret_string += '</street>'
            ret_string += '</walk>'
            walk_path.name = ""
            walk_path.points = []
            walk_path.length = 0.0
    
        event_time = vertex2.payload.time
        trip_id = vertex2.payload.trip_id
        stop_id = vertex1.label.split("-")[-1]
        
        route_desc = list( gtfsdb.execute( "SELECT routes.route_id, routes.route_long_name, routes.route_type FROM routes, trips WHERE routes.route_id=trips.route_id AND trip_id=?", (trip_id,) ) )
        stop_desc = list( gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
        lat, lon = list( gtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id = ?", (stop_id,) ) )[0]
        
        boardtime = str(TimeHelpers.unix_to_localtime( event_time, "America/Chicago" ))
        #stop_desc = stop_desc.replace("&","&amp;")
        stop_desc = stop_desc.replace("&","and")
        
        ret_string += '<transit mode="' + route_desc[0][2] + '" route_id="' + route_desc[0][0] + '" route_long_name="' + route_desc[0][1] + '" trip_id="' + str(trip_id) + '" board_stop_id="' + str(stop_id) + '" board_stop="' + stop_desc + '" board_time="' + boardtime + '" board_lat="' + str(lat) + '" board_lon="' + str(lon) + '"'
        
        return (ret_string, walk_path)
    
    def alight_event_xml(vertex1, edge, vertex2, walk_path, last_edge):
        event_time = vertex1.payload.time
        stop_id = vertex2.label.split("-")[-1]
        
        stop_desc = list( gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
        lat, lon = list( gtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id = ?", (stop_id,) ) )[0]
        
        walk_path.lastlat = lat
        walk_path.lastlon = lon
        
        alighttime = str(TimeHelpers.unix_to_localtime( event_time, "America/Chicago" ))
        #stop_desc = stop_desc.replace("&","&amp;")
        stop_desc = stop_desc.replace("&","and")
        
        ret_string = ' alight_stop_id="' + str(stop_id) + '" alight_stop="' + stop_desc + '" alight_time="' + alighttime + '" alight_lat="' + str(lat) + '" alight_lon="' + str(lon) + '" />'
        
        return (ret_string, walk_path)
    
    def headwayboard_event_xml(vertex1, edge, vertex2, walk_path, last_edge):
        ret_string = ""
        
        if (len(walk_path.points) > 0):
            first_pt_dist = vincenty(_get_lat_lon(walk_path.points[0])[0], _get_lat_lon(walk_path.points[0])[1], walk_path.lastlat, walk_path.lastlon)
            last_pt_dist = vincenty(_get_lat_lon(walk_path.points[-1])[0], _get_lat_lon(walk_path.points[-1])[1], walk_path.lastlat, walk_path.lastlon)
            
            if (first_pt_dist > last_pt_dist):
                walk_path.points.reverse()
            
            ret_string += '<street name="' + walk_path.name + '" length="' + str(int(round(walk_path.length))) + '" bearing="' + str(int(round(_path_bearing(walk_path.points)))) + '">'
            ret_string += _print_path_points(walk_path.points)
            ret_string += '</street>'
            ret_string += '</walk>'
            walk_path.name = ""
            walk_path.points = []
            walk_path.length = 0.0
            
        event_time = vertex2.payload.time
        trip_id = vertex2.payload.trip_id
        stop_id = vertex1.label.split("-")[-1]
        
        route_desc = list( gtfsdb.execute( "SELECT routes.route_id, routes.route_long_name, routes.route_type FROM routes, trips WHERE routes.route_id=trips.route_id AND trip_id=?", (trip_id,) ) )
        stop_desc = list( gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
        lat, lon = list( gtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id = ?", (stop_id,) ) )[0]
        
        boardtime = str(TimeHelpers.unix_to_localtime( event_time, "America/Chicago" ))
        #stop_desc = stop_desc.replace("&","&amp;")
        stop_desc = stop_desc.replace("&","and")
        
        ret_string += '<transit mode="' + route_desc[0][2] + '" route_id="' + route_desc[0][0] + '" route_long_name="' + route_desc[0][1] + '" hw_trip_id="' + str(trip_id) + '" hw_board_stop_id="' + str(stop_id) + '" hw_board_stop="' + stop_desc + '" hw_board_time="' + boardtime + '" hw_board_lat="' + str(lat) + '" hw_board_lon="' + str(lon) + '"'
        
        return (ret_string, walk_path)
    
    def headwayalight_event_xml(vertex1, edge, vertex2, walk_path, last_edge):
        event_time = vertex1.payload.time
        stop_id = vertex2.label.split("-")[-1]
        
        stop_desc = list( gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
        lat, lon = list( gtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id = ?", (stop_id,) ) )[0]
        
        walk_path.lastlat = lat
        walk_path.lastlon = lon
        
        alighttime = str(TimeHelpers.unix_to_localtime( event_time, "America/Chicago" ))
        #stop_desc = stop_desc.replace("&","&amp;")
        stop_desc = stop_desc.replace("&","and")
        
        ret_string = ' alight_stop_id="' + str(stop_id) + '" hw_alight_stop="' + stop_desc + '" hw_alight_time="' + alighttime + '" hw_alight_lat="' + str(lat) + '" hw_alight_lon="' + str(lon) + '" />'
        
        return (ret_string, walk_path)
    
    def _insert_or_append(path_str_list, full_path):
        if (len(full_path) == 0):
            for point in path_str_list:
                full_path.append(point)
        
        elif (path_str_list[0] == full_path[-1]):
            path_str_list.remove(path_str_list[0])
            for point in path_str_list:
                full_path.append(point)
        
        elif (path_str_list[-1] == full_path[0]):
            path_str_list.remove(path_str_list[-1])
            path_str_list.reverse()
            for point in path_str_list:
                full_path.insert(0, point)
    
    def street_event_xml(vertex1, edge, vertex2, walk_path, last_edge):
        # initialize return string to empty
        ret_string = ""
        
        # get street name and path geometry from edge
        (street_name, path_str) = pgosmdb.get_street_name_and_path_geometry_from_edge(edge.payload.name)
        
        if (walk_path.name == ""):
            walk_path.name = street_name
            walk_path.points = []
            walk_path.length = 0.0
            ret_string += '<walk>'
        
        elif (walk_path.name != street_name):
            first_pt_dist = vincenty(_get_lat_lon(walk_path.points[0])[0], _get_lat_lon(walk_path.points[0])[1], walk_path.lastlat, walk_path.lastlon)
            last_pt_dist = vincenty(_get_lat_lon(walk_path.points[-1])[0], _get_lat_lon(walk_path.points[-1])[1], walk_path.lastlat, walk_path.lastlon)
            
            if (first_pt_dist > last_pt_dist):
                walk_path.points.reverse()
            
            (walk_path.lastlat, walk_path.lastlon) = _get_lat_lon(walk_path.points[-1])
            
            ret_string += '<street name="' + walk_path.name + '" length="' + str(int(round(walk_path.length))) + '" bearing="' + str(int(round(_path_bearing(walk_path.points)))) + '">'
            ret_string += _print_path_points(walk_path.points)
            ret_string += '</street>'
            walk_path.name = street_name
            walk_path.points = []
            walk_path.length = 0.0
        
        # add length of edge to walk path length
        walk_path.length += edge.payload.length

        # clean up path string
        path_str = path_str.replace('LINESTRING(','').replace(')','')
        
        # create list out of path string
        path_str_list = path_str.split(',')
        
        # insert or append current walk path
        _insert_or_append(path_str_list, walk_path.points)
        
        # if this is the last edge in the route
        if (last_edge):
            first_pt_dist = vincenty(_get_lat_lon(walk_path.points[0])[0], _get_lat_lon(walk_path.points[0])[1], walk_path.lastlat, walk_path.lastlon)
            last_pt_dist = vincenty(_get_lat_lon(walk_path.points[-1])[0], _get_lat_lon(walk_path.points[-1])[1], walk_path.lastlat, walk_path.lastlon)
            
            if (first_pt_dist > last_pt_dist):
                walk_path.points.reverse()
            
            ret_string += '<street name="' + walk_path.name + '" length="' + str(int(round(walk_path.length))) + '" bearing="' + str(int(round(_path_bearing(walk_path.points)))) + '">'
            ret_string += _print_path_points(walk_path.points)
            ret_string += '</street>'
            ret_string += '</walk>'
        
        return (ret_string, walk_path)
        
        
    event_dispatch = {graphserver.core.TripBoard:board_event_xml,
                      graphserver.core.Alight:alight_event_xml,
                      graphserver.core.Street:street_event_xml,
                      graphserver.core.HeadwayBoard:headwayboard_event_xml,
                      graphserver.core.HeadwayAlight:headwayalight_event_xml}
    
    gc = RouteServer(graphdb_filename, pgosmdb, pggtfsdb, event_dispatch)
    gc.run_test_server(8081)
