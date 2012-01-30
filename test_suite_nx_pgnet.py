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

import pggkgetpass as gp

# Get database password from gnomekeyring (for development purposes only).
# REF: http://www.students.ncl.ac.uk/tom.holderness/pythongnomekeyring.php
PGS = gp.getpass('login', 'pg-ceg-tyndall')

def main():
    '''Testing nx_pg_ncl.py for NetworkX read/write of PostGIS tables.'''
    # Create a source connecton
    conn = ogr.Open("PG: host='ceg-tyndall' dbname='tyndall_data' \
        user='postgres' password="+PGS+"")  
    
    print 'reading network'
    # Build network in Python (see module notes about input nodes tables.)
    
    net = read_pg(conn, 'LightRail_Baseline') #, 'LightRail_Baseline_Stations')
    # Do some stuff with network.
    
    # Write network to PostGIS tables (use the same connection in this case).
    print 'writing network'
    #conn = ogr.Open("PG: host='127.0.0.1' dbname='MIDAS-SPATIAL' \
    #   user='postgres' password="+PGS+"")  
    
    write_pg(conn, net, 'lightrail_baseline_nd', overwrite=True)    
    
    print "Done"
    conn = None
    
if __name__ == "__main__":
    main()
    
if __name__ == "__main__":
    main()
