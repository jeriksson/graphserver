#
# Class for handling interaction with GTFSDB stored in PostgreSQL with PostGIS extensions.
# Author: James P. Biagioni (jbiagi1@uic.edu)
# Company: University of Illinois at Chicago
# Last modified: 11/2/09
#

import psycopg2

class PostgresGIS_GTFSDB:
    
    #
    # initializer method for connecting to PostgreSQL database
    #
    def __init__(self, db_connect_string):
        
        # store the connection string
        self.db_connect_string = db_connect_string
    
    #
    # method to create a database connection
    #
    def create_pggtfsdb_connection(self):
        
        # create a database connection
        conn = psycopg2.connect(self.db_connect_string)
        
        # grab a database cursor
        cur = conn.cursor()
        
        # prepare query for get_board/alight_event_data
        prepare_stop_data_query = "PREPARE get_board_alight_event_data_stop_data (text) AS SELECT stop_name, stop_lat, stop_lon, parent_station FROM stops WHERE stop_id=$1"
        
        # create prepared statement for get_board/alight_event_data
        cur.execute(prepare_stop_data_query)
        
        # prepare queries for get_board_event_data
        prepare_route_data_query = "PREPARE get_board_event_data_route_data (text) AS SELECT routes.agency_id, routes.route_id, routes.route_long_name, routes.route_short_name, routes.route_type FROM routes, trips WHERE routes.route_id=trips.route_id AND trip_id=$1"
        prepare_stop_headsign_query = "PREPARE get_board_event_data_stop_headsign (text, text) AS SELECT stop_headsign FROM stop_times WHERE trip_id=$1 AND stop_id=$2"
        
        # create prepared statements for get_board_event_data
        cur.execute(prepare_route_data_query)
        cur.execute(prepare_stop_headsign_query)
        
        # prepare query for get_station_vertex_from_coords
        prepare_dist_query = "PREPARE get_station_vertex_from_coords (text, text) AS SELECT stop_id, ST_distance_sphere(SetSRID(GeomFromText($1),4326),location) as dist from stops where location && SetSRID($2::box3d,4326) ORDER BY dist ASC LIMIT 1"
        
        # create prepared statement for get_station_vertex_from_coords
        cur.execute(prepare_dist_query)
        
        # prepare query for get_coords_for_station_vertex
        prepare_vertex_query = "PREPARE get_coords_for_station_vertex (text) AS SELECT ST_AsText(location) FROM stops WHERE stop_id=$1"
        
        # create prepared statement for get_coords_for_station_vertex
        cur.execute(prepare_vertex_query)
        
        # return database connection
        return conn
    
    #
    # method to create a database connection for get_transit_path_points function
    #
    def create_transit_path_pggtfsdb_connection(self):
        
        # create a database connection
        conn = psycopg2.connect(self.db_connect_string)
        
        # grab a database cursor
        cur = conn.cursor()
        
        # prepare queries for get_transit_path_points
        prepare_stop_data_query = "PREPARE get_transit_path_points_stop_data (text) AS SELECT stop_lat, stop_lon FROM stops WHERE stop_id=$1"
        prepare_shape_pt_sequence_query = "PREPARE get_transit_path_points_shape_pt_sequence (text) AS SELECT shapes.shape_pt_sequence, ST_Distance(shapes.location, stops.location) AS distance FROM shapes, stops WHERE shapes.shape_id=$1 AND stops.stop_id=$2 ORDER BY distance ASC LIMIT 1"
        
        # create prepared statements for get_transit_path_points
        cur.execute(prepare_stop_data_query)
        cur.execute(prepare_shape_pt_sequence_query)
        
        # return database connection
        return conn
    
    #
    # method to close a database connection
    #
    def close_pggtfsdb_connection(self, conn):
        
        # close database connection
        conn.close()
    
    #
    # method for returning the data for a transit board event
    #
    def get_board_event_data(self, conn, trip_id, stop_id):
        
        # grab database cursor
        cur = conn.cursor()
        
        # execute route data prepared statement
        cur.execute("EXECUTE get_board_event_data_route_data ('" + trip_id + "')")
        
        # grab the route data
        agency_id, route_id, route_long_name, route_short_name, route_type = cur.fetchone()
        
        # execute stop data prepared statement
        cur.execute("EXECUTE get_board_alight_event_data_stop_data ('" + stop_id + "')")
        
        # grab the stop data
        stop_name, stop_lat, stop_lon, parent_station = cur.fetchone()
        
        # execute stop headsign prepared statement
        cur.execute("EXECUTE get_board_event_data_stop_headsign ('" + trip_id + "','" + stop_id + "')")
        
        # grab the stop headsign data
        stop_headsign = cur.fetchone()[0]
        
        return (agency_id, route_id, route_long_name, route_short_name, route_type, stop_name, stop_lat, stop_lon, parent_station, stop_headsign)
    
    #
    # method for returning the data for a transit alight event
    #
    def get_alight_event_data(self, conn, stop_id):
        
        # grab database cursor
        cur = conn.cursor()
        
        # execute stop data prepared statement
        cur.execute("EXECUTE get_board_alight_event_data_stop_data ('" + stop_id + "')")
        
        # grab the stop data
        stop_name, stop_lat, stop_lon, parent_station = cur.fetchone()
        
        return (stop_name, stop_lat, stop_lon, parent_station)
    
    #
    # method for returning the closest station vertex to a coordinate pair
    #
    def get_station_vertex_from_coords(self, conn, longitude, latitude):
        
        # grab database cursor
        cur = conn.cursor()
        
        # place coordinates in POINT GIS object
        geom_point = "'POINT(" + str(longitude) + ' ' + str(latitude) + ")'"
        
        # longitude/latitude offset
        offset = 0.05
        
        # created BOX3D object for search space
        box3d_coords = "'BOX3D(" + str(longitude - offset) + ' ' + str(latitude - offset) + ',' + str(longitude + offset) + ' ' + str(latitude + offset) + ")'"
        
        # execute the box3d-enhanced prepared statement
        cur.execute("EXECUTE get_station_vertex_from_coords (" + geom_point + "," + box3d_coords + ")")
        
        # fetch the first row from the results
        first_row = cur.fetchone()
        
        # if the first row contains no results
        if (first_row is None):
            
            # execute the non-box3d-enhanced query
            cur.execute("SELECT stop_id, ST_distance_sphere(SetSRID(GeomFromText(' + geom_point + '),4326),location) AS dist FROM stops ORDER BY dist ASC LIMIT 1")
            
            # fetch the first row from the results
            first_row = cur.fetchone()
        
        # return osm vertex id
        return ('sta-' + first_row[0], first_row[1])
    
    #
    # method for returning the coordinates (lat, lon) for a station vertex
    #
    def get_coords_for_station_vertex(self, conn, vertex_id):
        
        # grab database cursor
        cur = conn.cursor()
        
        # strip 'osm-' prefix from vertex_id
        vertex_id = vertex_id.replace('sta-','')
        
        # execute the prepared statement
        cur.execute("EXECUTE get_coords_for_station_vertex ('" + vertex_id + "')")
        
        # fetch the first row from the results
        first_row = cur.fetchone()
        
        # grab raw coordinates
        vertex_coords = first_row[0].replace('POINT(','').replace(')','')
        
        # return coordinates (lat, lon)
        return (float(vertex_coords[vertex_coords.index(' ')+1:]), float(vertex_coords[0:vertex_coords.index(' ')]))
    
    #
    # method for returning the points along a transit path between board_stop_id and alight_stop_id
    #
    def get_transit_path_points(self, conn, trip_id, board_stop_id, alight_stop_id):
        
        # grab database cursor
        cur = conn.cursor()
        
        # execute stop data prepared statement
        cur.execute("EXECUTE get_transit_path_points_stop_data ('" + board_stop_id + "')")
        
        # grab the board stop data
        board_stop_lat, board_stop_lon = cur.fetchone()
        
        # execute stop data prepared statement
        cur.execute("EXECUTE get_transit_path_points_stop_data ('" + alight_stop_id + "')")
        
        # grab the alight stop data
        alight_stop_lat, alight_stop_lon = cur.fetchone()
        
        # execute query to get trip shape id
        cur.execute("select shape_id from trips where trip_id='" + str(trip_id) + "'")
        
        # grab the shape id
        shape_id = cur.fetchone()[0]
        
        # create list for storing points along the the shape between the stops
        path_points = []
        
        if (shape_id is not None):
            
            # check the shape id
            if (shape_id.strip() == ''):
                return [str(board_stop_lat) + ',' + str(board_stop_lon), str(alight_stop_lat) + ',' + str(alight_stop_lon)]
            
            # execute prepared statement to get shape point sequence value for the board stop
            cur.execute("EXECUTE get_transit_path_points_shape_pt_sequence ('" + shape_id + "','" + board_stop_id + "')")
            
            # grab the shape point sequence value for the board stop
            board_shape_pt_sequence = cur.fetchone()[0]
            
            # execute prepared statement to get shape point sequence value for the alight stop
            cur.execute("EXECUTE get_transit_path_points_shape_pt_sequence ('" + shape_id + "','" + alight_stop_id + "')")
            
            # grab the shape point sequence value for the alight stop
            alight_shape_pt_sequence = cur.fetchone()[0]
            
            # determine which point sequence value is greater
            if (board_shape_pt_sequence < alight_shape_pt_sequence):
                
                # execute query to get the list of points along the shape between the board and alight stops
                cur.execute("select ST_AsText(location) from shapes where shape_id='" + shape_id + "' and shape_pt_sequence >= " + str(board_shape_pt_sequence) + " and shape_pt_sequence <= " + str(alight_shape_pt_sequence) + " order by shape_pt_sequence asc")
            else:
                
                # execute query to get the list of points along the shape between the alight and board stops
                cur.execute("select ST_AsText(location) from shapes where shape_id='" + shape_id + "' and shape_pt_sequence >= " + str(alight_shape_pt_sequence) + " and shape_pt_sequence <= " + str(board_shape_pt_sequence) + " order by shape_pt_sequence desc")
            
            # grab list of points along the the shape between the stops
            path_points = cur.fetchall()
            
            # iterate through points
            for i in range(len(path_points)):
                mod_point = path_points[i][0].replace('POINT(','').replace(')','').replace(' ',',')
                point_lat = mod_point[mod_point.index(',')+1:]
                point_lon = mod_point[0:mod_point.index(',')]
                path_points[i] = point_lat + ',' + point_lon
        
        # insert board stop location to front of path points list
        path_points.insert(0, str(board_stop_lat) + ',' + str(board_stop_lon))
        
        # append alight stop location to end of path points list
        path_points.append(str(alight_stop_lat) + ',' + str(alight_stop_lon))
        
        # return transit path points
        return path_points

