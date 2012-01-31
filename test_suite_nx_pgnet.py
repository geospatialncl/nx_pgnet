#!/usr/bin/env  python
# -*- coding: utf-8 -*-
"""
test_suite_nx_pgnet - Module test suite for for nx_pgnet.

Contains main function tests  (moved from nx_pg_ncl.py)

"""
__author__ = "Tom Holderness"
__created__ = "Mon Jan 30 14:32:38 2012"
__year__ = "2011"
__version__ = "1.0"

import nx_pgnet
import pggkgetpass as gp
import osgeo.ogr as ogr

# Get database password from gnomekeyring (for development purposes only).
# REF: http://www.students.ncl.ac.uk/tom.holderness/pythongnomekeyring.php
PGS = gp.getpass('login', 'pg-ceg-tyndall')

def unit_test_read_pg(conn):
    net = nx_pgnet.read(conn).read_pg('LightRail_Baseline')
    
    if net.edges() != None:
        print 'Test passed.'
        

    
def unit_test_get_layer(conn):
    layer = nx_pgnet.write(conn).getlayer('graphs')
    print layer
    
def unit_test_write_pg(conn, net):
    nx_pgnet.write(conn).write_pg(net,  'test3', overwrite=False)

def unit_test_write_pgnet(conn, net):
    nx_pgnet.write(conn).write_pgnet(net, 'test2',overwrite=True)
    
def unit_test_update_graphs_table(conn, net):
    nx_pgnet.write(conn).update_graph_table(net, 'new_graph','edges','nodes')

def main():
    
    '''Testing nx_pg_ncl.py for NetworkX read/write of PostGIS tables.'''
    # Create a source connecton
    conn = ogr.Open("PG: host='ceg-tyndall' dbname='tyndall_data' \
        user='postgres' password="+PGS+"")  
    
    net = nx_pgnet.read(conn).read_pg('LightRail_Baseline')
    #unit_test_update_graphs_table(conn, net)
    #unit_test_write_pgnet(conn, net)
    unit_test_write_pg(conn, net)
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
