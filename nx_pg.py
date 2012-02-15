#!/usr/bin/env  python
# -*- coding: utf-8 -*-
"""
------------
NetworkX is a python library for graph analysis. Using edge and node 
attribution it can be used for spatial network analysis (with geography stored 
as node/edge attributes). This module supports the use of NetworkX for the
development of network analysis of spatial networks stored in a PostGIS 
spatial database by acting as an interface to node and edge tables which 
contain graph nodes and edges.

-----
Notes
-----
Node support
Note that nodes are defined by the edges at network creation and the reading 
of node tables independently is not currently supported (because without 
defining a primary key/foreign key relationship this can easily break the :
network). This issue is solved in nx_pgnet which should be used for proper
storage of networks in PostGIS tables. To read/write PostGIS networks 
(as defined by a network schema use) the nx_pgnet module.

Output tables
For each network written two tables are created: edges and nodes. 
This representation is similar to that of the nx_shp module 
(for reading/writing network shapefiles). 

Coordinate system support
nx_pg has no support for defining a coordinate system of the output tables. 
Geometry is written without an SRS value, when viewing using a GIS you must
specify the correct coordinate system for the network. nx_pgnet has coordinate
systems support for network tables.

Graph/Network terms
Note that the terms 'graph' and 'network' are used interchangeably within the 
software and documentation. To some extent a 'graph' refers to a topological 
object (often in memory) with none or limited attribution, whilst a 'network' 
refers to a graph object with attribution of edges and nodes and with 
geography defined, although this is not always the case.

----------------
Module structure    
----------------
The module has two key functions:
    - read_pg:
        Function to create NetworkX graph instance from PostGIS table(s) 
        representing edge and node objects.
    - write_pg:
        Function to create PostGIS tables (edge and node) from NetworkX graph
        instance.
        
    - Other functions support the read and write operations.
    
--------------------
Database connections
--------------------
Connections to PostGIS are created using the OGR simple feature library and are
passed to the read() and write() classes. See http://www.gdal.ogr/ogr

Connections are mutually exclusive between read_pg and write_pg, although you 
can of course read and write to the same database. 
You must pass a valid connection to the read or write classes for the module 
to work.

To create a connection using the OGR Python (SWIG) OGR bindings to a database
on localhost:
    
    import osgeo.ogr as ogr
    conn = ogr.Open("PG: host='127.0.0.1' dbname='database' user='postgres'
                    password='password'")
    
--------
Examples
--------
The following are examples of high level read and write network operations. For
more detailed information see method documentation below.

Reading a network from PostGIS table of LINESTRINGS representing edges:
    
    import nx_pg
    import osgeo.ogr as ogr
    
    # Create a connection
    conn = ogr.Open("PG: host='127.0.0.1' dbname='database' user='postgres'
                    password='password'")

    # Read a network
    # Note 'my_network' is the name of the network stored in the 'Graphs' table
    
    network = nx_pg.read_pg(conn, 'tablename')
    

Writing a NetworkX graph instance to a PostGIS schema:
    
    # Write the network to the same database but under a different name.
    # Note if 'overwrite=True' then an existing network in the database of the 
    # same name will be overwritten.
    
    nx_pg.write_pg(conn, network, 'new_network, overwrite=False')
    
------------
Dependencies
------------
Python 2.6 or later
NetworkX 1.6 or later
OGR 1.8.0 or later

-------------
Copyright (C)
-------------
Tomas Holderness / Newcastle University

Developed by Tom Holderness at Newcastle University School of Civil Engineering
and Geosciences, geoinfomatics group:

---------------
Acknowledgement 
---------------
Acknowledgement must be made to the nx_shp developers as much of the 
functionality of this module is the same.

-------
License
-------
This software is released under a BSD style license which must be compatible
with the NetworkX license because of similarities with NetworkX source code.:
    
See LICENSE.TXT or type
nx_pg.license() for full details.

-------
Credits
-------
Tomas Holderness, David Alderson, Alistair Ford, Stuart Barr and Craig Robson.

-------
Contact
-------
tom.holderness@ncl.ac.uk
www.staff.ncl.ac.uk/tom.holderness

"""
__author__ = "Tom Holderness"
__created__ = "Thu Jan 19 15:55:13 2012"
__year__ = "2011"
__version__ = "0.9.1"

import networkx as nx
import osgeo.ogr as ogr

# Ask ogr to use Python exceptions rather than stderr messages.
##ogr.UseExceptions()

def getfieldinfo(lyr, feature, flds):
    ''' Get information about fields - borrowed from nx_shp.py'''
    f = feature
    return [f.GetField(f.GetFieldIndex(x)) for x in flds]
    
