#
# Class for handling interaction with OSMDB stored in PostgreSQL with PostGIS extensions.
# Author: James P. Biagioni (jbiagi1@uic.edu)
# Company: University of Illinois at Chicago
# Last modified: 11/17/09
#

import psycopg2

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
        
        # create a database connection
        conn = psycopg2.connect(self.db_connect_string)
        
        # grab a database cursor
        cur = conn.cursor()
        
        # prepare query for get_osm_vertex_from_coords
        prepare_dist_query = "PREPARE get_osm_vertex_from_coords (text, text) AS SELECT id, ST_distance_sphere(ST_SetSRID(ST_GeomFromText($1),4326),location) AS dist FROM nodes WHERE endnode_refs > 1 AND location && ST_SetSRID($2::box3d,4326) ORDER BY dist ASC LIMIT 1"
        
        # create prepared statement for get_osm_vertex_from_coords
        cur.execute(prepare_dist_query)
        
        # prepare query for get_street_name_and_path_geometry_from_edge
        prepare_street_query = "PREPARE get_street_name_and_path_geometry_from_edge (text) AS SELECT ways.tags, ST_AsText(start_node.location), ST_AsText(end_node.location) FROM edges, nodes AS start_node, nodes AS end_node, ways WHERE start_node.id=start_nd AND end_node.id=end_nd AND ways.id=parent_id AND edges.id=$1"
        
        # create prepared statement for get_street_name_and_path_geometry_from_edge
        cur.execute(prepare_street_query)
        
        # prepare query for get_coords_for_osm_vertex
        prepare_vertex_query = "PREPARE get_coords_for_osm_vertex (text) AS SELECT ST_AsText(location) FROM nodes WHERE id=$1"
        
        # create prepared statement for get_coords_for_osm_vertex
        cur.execute(prepare_vertex_query)
        
        # return database connection
        return conn
    
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
        
        # longitude/latitude offset
        offset = 0.05
        
        # created BOX3D object for search space
        box3d_coords = "'BOX3D(" + str(longitude - offset) + ' ' + str(latitude - offset) + ',' + str(longitude + offset) + ' ' + str(latitude + offset) + ")'"
        
        # execute the box3d-enhanced prepared statement
        cur.execute("EXECUTE get_osm_vertex_from_coords (" + geom_point + "," + box3d_coords + ")")
        
        # fetch the first row from the results
        first_row = cur.fetchone()
        
        # if the first row contains no results
        if (first_row is None):
            
            # execute the non-box3d-enhanced query
            cur.execute("SELECT id, ST_distance_sphere(ST_SetSRID(ST_GeomFromText(" + geom_point + "),4326),location) AS dist FROM nodes WHERE endnode_refs > 1 ORDER BY dist ASC LIMIT 1")
            
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
        
        # execute the prepared statement
        cur.execute("EXECUTE get_coords_for_osm_vertex ('" + vertex_id + "')")
        
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
        
        # grab database cursor
        cur = conn.cursor()
        
        # execute the prepared statement
        cur.execute("EXECUTE get_street_name_and_path_geometry_from_edge ('" + edge_name + "')")
        
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
        
        # return the street name and path geometry
        return (street_name, start_node_loc + "," + end_node_loc)
    
