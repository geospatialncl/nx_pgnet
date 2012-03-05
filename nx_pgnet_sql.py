#!/usr/bin/env  python
# -*- coding: utf-8 -*-
"""
nx_pgnet_sql.py - Module containing wrapper functions around database network
SQL functions.

"""
__author__ = "Tom Holderness"
__created__ = "Mon Feb  6 09:09:18 2012"
__version__ = "0.1"

import osgeo.ogr as ogr

def ni_create_network_tables(conn, prefix, epsg):
    '''Takes database connection, graph name and srid and creates network 
    tables (requires schema in database) returns true if succesful'''
    
    sql = ("SELECT * FROM ni_create_network_tables ('%s', %i);" % (prefix, epsg))
    
    for row in conn.ExecuteSQL(sql):
        result = row.ni_create_network_tables

    return result

def ni_delete_network(conn, prefix):
    '''Takes network tablename prefix and removes tables and graph table 
    entry.'''        
    
    sql = ("SELECT * FROM ni_delete_network('%s');" % prefix)
    conn.ExecuteSQL(sql)
    ##sql = ("DELETE FROM "'"Graphs"'" WHERE "'"GraphName"'" = '%s';" % prefix)
    ##print sql
    ##conn.ExecuteSQL(sql)

def ni_node_geometry_equaility(conn, prefix, geom):
    
    table = prefix+'_Nodes'
        
    sql = ("SELECT '%s.NodeID' FROM "'"%s"'" WHERE ST_Equals(ST_GeomFromText('%s',27700),%s);") % (table, table, geom, 'geom')
    result = conn.ExecuteSQL(sql)
        
    for row in result:
        print row
            
    return -1

def ni_edge_geometry_equaility(conn, prefix, geom):
    '''Takes network tablename prefix and geometry and checks if geometry 
    already exists in edge table.'''
    
    ''' - Calling node_geom_eq_check function. Dave to fix,
    sql = ("SELECT * FROM ni_edge_geometry_equality_check('%s', '%s');" % (prefix, geom))
    print sql
    for row in conn.ExecuteSQL(sql):
        result = row.ni_edge_geometry_equality_check
        
    return result
    '''
    table = prefix+'_Edge_Geometry'
    # Hacked version:
        
    sql = ("SELECT "'"%s"'"."'"GeomID"'" FROM "'"%s"'" WHERE ST_Equals(ST_GeomFromText('%s',27700),%s);") % (table, table, geom, 'geom')
    print sql
    result = conn.ExecuteSQL(sql)
        
    for row in result:
        print row
            
    return -1

def ni_check_network_tables():
    '''Check network tables exist'''
    
    sql = ('SELECT "GeomID" FROM "%s" ORDER BY "GeomID" DESC LIMIT 1;' % 
                                                            self.tbledge_geom)
                                                            
    for row in self.conn.ExecuteSQL(sql):
        GeomID = row.GeomID                            

def main():
    '''Main function.'''
    
if __name__ == "__main__":
    main()
