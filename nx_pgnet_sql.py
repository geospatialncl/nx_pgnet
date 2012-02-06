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
    
    sql = ("SELECT * FROM ni_create_network_tables (%s, %i);" % (prefix, epsg))
    
    for row in conn.ExecuteSQL(sql):
        result = row.ni_create_network_tables
        
    return result
        

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