def read_pg(conn, tablename):
    '''Function to convert geometry from PostGIS table to Network.'''
    # Create Directed graph to store output  
    net = nx.DiGraph()
    # Empty attributes dict
    for lyr in conn:
        if lyr.GetName() == tablename:
            flds = [x.GetName() for x in lyr.schema]
            # Get the number of features in the layer
            for findex in xrange(lyr.GetFeatureCount()):
                # Get a specific feature
                f = lyr.GetFeature(findex+1)
                if f is None:
                   pass # Catch any returned features which are None. 
                   #Raise warning?
                else:
                   flddata = getfieldinfo(lyr, f, flds )
                   attributes = dict(zip(flds, flddata))
                   attributes["TableName"] = lyr.GetName()
                   # Get the geometry for that feature
                   geom = f.GetGeometryRef()
                   #print geom
                   # We've got a Multiline geometry so split into line segments
                   if ogr.Geometry.GetGeometryName(geom) == 'MULTILINESTRING':
                   #print f.GetGeomertyTypeName()
                       for line in geom:
                           # Get points in line
                           n = line.GetPointCount()
                           # Get the attributes (akin to nx_shp)
                           attributes["Wkb"] = ogr.Geometry.ExportToWkb(line)
                           attributes["Wkt"] = ogr.Geometry.ExportToWkb(line)
                           attributes["Json"] = ogr.Geometry.ExportToWkb(line)
                           #print type(line.GetPoint(0))
                           net.add_edge(line.GetPoint_2D(0), 
                                        line.GetPoint_2D(n-1), attributes)
                   elif ogr.Geometry.GetGeometryName(geom) == 'LINESTRING':
                       n = geom.GetPointCount()
                       attributes["Wkb"] = ogr.Geometry.ExportToWkb(geom)
                       attributes["Wkt"] = ogr.Geometry.ExportToWkb(geom)
                       attributes["Json"] = ogr.Geometry.ExportToWkb(geom)  
                       net.add_edge(geom.GetPoint_2D(0), geom.GetPoint_2D(n-1), 
                                    attributes)
                   elif ogr.Geometry.GetGeometryName(geom) == 'POINT':
                       net.add_node((geom.GetPoint_2D(0)), attributes)
                   else:
                       raise ValueError, "PostGIS geometry type not supported."
    return net

def netgeometry(key, data):
        if data.has_key('Wkb'):
            geom = ogr.CreateGeometryFromWkb(data['Wkb'])
        elif data.has_key('Wkt'):
            geom = ogr.CreateGeometryFromWkt(data['Wkt'])
        elif type(key[0]) == 'tuple': # edge keys are packed tuples
            geom = ogr.Geometry(ogr.wkbLineString)
            _from, _to = key[0], key[1]
            geom.SetPoint(0, *_from)
            geom.SetPoint(1, *_to)
        else:
            geom = ogr.Geometry(ogr.wkbPoint)
            geom.SetPoint(0, *key)
        return geom

def create_feature(geometry, lyr, attributes=None):
  feature = ogr.Feature(lyr.GetLayerDefn())
  feature.SetGeometry(geometry)
  if attributes != None:
      for field, data in attributes.iteritems(): 
         feature.SetField(field,data)
  lyr.CreateFeature(feature)
  feature.Destroy()

def write_pg(conn, network, tablename_prefix, overwrite=False):
    '''Function to write Network with geometry to PostGIS edges and nodes tables.'''
    G = network
    tbledges = tablename_prefix+'_edges'
    tblnodes = tablename_prefix+'_nodes'

    if overwrite is True:
      try:
         conn.DeleteLayer(tbledges)
      except:
         pass
      try:
         conn.DeleteLayer(tblnodes)
      except:
         pass    
    edges = conn.CreateLayer(tbledges, None, ogr.wkbLineString)
    nodes = conn.CreateLayer(tblnodes, None, ogr.wkbPoint)
    
    for n in G:
        data = G.node[n].values() or [{}]
        g = netgeometry(n, data[0])
        create_feature(g, nodes)
    
    fields = {}
    attributes = {}
    OGRTypes = {int:ogr.OFTInteger, str:ogr.OFTString, float:ogr.OFTReal}
    for e in G.edges(data=True):
        data = G.get_edge_data(*e)
        g = netgeometry(e, data)
        # Loop through data in edges
        for key, data in e[2].iteritems():
            # Reject data not for attribute table
            if (key != 'Json' and key != 'Wkt' and key != 'Wkb' 
                and key != 'ShpName'):
                  # Add new attributes for each feature
                  if key not in fields:
                     if type(data) in OGRTypes:
                         fields[key] = OGRTypes[type(data)]
                     else:
                         fields[key] = ogr.OFTString
                     newfield = ogr.FieldDefn(key, fields[key])
                     edges.CreateField(newfield)
                     attributes[key] = data
                  # Create dict of single feature's attributes
                  else:
                     attributes[key] = data
         # Create the feature with attributes
        
        create_feature(g, edges, attributes)

    nodes, edges = None, None    
