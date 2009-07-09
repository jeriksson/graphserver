#
# Class for handling interaction with GTFSDB stored in PostgreSQL with PostGIS extensions.
# Author: James P. Biagioni (jbiagi1@uic.edu)
# Company: University of Illinois at Chicago
# Last modified: 6/3/09
#

import psycopg2

class PostgresGIS_GTFSDB:
    
    #
    # initializer method for connecting to PostgreSQL database
    #
    def __init__(self, db_connect_string):
        
        # connect to database
        self.conn = psycopg2.connect(db_connect_string)
    
    #
    # method for returning the points along a transit path
    #
    def get_transit_path_points(self, trip_id, board_stop_id, alight_stop_id):
        
        # grab database cursor
        cur = self.conn.cursor()
        
        # execute query to get trip shape id
        cur.execute("select shape_id from trips where trip_id='" + str(trip_id) + "'")
        
        # grab the shape id
        shape_id = cur.fetchone()[0]
        
        # send commit to the database
        self.conn.commit()
        
        # execute query to get shape point sequence value for the board stop
        cur.execute("select shapes.shape_pt_sequence, ST_Distance(shapes.location, stops.location) as distance from shapes, stops where shapes.shape_id='" + shape_id + "' and stops.stop_id='" + str(board_stop_id) + "' order by distance asc limit 1")
        
        # grab the shape point sequence value for the board stop
        board_shape_pt_sequence = cur.fetchone()[0]
        
        # send commit to the database
        self.conn.commit()
        
        # execute query to get shape point sequence value for the alight stop
        cur.execute("select shapes.shape_pt_sequence, ST_Distance(shapes.location, stops.location) as distance from shapes, stops where shapes.shape_id='" + shape_id + "' and stops.stop_id='" + str(alight_stop_id) + "' order by distance asc limit 1")
        
        # grab the shape point sequence value for the alight stop
        alight_shape_pt_sequence = cur.fetchone()[0]
        
        # send commit to the database
        self.conn.commit()
        
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
        self.conn.commit()
        
        # iterate through points
        for i in range(len(path_points)):
            mod_point = path_points[i][0].replace('POINT(','').replace(')','').replace(' ',',')
            point_lat = mod_point[mod_point.index(',')+1:]
            point_lon = mod_point[0:mod_point.index(',')]
            path_points[i] = point_lat + ',' + point_lon
        
        # return transit path points
        return path_points

