#
# Class for handling interaction with OSMDB stored in PostgreSQL with PostGIS extensions.
# Author: James P. Biagioni (jbiagi1@uic.edu)
# Company: University of Illinois at Chicago
# Last modified: 9/23/09
#

import psycopg2

class PostgresGIS_OSMDB:
    
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
        
        # return the query result
        return query_result
    
    #
    # method for returning the closest osm vertex to a coordinate pair
    #
    def get_osm_vertex_from_coords(self, longitude, latitude):
        
        # connect to database
        conn = psycopg2.connect(self.db_connect_string)
        
        # grab database cursor
        cur = conn.cursor()
        
        # place coordinates in POINT GIS object
        geom_point = "'POINT(" + str(longitude) + ' ' + str(latitude) + ")'"
        
        # generate query to search for closest OSM point to the provided coordinates
        dist_query = 'select id, ST_distance_sphere(SetSRID(GeomFromText(' + geom_point + '),4326),location) as dist from nodes order by dist asc limit 1'
        
        # execute the query
        cur.execute(dist_query)
        
        # fetch the first row from the results
        first_row = cur.fetchone()
        
        # send commit to the database
        conn.commit()
        
        # close database connection
        conn.close()
        
        # return osm vertex id
        return 'osm-' + first_row[0]
    
    #
    # method for returning the coordinates (lat, lon) for an osm vertex
    #
    def get_coords_for_osm_vertex(self, vertex_id):
        
        # connect to database
        conn = psycopg2.connect(self.db_connect_string)
        
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
        
        # send commit to the database
        conn.commit()
        
        # grab raw coordinates
        vertex_coords = first_row[0].replace('POINT(','').replace(')','')
        
        # close database connection
        conn.close()
        
        # return coordinates (lat, lon)
        return (float(vertex_coords[vertex_coords.index(' ')+1:]), float(vertex_coords[0:vertex_coords.index(' ')]))
    
    #
    # method for returning the street name for a graph edge
    #
    def get_street_name_from_edge(self, edge_name):
        
        # connect to database
        conn = psycopg2.connect(self.db_connect_string)
        
        # grab database cursor
        cur = conn.cursor()
        
        # generate query to grab tags for way matching the edge name
        tags_query = "select tags from ways where id='" + edge_name + "'"
        
        # execute the query
        cur.execute(tags_query)
        
        # fetch the first row from the results
        first_row = cur.fetchone()
        
        # send commit to the database
        conn.commit()
        
        # create dictionary from returned tags
        street_dict = eval(first_row[0])
        
        # if there is a name for this street
        if 'name' in street_dict:
        
            # store the street name
            street_name = street_dict['name'].replace("&","&amp;")
            
        else:
        
            # store an 'Unknown' street name
            street_name = "Unknown"
        
        # close database connection
        conn.close()
        
        # return the street name
        return street_name
    
    #
    # method for returning the street name and path geometry for a graph edge
    #
    def get_street_name_and_path_geometry_from_edge(self, edge_name):
        
        # connect to database
        conn = psycopg2.connect(self.db_connect_string)
        
        # grab database cursor
        cur = conn.cursor()
        
        # generate query to grab tags and path geometry for way matching the edge name
        tags_path_query = "select tags, ST_AsText(path) from ways where id='" + edge_name + "'"
        
        # execute the query
        cur.execute(tags_path_query)
        
        # fetch the first row from the results
        first_row = cur.fetchone()
        
        # send commit to the database
        conn.commit()
        
        # create dictionary from returned tags
        street_dict = eval(first_row[0])
        
        # if there is a name for this street
        if 'name' in street_dict:
        
            # store the street name
            street_name = street_dict['name'].replace("&","&amp;")
            
        else:
        
            # store an 'Unknown' street name
            street_name = "Unknown"
        
        # store the path geometry
        path_geometry = str(first_row[1])
        
        # close database connection
        conn.close()
        
        # return the street name and path geometry
        return (street_name, path_geometry)
    