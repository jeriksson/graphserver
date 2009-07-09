from servable import Servable
from graphserver.graphdb import GraphDatabase
import cgi
from graphserver.core import State, WalkOptions
import time
import sys
import graphserver
from graphserver.util import TimeHelpers
from graphserver.ext.gtfs.gtfsdb import GTFSDatabase
from graphserver.ext.osm.pggis_osmdb import PostgresGIS_OSMDB
import json

class RouteServer(Servable):
    def __init__(self, graphdb_filename, event_dispatch):
        graphdb = GraphDatabase( graphdb_filename )
        self.graph = graphdb.incarnate()
        self.event_dispatch = event_dispatch
    
    def vertices(self):
        return "\n".join( [vv.label for vv in self.graph.vertices] )
    vertices.mime = "text/plain"

    def path(self, origin, dest, currtime, transfer_penalty=0, walking_speed=1.0):
        
        wo = WalkOptions()
        wo.transfer_penalty=transfer_penalty
        wo.walking_speed=walking_speed
        spt = self.graph.shortest_path_tree( origin, dest, State(1,currtime), wo )
        wo.destroy()
        
        vertices, edges = spt.path( dest )
        
        ret = []
        for i in range(len(edges)):
            edgetype = edges[i].payload.__class__
            if edgetype in self.event_dispatch:
                ret.append( self.event_dispatch[ edges[i].payload.__class__ ]( vertices[i], edges[i], vertices[i+1] ) )
        
        spt.destroy()
        
        return json.dumps(ret)
    
    def path_retro(self, origin, dest, currtime, transfer_penalty=0, walking_speed=1.0):
        
        wo = WalkOptions()
        wo.transfer_penalty = transfer_penalty
        wo.walking_speed = walking_speed
        spt = self.graph.shortest_path_tree_retro( origin, dest, State(1,currtime), wo )
        wo.destroy()
        
        vertices, edges = spt.path_retro( origin )
        
        ret = []
        for i in range(len(edges)):
            edgetype = edges[i].payload.__class__
            if edgetype in self.event_dispatch:
                ret.append( self.event_dispatch[ edges[i].payload.__class__ ]( vertices[i], edges[i], vertices[i+1] ) )
        
        spt.destroy()
        
        return json.dumps(ret)

    def path_xml(self, origin, dest, currtime, transfer_penalty=0, walking_speed=1.0):
        
        wo = WalkOptions()
        wo.transfer_penalty=transfer_penalty
        wo.walking_speed=walking_speed
        spt = self.graph.shortest_path_tree( origin, dest, State(1,currtime), wo )
        wo.destroy()
        
        vertices, edges = spt.path( dest )
        
        ret = '<?xml version="1.0"?><routes><route>'
        for i in range(len(edges)):
            edgetype = edges[i].payload.__class__
            if edgetype in self.event_dispatch:
                ret += self.event_dispatch[ edges[i].payload.__class__ ]( vertices[i], edges[i], vertices[i+1] )
        
        ret += '</route></routes>'
        
        spt.destroy()
        
        return str(ret)
        
    path_xml.mime = "text/xml"

    def path_xml_coords(self, origlon, origlat, destlon, destlat, currtime=int(time.time()), transfer_penalty=0, walking_speed=1.0):
        
        pgdb = PostgresGIS_OSMDB ("dbname='chicago_osm'")
        
        origin = get_osm_vertex_from_coords(origlon, origlat, "4326", "location")
        dest = get_osm_vertex_from_coords(destlon, destlat, "4326", "location")
        
        #conn = psycopg2.connect("dbname='chicago_osm' user='james' host='bits.cs.uic.edu' password='graphserv01'")
        #conn = psycopg2.connect("dbname='chicago_osm'")
        #cur = conn.cursor()
        
        #origpoint = "'POINT(" + str(origlon) + ' ' + str(origlat) + ")'"
        #destpoint = "'POINT(" + str(destlon) + ' ' + str(destlat) + ")'"
        
        #origquery = 'select id,distance_sphere(SetSRID(GeomFromText(' + origpoint + '),4326),location) as dist from nodes order by dist asc limit 1'
        #destquery = 'select id,distance_sphere(SetSRID(GeomFromText(' + destpoint + '),4326),location) as dist from nodes order by dist asc limit 1'
        
        #cur.execute(origquery)
        #row = cur.fetchone()
        #conn.commit()

        #origin = 'osm-' + row[0]
        
        #cur.execute(destquery)
        #row = cur.fetchone()
        
        #dest = 'osm-' + row[0]
        
        wo = WalkOptions()
        wo.transfer_penalty=transfer_penalty
        wo.walking_speed=walking_speed
        spt = self.graph.shortest_path_tree( origin, dest, State(1,currtime), wo )

        wo.destroy()

        vertices, edges = spt.path( dest )
        
        if (edges is None):
            return '<?xml version="1.0"?><routes></routes>'
        
        ret = '<?xml version="1.0"?><routes><route>'
        for i in range(len(edges)):
            edgetype = edges[i].payload.__class__
            if edgetype in self.event_dispatch:
                ret += self.event_dispatch[ edges[i].payload.__class__ ]( vertices[i], edges[i], vertices[i+1] )
        
        ret += '</route></routes>'
        
        spt.destroy()
        
        return str(ret)
        
    path_xml_coords.mime = "text/xml"

    def path_xml_coords_walk(self, origlon, origlat, destlon, destlat, currtime=int(time.time()), transfer_penalty=0, walking_speed=1.0):
        
        #conn = psycopg2.connect("dbname='chicago_osm'")
        #cur = conn.cursor()
        
        #origpoint = "'POINT(" + str(origlon) + ' ' + str(origlat) + ")'"
        #destpoint = "'POINT(" + str(destlon) + ' ' + str(destlat) + ")'"
        
        #origquery = 'select id,distance_sphere(SetSRID(GeomFromText(' + origpoint + '),4326),location) as dist from nodes order by dist asc limit 1'
        #destquery = 'select id,distance_sphere(SetSRID(GeomFromText(' + destpoint + '),4326),location) as dist from nodes order by dist asc limit 1'
        
        #cur.execute(origquery)
        #row = cur.fetchone()
        #conn.commit()

        #origin = 'osm-' + row[0]
        
        #cur.execute(destquery)
        #row = cur.fetchone()
        
        #dest = 'osm-' + row[0]
        
        pgdb = PostgresGIS_OSMDB ("dbname='chicago_osm'")
        
        origin = pgdb.get_osm_vertex_from_coords(origlon, origlat, "4326", "location")
        dest = pgdb.get_osm_vertex_from_coords(destlon, destlat, "4326", "location")
        
        
        wo = WalkOptions()
        wo.transfer_penalty=transfer_penalty
        wo.walking_speed=walking_speed
        spt = self.graph.shortest_path_tree( origin, dest, State(1,currtime), wo )

        wo.destroy()

        vertices, edges = spt.path( dest )
        
        if (edges is None):
            return '<?xml version="1.0"?><routes></routes>'
        
        ret = '<?xml version="1.0"?><routes><route>'
        
        walk_path_name = ""
        walk_path_pts = []
        walk_path_length = 0.0
        last_edge = False
        edges_len = len(edges)
        
        for i in range(edges_len): #range(len(edges)):
            if (i == (edges_len-1)):
                last_edge = True
        	    
            edgetype = edges[i].payload.__class__
            if edgetype in self.event_dispatch:
                (new_event, walk_path_name, walk_path_pts, walk_path_length) = self.event_dispatch[ edges[i].payload.__class__ ]( vertices[i], edges[i], vertices[i+1], walk_path_name, walk_path_pts, walk_path_length, last_edge)
                ret += new_event
        
        ret += '</route></routes>'
        
        spt.destroy()
        
        return str(ret)
        
    path_xml_coords_walk.mime = "text/xml"

    def path_raw(self, origin, dest, currtime):
        
        wo = WalkOptions()
        spt = self.graph.shortest_path_tree( origin, dest, State(1,currtime), wo )
        wo.destroy()
        
        vertices, edges = spt.path( dest )
        
        ret = "\n".join([str(x) for x in vertices]) + "\n\n" + "\n".join([str(x) for x in edges])

        spt.destroy()
        
        return ret
        
    def path_raw_retro(self, origin, dest, currtime):
        
        wo = WalkOptions()
        spt = self.graph.shortest_path_tree_retro( origin, dest, State(1,currtime), wo )
        wo.destroy()
        
        vertices, edges = spt.path_retro( origin )
        
        ret = "\n".join([str(x) for x in vertices]) + "\n\n" + "\n".join([str(x) for x in edges])

        spt.destroy()
        
        return ret
            
