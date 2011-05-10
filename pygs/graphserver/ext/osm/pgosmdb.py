#
# Class for handling interaction with OSMDB stored in PostgreSQL with PostGIS extensions.
# Author: James P. Biagioni (jbiagi1@uic.edu)
# Company: University of Illinois at Chicago
# Last modified: 11/17/09
#

import psycopg2
import time
import sys

class PostgresGIS_OSMDB:
    
    #
    # initializer method for connecting to PostgreSQL database
    #
    def __init__(self, db_connect_string):
        
        # store the connection string
        self.db_connect_string = db_connect_string
    
    #
    # method to create a database connection
    #
    def create_pgosmdb_connection(self):
        
        # return a database connection
        return psycopg2.connect(self.db_connect_string)
    
    #
    # method to close a database connection
    #
    def close_pgosmdb_connection(self, conn):
        
        # close database connection
        conn.close()
    
    #
    # method for returning the closest osm vertex to a coordinate pair
    #
    def get_osm_vertex_from_coords(self, conn, longitude, latitude):
        
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
        dist_query = 'select id, ST_distance_sphere(SetSRID(GeomFromText(' + geom_point + '),4326),location) as dist from nodes where endnode_refs > 1 order by dist asc limit 1'
        dist_box3d_query = 'select id, ST_distance_sphere(SetSRID(GeomFromText(' + geom_point + '),4326),location) as dist from nodes where endnode_refs > 1 and location && SetSRID(' + box3d_coords + '::box3d,4326) order by dist asc limit 1'
        
        #print "dist_query: " + str(dist_query)
        #print "dist_box3d_query: " + str(dist_box3d_query)
        
        # execute the box3d-enhanced query
        cur.execute(dist_box3d_query)
        
        # fetch the first row from the results
        first_row = cur.fetchone()
        
        # if the first row contains no results
        if (first_row is None):
            
            # print
            #print "first_row is None for OSM coords (" + str(longitude) + "," + str(latitude) + ")"
            
            # execute the non-enhanced query
            cur.execute(dist_query)
            
            # fetch the first row from the results
            first_row = cur.fetchone()
        
        # return osm vertex id
        return ('osm-' + first_row[0], first_row[1])
    
    #
    # method for returning the coordinates (lat, lon) for an osm vertex
    #
    def get_coords_for_osm_vertex(self, conn, vertex_id):
        
        # grab database cursor
        cur = conn.cursor()
        
        # strip 'osm-' prefix from vertex_id
        vertex_id = vertex_id.replace('osm-','')
        
        # generate query to grab coordinates for vertex
        vertex_query = "select ST_AsText(location) from nodes where id='" + vertex_id + "'"
        
        # execute the query
        cur.execute(vertex_query)
        
        # fetch the first row from the results
        first_row = cur.fetchone()
        
        # grab raw coordinates
        vertex_coords = first_row[0].replace('POINT(','').replace(')','')
        
        # return coordinates (lat, lon)
        return (float(vertex_coords[vertex_coords.index(' ')+1:]), float(vertex_coords[0:vertex_coords.index(' ')]))
    
    #
    # method for returning the street name and path geometry for a graph edge
    #
    def get_street_name_and_path_geometry_from_edge(self, conn, edge_name):
        
        start_time = time.time()
        
        # grab database cursor
        cur = conn.cursor()
        
        # generate query to grab way tags, and start and end node locations
        street_query = "select ways.tags, ST_AsText(start_node.location), ST_AsText(end_node.location) from edges, nodes as start_node, nodes as end_node, ways where start_node.id=start_nd and end_node.id=end_nd and ways.id=parent_id and edges.id='" + edge_name + "'"
        
        # execute the query
        cur.execute(street_query)
        
        # fetch the first row from the results
        first_row = cur.fetchone()
        
        # create dictionary from returned tags
        street_dict = eval(first_row[0])
        
        # store start node location
        start_node_loc = str(first_row[1]).replace('POINT(','').replace(')','')
        
        # store end node location
        end_node_loc = str(first_row[2]).replace('POINT(','').replace(')','')
        
        # if there is a name for this street
        if 'name' in street_dict:
        
            # store the street name
            street_name = street_dict['name'].replace("&","&amp;")
            
        else:
        
            # store an 'Unknown' street name
            street_name = "Unknown"
        
        # store the path geometry
        path_geometry = start_node_loc + "," + end_node_loc
        
        sys.stderr.write("[get_street_name_and_path_geometry_from_edge," + str(time.time() - start_time) + "]\n")
        
        # return the street name and path geometry
        return (street_name, path_geometry)
    
