#!/usr/bin/env  python
# -*- coding: utf-8 -*-
"""
test_suite_nx_pgnet - Module test suite for for nx_pgnet.

Contains main function tests  (moved from nx_pg_ncl.py)

"""
__author__ = "Tom Holderness"
__created__ = "Mon Jan 30 14:32:38 2012"
__version__ = "1.0"
import sys
sys.path.append('/home/a5245228/bin/python/postgres')
sys.path.append('/home/a5245228/bin/python/IAM/network/nx_pg/')
import nx_pg
import nx_pgnet
import nx_pgnet_sql
import pggkgetpass as gp
import osgeo.ogr as ogr

# Get database password from gnomekeyring (for development purposes only).
# REF: http://www.students.ncl.ac.uk/tom.holderness/pythongnomekeyring.php
PGS = gp.getpass('login', 'pg-ceg-tyndall')
#PGS = 'postgres'

def unit_test_read_pg(conn):
    net = nx_pgnet.read(conn).read_pg('LightRail_Baseline')
    
    if net.edges() != None:
        print 'Test passed.'
    
def unit_test_get_layer(conn):
    layer = nx_pgnet.write(conn).getlayer('graphs')
    print layer
    
def unit_test_write_pg(conn, net):
    nx_pgnet.write(conn).write_pg(net,  'test3', overwrite=True)
    
def unit_test_create_tables(conn, name, epsg):
    nx_pgnet_sql.ni_create_network_tables(conn, name, epsg)

def unit_test_write_pgnet(conn, net, name):
    nx_pgnet.write(conn).pgnet(net, name, 27700, overwrite=True)
    ##nx_pgnet_sql.ni_delete_network(conn, 'test4')
    ##exit(0)
    ##nx_pgnet.write(conn).write_pgnet(net, name, overwrite=True)
    
def unit_test_update_graphs_table(conn, net):
    nx_pgnet.write(conn).update_graph_table(net, 'new_graph','edges','nodes')
    
def unit_test_delete_network(conn, name):
    nx_pgnet_sql.ni_delete_network(conn, name)
    
def unit_test_read_graph(conn, name):
   G = nx_pgnet.read(conn).pgnet(name)
   print type(G)
   return G

def main():
    
    '''Testing nx_pg_ncl.py for NetworkX read/write of PostGIS tables.'''
    '''
    # Test read data from spatial non-schema table:
    conn = ogr.Open("PG: host='ceg-tyndall' dbname = 'tyndall_data' user= 'postgres' password="+PGS+"")
    print conn
    if conn == None:
        print 'conn error'
    net = nx_pg.read_pg(conn, 'LightRail_Baseline')
    
    # Test to write non-schema derived nx to schema tables.
    conn = ogr.Open("PG: host='ceg-tyndall' dbname = 'networks_14022012' user= 'postgres' password="+PGS+"")  
    print conn
    if conn is None:
      print 'conn is none'
      exit(0)
    nx_pgnet.write(conn).pgnet(net, 'LightRail_Baseline3', 27700, overwrite=True)
    '''
    conn = None
    # Test read data from schema
    conn = ogr.Open("PG: host='ceg-tyndall' dbname = 'tyndall_data' user= 'postgres' password="+PGS+"") 

    #net = nx_pg.read_pg(conn, 'LightRail_Baseline', 'LightRail_Baseline_Stations')
    net = nx_pgnet.read(conn).pgnet('LightRail_Baseline_Wards')
    print 'read'
    print 'writing'
    nx_pgnet.write(conn).pgnet(net, 'LightRail_Baseline_Three', 27700, overwrite=True)
    print 'written'
    #print net.edges(data=True)
    #print net.nodes(data=True)
    # Test to write data to schema
    
    ##conn = ogr.Open("PG: host='ceg-tyndall' dbname = 'tyndall_data' user= 'postgres' password="+PGS+"")  
    ##nx_pgnet.write(conn).pgnet(net, 'LightRail_Baseline', 27700, overwrite=True)
    
#    G = unit_test_write_(conn, 'LightRail_Baseline')
    #print G.edges(data=True)

    ##unit_test_create_tables(conn, 'ut_create_tables',27700)    
    
    ##sql = 'SELECT * FROM "Graphs" WHERE "GraphID" = 1;'
    ##for row in conn.ExecuteSQL(sql):
    ##    print row.Directed
    ##    print type(row.Directed)
    ##unit_test_write_pgnet(conn, G, 'LightRail_Baseline2')
    #unit_test_write_pg(conn, net)
    #unit_test_read_pg(conn)

    #unit_test_get_layer(conn)    
    
    # Do some stuff with network.
    
    # Write network to PostGIS tables (use the same connection in this case).
    #print 'writing network'
    #conn = ogr.Open("PG: host='127.0.0.1' dbname='MIDAS-SPATIAL' \
    #   user='postgres' password="+PGS+"")  
    
    #write_pg(conn, net, 'lightrail_baseline_nd', overwrite=True)    
    
    #print "Done"
    #conn = None
if __name__ == "__main__":
    main()
