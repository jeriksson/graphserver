#
# Class for handling interaction with GTFSDB stored in PostgreSQL with PostGIS extensions.
# Author: James P. Biagioni (jbiagi1@uic.edu)
# Company: University of Illinois at Chicago
# Last modified: 11/2/09
#

import psycopg2
import time
import sys

class PostgresGIS_GTFSDB:
    
    #
    # initializer method for connecting to PostgreSQL database
    #
    def __init__(self, db_connect_string):
        
        # store the connection string
        self.db_connect_string = db_connect_string
        
        # connect to database
        #self.conn = psycopg2.connect(db_connect_string)
    
    #
    # method for running a remote query against the PostgreSQL database
    #
    def execute(self, query, args=None):
        
        start_time = time.time()
        
        # connect to database
        conn = psycopg2.connect(self.db_connect_string)
        
        # grab database cursor
        cur = conn.cursor()
        
        # execute remote query with or without arguments
        if (args is None):
            cur.execute(query)
        else:
            cur.execute(query, args)
        
        # send commit to the database
        conn.commit()
        
        # store the query result
        query_result = cur.fetchall()
        
        # close database connection
        conn.close()
        
        sys.stderr.write("[pggtfsdb_execute," + str(time.time() - start_time) + "]\n")
        
        # return the query result
        return query_result
    
    #
    # method for returning the data for a transit board event
    #
    def get_board_event_data(self, trip_id, stop_id):
    
        #route_desc = list( pggtfsdb.execute( "SELECT routes.route_id, routes.route_long_name, routes.route_short_name, routes.route_type FROM routes, trips WHERE routes.route_id=trips.route_id AND trip_id='" + trip_id + "'") )
        #agency_id = list( pggtfsdb.execute( "SELECT agency_id FROM routes WHERE route_id='" + str(route_desc[0][0]) + "'") )[0][0]
        #
        #stop_desc = list( pggtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id='" + stop_id + "'") )[0][0]
        #lat, lon = list( pggtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id='" + stop_id + "'") )[0]
        #
        #stop_headsign = list( pggtfsdb.execute( "SELECT stop_headsign FROM stop_times WHERE trip_id='" + trip_id + "' AND stop_id='" + stop_id + "'") )[0][0]
        
        start_time = time.time()
        
        # connect to database
        conn = psycopg2.connect(self.db_connect_string)
        
        # grab database cursor
        cur = conn.cursor()
        
        # generate query to get route data
        route_data_query = "SELECT routes.agency_id, routes.route_id, routes.route_long_name, routes.route_short_name, routes.route_type FROM routes, trips WHERE routes.route_id=trips.route_id AND trip_id='" + trip_id + "'"
        
        # execute route data query
        cur.execute(route_data_query)
        
        # grab the route data
        agency_id, route_id, route_long_name, route_short_name, route_type = cur.fetchone()
        
        # generate query to get stop data
        stop_data_query = "SELECT stop_name, stop_lat, stop_lon, parent_station FROM stops WHERE stop_id='" + stop_id + "'"
        
        # execute stop data query
        cur.execute(stop_data_query)
        
        # grab the stop data
        stop_name, stop_lat, stop_lon, parent_station = cur.fetchone()
        
        # generate query to get stop headsign data
        stop_headsign_query = "SELECT stop_headsign FROM stop_times WHERE trip_id='" + trip_id + "' AND stop_id='" + stop_id + "'"
        
        # execute stop headsign query
        cur.execute(stop_headsign_query)
        
        # grab the stop headsign data
        stop_headsign = cur.fetchone()[0]
        
        sys.stderr.write("[get_board_event_data," + str(time.time() - start_time) + "]\n")
        
        return (agency_id, route_id, route_long_name, route_short_name, route_type, stop_name, stop_lat, stop_lon, parent_station, stop_headsign)
    
    #
    # method for returning the data for a transit alight event
    #
    def get_alight_event_data(self, stop_id):
        
        #stop_desc = list( pggtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id='" + stop_id + "'") )[0][0]
        #lat, lon = list( pggtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id='" + stop_id + "'") )[0]
        
        start_time = time.time()
        
        # connect to database
        conn = psycopg2.connect(self.db_connect_string)
        
        # grab database cursor
        cur = conn.cursor()
        
        # generate query to get stop data
        stop_data_query = "SELECT stop_name, stop_lat, stop_lon, parent_station FROM stops WHERE stop_id='" + stop_id + "'"
        
        # execute stop data query
        cur.execute(stop_data_query)
        
        # grab the stop data
        stop_name, stop_lat, stop_lon, parent_station = cur.fetchone()
        
        sys.stderr.write("[get_alight_event_data," + str(time.time() - start_time) + "]\n")
        
        return (stop_name, stop_lat, stop_lon, parent_station)
    
    #
    # method for returning the closest station vertex to a coordinate pair
    #
    def get_station_vertex_from_coords(self, longitude, latitude):
        
        # connect to database
        conn = psycopg2.connect(self.db_connect_string)
        
        # grab database cursor
        cur = conn.cursor()
        
        # place coordinates in POINT GIS object
        geom_point = "'POINT(" + str(longitude) + ' ' + str(latitude) + ")'"
        
        #print "geom_point: " + str(geom_point)
        
        # longitude/latitude offset
        offset = 0.05
        
        # created BOX3D object for search space
        box3d_coords = "'BOX3D(" + str(longitude - offset) + ' ' + str(latitude - offset) + ',' + str(longitude + offset) + ' ' + str(latitude + offset) + ")'"
        
        #print "box3d_coords: " + str(box3d_coords)
        
        # generate query to search for closest OSM point to the provided coordinates
        dist_query = 'select stop_id, ST_distance_sphere(SetSRID(GeomFromText(' + geom_point + '),4326),location) as dist from stops order by dist asc limit 1'
        dist_box3d_query = 'select stop_id, ST_distance_sphere(SetSRID(GeomFromText(' + geom_point + '),4326),location) as dist from stops where location && SetSRID(' + box3d_coords + '::box3d,4326) order by dist asc limit 1'
        
        #print "dist_query: " + str(dist_query)
        #print "dist_box3d_query: " + str(dist_box3d_query)
        
        # execute the box3d-enhanced query
        cur.execute(dist_box3d_query)
        
        # fetch the first row from the results
        first_row = cur.fetchone()
        
        # if the first row contains no results
        if (first_row is None):
            
            # print
            #print "first_row is None for STATION coords (" + str(longitude) + "," + str(latitude) + ")"
            
            # execute the non-enhanced query
            cur.execute(dist_query)
            
            # fetch the first row from the results
            first_row = cur.fetchone()
        
        # send commit to the database
        conn.commit()
        
        # close database connection
        conn.close()
        
        # return osm vertex id
        return ('sta-' + first_row[0], first_row[1])
    
    #
    # method for returning the coordinates (lat, lon) for a station vertex
    #
    def get_coords_for_station_vertex(self, vertex_id):
        
        # connect to database
        conn = psycopg2.connect(self.db_connect_string)
        
        # grab database cursor
        cur = conn.cursor()
        
        # strip 'osm-' prefix from vertex_id
        vertex_id = vertex_id.replace('sta-','')
        
        # generate query to grab coordinates for vertex
        vertex_query = "select ST_AsText(location) from stops where stop_id='" + vertex_id + "'"
        
        # execute the query
        cur.execute(vertex_query)
        
        # fetch the first row from the results
        first_row = cur.fetchone()
        
        # send commit to the database
        conn.commit()
        
        # grab raw coordinates
        vertex_coords = first_row[0].replace('POINT(','').replace(')','')
        
        # close database connection
        conn.close()
        
        # return coordinates (lat, lon)
        return (float(vertex_coords[vertex_coords.index(' ')+1:]), float(vertex_coords[0:vertex_coords.index(' ')]))
    
    #
    # method for returning all the points along a transit path
    #
    def get_all_transit_path_points(self, trip_id):
        
        # connect to database
        conn = psycopg2.connect(self.db_connect_string)
        
        # grab database cursor
        cur = conn.cursor()
        
        # execute query to get trip shape id
        cur.execute("select shape_id from trips where trip_id='" + str(trip_id) + "'")
        
        # grab the shape id
        shape_id = cur.fetchone()[0]
        
        # send commit to the database
        conn.commit()
        
        # execute query to get the list of all points along the shape
        cur.execute("select ST_AsText(location) from shapes where shape_id='" + shape_id + "' order by shape_pt_sequence asc")
        
        # grab list of points along the the shape
        path_points = cur.fetchall()
        
        # send commit to the database
        conn.commit()
        
        # iterate through points
        for i in range(len(path_points)):
            mod_point = path_points[i][0].replace('POINT(','').replace(')','').replace(' ',',')
            point_lat = mod_point[mod_point.index(',')+1:]
            point_lon = mod_point[0:mod_point.index(',')]
            path_points[i] = point_lat + ',' + point_lon
        
        # close database connection
        conn.close()
        
        # return transit path points
        return path_points
    
    #
    # method for returning the points along a transit path between board_stop_id and alight_stop_id
    #
    def get_transit_path_points(self, trip_id, board_stop_id, alight_stop_id):
        
        # connect to database
        conn = psycopg2.connect(self.db_connect_string)
        
        # grab database cursor
        cur = conn.cursor()
        
        # execute query to get board stop coordinates
        cur.execute("select stop_lat, stop_lon from stops where stop_id='" + str(board_stop_id) + "'")
        
        # grab the board stop location
        board_stop_loc = cur.fetchone()
        
        # send commit to the database
        conn.commit()
        
        # execute query to get alight stop coordinates
        cur.execute("select stop_lat, stop_lon from stops where stop_id='" + str(alight_stop_id) + "'")
        
        # grab the alight stop location
        alight_stop_loc = cur.fetchone()
        
        # send commit to the database
        conn.commit()
        
        # execute query to get trip shape id
        cur.execute("select shape_id from trips where trip_id='" + str(trip_id) + "'")
        
        # grab the shape id
        shape_id = cur.fetchone()[0]
        
        # send commit to the database
        conn.commit()
        
        # create list for storing points along the the shape between the stops
        path_points = []
        
        if (shape_id is not None):
            
            # check the shape id
            if (shape_id.strip() == ''):
                return [str(board_stop_loc[0]) + ',' + str(board_stop_loc[1]), str(alight_stop_loc[0]) + ',' + str(alight_stop_loc[1])]
            
            # send commit to the database
            #conn.commit()
            
            # execute query to get shape point sequence value for the board stop
            cur.execute("select shapes.shape_pt_sequence, ST_Distance(shapes.location, stops.location) as distance from shapes, stops where shapes.shape_id='" + shape_id + "' and stops.stop_id='" + str(board_stop_id) + "' order by distance asc limit 1")
            
            # grab the shape point sequence value for the board stop
            board_shape_pt_sequence = cur.fetchone()[0]
            
            # send commit to the database
            conn.commit()
            
            # execute query to get shape point sequence value for the alight stop
            cur.execute("select shapes.shape_pt_sequence, ST_Distance(shapes.location, stops.location) as distance from shapes, stops where shapes.shape_id='" + shape_id + "' and stops.stop_id='" + str(alight_stop_id) + "' order by distance asc limit 1")
            
            # grab the shape point sequence value for the alight stop
            alight_shape_pt_sequence = cur.fetchone()[0]
            
            # send commit to the database
            conn.commit()
            
            # determine which point sequence value is greater
            if (board_shape_pt_sequence < alight_shape_pt_sequence):
                
                # execute query to get the list of points along the shape between the board and alight stops
                cur.execute("select ST_AsText(location) from shapes where shape_id='" + shape_id + "' and shape_pt_sequence >= " + str(board_shape_pt_sequence) + " and shape_pt_sequence <= " + str(alight_shape_pt_sequence) + " order by shape_pt_sequence asc")
            else:
                
                # execute query to get the list of points along the shape between the alight and board stops
                cur.execute("select ST_AsText(location) from shapes where shape_id='" + shape_id + "' and shape_pt_sequence >= " + str(alight_shape_pt_sequence) + " and shape_pt_sequence <= " + str(board_shape_pt_sequence) + " order by shape_pt_sequence desc")
            
            # grab list of points along the the shape between the stops
            path_points = cur.fetchall()
            
            # send commit to the database
            conn.commit()
            
            # iterate through points
            for i in range(len(path_points)):
                mod_point = path_points[i][0].replace('POINT(','').replace(')','').replace(' ',',')
                point_lat = mod_point[mod_point.index(',')+1:]
                point_lon = mod_point[0:mod_point.index(',')]
                path_points[i] = point_lat + ',' + point_lon
            
        # close database connection
        conn.close()
        
        # insert board stop location to front of path points list
        path_points.insert(0, str(board_stop_loc[0]) + ',' + str(board_stop_loc[1]))
        
        # append alight stop location to end of path points list
        path_points.append(str(alight_stop_loc[0]) + ',' + str(alight_stop_loc[1]))
        
        # return transit path points
        return path_points