import sys
if __name__ == '__main__':
    usage = "python routeserver.py graphdb_filename gtfsdb_filename"
    
    if len(sys.argv) < 2:
        print usage
        exit()
        
    graphdb_filename = sys.argv[1]
    gtfsdb_filename = sys.argv[2]
    
    gtfsdb = GTFSDatabase( gtfsdb_filename )

    def _print_path_pts(walk_path_pts):
        ret_string = ""
        
        for point in walk_path_pts:
            ret_string += '<point lat="' + point[0:point.index(',')] + '" lon="' + point[point.index(',')+1:] + '" />'
        
        return ret_string

    def board_event(vertex1, edge, vertex2, walk_path_name, walk_path_pts, walk_path_length, last_edge):
        ret_string = ""
        
        if (len(walk_path_pts) > 0):
            ret_string += '<street name="' + walk_path_name + '" length="' + str(walk_path_length) + '">'
            ret_string += '<points>' + _print_path_pts(walk_path_pts) + '</points>'
            ret_string += '</street>'
            ret_string += '</walk>'
            walk_path_name = ""
            walk_path_pts = []
            walk_path_length = 0.0
    
        event_time = vertex2.payload.time
        trip_id = vertex2.payload.trip_id
        stop_id = vertex1.label.split("-")[-1]
        
        route_desc = list( gtfsdb.execute( "SELECT routes.route_short_name, routes.route_long_name FROM routes, trips WHERE routes.route_id=trips.route_id AND trip_id=?", (trip_id,) ) )
        stop_desc = list( gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
        lat, lon = list( gtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id = ?", (stop_id,) ) )[0]
        
        # determine mode based off of stop id
        if (int(stop_id) < 30000):
            mode = 3
        else:
            mode = 1
        
        #what = "Board the %s"%route_desc
        #where = stop_desc
        #when = str(TimeHelpers.unix_to_localtime( event_time, "America/Chicago" ))
        #loc = (lat,lon)
        #return (what, where, when, loc)
        
        boardtime = str(TimeHelpers.unix_to_localtime( event_time, "America/Chicago" ))
        stop_desc = stop_desc.replace("&","&amp;")
        
        #return '<board route_short_name="' + route_desc[0][0] + '" route_long_name="' + route_desc[0][1] + '" stop="' + stop_desc + '" time="' + boardtime + '" lat="' + str(lat) + '" lon="' + str(lon) + '" />'
        #return '<transit route_short_name="' + route_desc[0][0] + '" route_long_name="' + route_desc[0][1] + '" board_stop="' + stop_desc + '" board_time="' + boardtime + '" board_lat="' + str(lat) + '" board_lon="' + str(lon) + '"'
        
        ret_string += '<transit mode="' + str(mode) + '" route_short_name="' + route_desc[0][0] + '" route_long_name="' + route_desc[0][1] + '" board_stop="' + stop_desc + '" board_time="' + boardtime + '" board_lat="' + str(lat) + '" board_lon="' + str(lon) + '"'
        
        return (ret_string, walk_path_name, walk_path_pts, walk_path_length)

    def alight_event(vertex1, edge, vertex2, walk_path_name, walk_path_pts, walk_path_length, last_edge):
        event_time = vertex1.payload.time
        stop_id = vertex2.label.split("-")[-1]
        
        stop_desc = list( gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
        lat, lon = list( gtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id = ?", (stop_id,) ) )[0]
        
        #what = "Alight"
        #where = stop_desc
        #when = str(TimeHelpers.unix_to_localtime( event_time, "America/Chicago" ))
        #loc = (lat,lon)
        #return (what, where, when, loc)
        
        alighttime = str(TimeHelpers.unix_to_localtime( event_time, "America/Chicago" ))
        stop_desc = stop_desc.replace("&","&amp;")
        
        #return '<alight stop="' + stop_desc + '" time="' + alighttime + '" lat="' + str(lat) + '" lon="' + str(lon) + '" />'
        return (' alight_stop="' + stop_desc + '" alight_time="' + alighttime + '" alight_lat="' + str(lat) + '" alight_lon="' + str(lon) + '" />', "", [], 0.0)
        
    def headwayboard_event(vertex1, edge, vertex2, walk_path_name, walk_path_pts, walk_path_length, last_edge):
        ret_string = ""
        
        if (len(walk_path_pts) > 0):
            ret_string += '<street name="' + walk_path_name + '" length="' + str(walk_path_length) + '">'
            ret_string += '<points>' + _print_path_pts(walk_path_pts) + '</points>'
            ret_string += '</street>'
            ret_string += '</walk>'
            walk_path_name = ""
            walk_path_pts = []
            walk_path_length = 0.0
            
        event_time = vertex2.payload.time
        trip_id = vertex2.payload.trip_id
        stop_id = vertex1.label.split("-")[-1]
        
        route_desc = list( gtfsdb.execute( "SELECT routes.route_short_name, routes.route_long_name FROM routes, trips WHERE routes.route_id=trips.route_id AND trip_id=?", (trip_id,) ) )
        stop_desc = list( gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
        lat, lon = list( gtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id = ?", (stop_id,) ) )[0]
        
        #what = "Board the %s"%route_desc
        #where = stop_desc
        #when = "about %s"%str(TimeHelpers.unix_to_localtime( event_time, "America/Chicago" ))
        #loc = (lat,lon)
        #return (what, where, when, loc)
        
        boardtime = str(TimeHelpers.unix_to_localtime( event_time, "America/Chicago" ))
        stop_desc = stop_desc.replace("&","&amp;")
        
        #return '<headway_board route_short_name="' + route_desc[0][0] + '" route_long_name="' + route_desc[0][1] + '" stop="' + stop_desc + '" time="' + boardtime + '" lat="' + str(lat) + '" lon="' + str(lon) + '" />'
        #return '<transit route_short_name="' + route_desc[0][0] + '" route_long_name="' + route_desc[0][1] + '" hw_board_stop="' + stop_desc + '" hw_board_time="' + boardtime + '" hw_board_lat="' + str(lat) + '" hw_board_lon="' + str(lon) + '"'

        ret_string += '<transit route_short_name="' + route_desc[0][0] + '" route_long_name="' + route_desc[0][1] + '" hw_board_stop="' + stop_desc + '" hw_board_time="' + boardtime + '" hw_board_lat="' + str(lat) + '" hw_board_lon="' + str(lon) + '"'
        
        return (ret_string, walk_path_name, walk_path_pts, walk_path_length)

    def headwayalight_event(vertex1, edge, vertex2, walk_path_name, walk_path_pts, walk_path_length, last_edge):
        event_time = vertex1.payload.time
        stop_id = vertex2.label.split("-")[-1]
        
        stop_desc = list( gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
        lat, lon = list( gtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id = ?", (stop_id,) ) )[0]
        
        #what = "Alight"
        #where = stop_desc
        #when = "about %s"%str(TimeHelpers.unix_to_localtime( event_time, "America/Chicago" ))
        #loc = (lat,lon)
        #return (what, where, when, loc)
        
        alighttime = str(TimeHelpers.unix_to_localtime( event_time, "America/Chicago" ))
        stop_desc = stop_desc.replace("&","&amp;")
        
        #return '<headway_alight stop="' + stop_desc + '" time="' + alighttime + '" lat="' + str(lat) + '" lon="' + str(lon) + '" />'
        return (' hw_alight_stop="' + stop_desc + '" hw_alight_time="' + alighttime + '" hw_alight_lat="' + str(lat) + '" hw_alight_lon="' + str(lon) + '" />', "", [], 0.0)
        
    def street_event(vertex1, edge, vertex2, walk_path_name, walk_path_pts, walk_path_length, last_edge):
        #return ("Walk", edge.payload.name, "", None)
        #return ("Walk", "", "", None)
        
        #osmdb = psycopg2.connect("dbname='chicago_osm'")
        #osmdb_cursor = osmdb.cursor()
        #osmdb_cursor.execute("select tags, AsText(path) from ways where id='" + edge.payload.name + "'")
        #osmdb_fetch = osmdb_cursor.fetchone()
        #osmdb.commit()
        
        #street_dict = eval(osmdb_fetch[0])
        #if 'name' in street_dict:
        #    street_name = street_dict['name'].replace("&","&amp;")
        #else:
        #    street_name = "Unknown"
        #
        #path_str = str(osmdb_fetch[1])
        
        pgdb = PostgresGIS_OSMDB ("dbname='chicago_osm'")
        (street_name, path_str) = pgdb.get_street_name_and_path_geometry_from_edge(edge.payload.name)
        
        street_length = str(edge.payload.length)
        
        ret_string = ""
        
        #if (prev_street == street_name):
        #    return '<segment length="' + street_length + '" geom="' + geom_str + '" />'
        #else:
        #    prev_street = street_name
        #    ret_string = '<walk street="' + street_name + '">'
        #    ret_string += '<segment length="' + street_length + '" geom="' + geom_str + '" />'
        #    return ret_string
        
        #ret_string = '<walk street="' + street_name + '"/>'
        #ret_string += '<segment length="' + street_length + '" geom="' + geom_str + '" />'
        #return ret_string
        
        if (walk_path_name == ""):
            walk_path_name = street_name
            walk_path_pts = []
            walk_path_length = 0.0
            ret_string += '<walk>'
        elif (walk_path_name != street_name):
            ret_string += '<street name="' + walk_path_name + '" length="' + str(walk_path_length) + '">'
            ret_string += '<points>' + _print_path_pts(walk_path_pts) + '</points>'
            ret_string += '</street>'
            walk_path_name = street_name
            walk_path_pts = []
            walk_path_length = 0.0
            
        walk_path_length += float(street_length)
        
        #ret_string += '<walk street="' + street_name + '" length="' + street_length + '" path="' + path_str + '" />'
        
        #from_pt = osmdb_fetch[1][osmdb_fetch[1].index('(')+1:osmdb_fetch[1].index(',')]
        #from_pt_lon = from_pt[0:from_pt.index(' ')]
        #from_pt_lat = from_pt[from_pt.index(' ')+1:]
        
        #to_pt = osmdb_fetch[1][osmdb_fetch[1].rindex(',')+1:osmdb_fetch[1].index(')')]
        #to_pt_lon = to_pt[0:to_pt.index(' ')]
        #to_pt_lat = to_pt[to_pt.index(' ')+1:]
        
        path_done = False
        mod_path = path_str.replace('LINESTRING(','').replace(')','')
        
        while path_done == False:
            if (mod_path.find(',') == -1):
                next_loc_lon = mod_path[0:mod_path.find(' ')]
                next_loc_lat = mod_path[mod_path.find(' ')+1:]
                path_done = True
            else:
                next_loc = mod_path[0:mod_path.find(',')]
                next_loc_lon = next_loc[0:next_loc.find(' ')]
                next_loc_lat = next_loc[next_loc.find(' ')+1:]
                mod_path = mod_path.replace(next_loc + ',','')
            
            if ((next_loc_lat + ',' + next_loc_lon) not in walk_path_pts):
                walk_path_pts.append(next_loc_lat + ',' + next_loc_lon)
                
            #ret_string += '<point lat="' + next_loc_lat + '" lon="' + next_loc_lon + '" />'

        #ret_string += '<points>' + str(walk_path_pts) + '</points>'

        #ret_string += '<segment from_lat="' + from_pt_lat + '" from_lon="' + from_pt_lon + '" to_lat="' + to_pt_lat + '" to_lon="' + to_pt_lon + '" />'
        
        if (last_edge):
            ret_string += '</walk>'
        
        return (ret_string, walk_path_name, walk_path_pts, walk_path_length)
        
    event_dispatch = {graphserver.core.TripBoard:board_event,
                      graphserver.core.Alight:alight_event,
                      graphserver.core.Street:street_event,
                      graphserver.core.HeadwayBoard:headwayboard_event,
                      graphserver.core.HeadwayAlight:headwayalight_event}
    
    gc = RouteServer(graphdb_filename, event_dispatch)
    gc.run_test_server(8081)
