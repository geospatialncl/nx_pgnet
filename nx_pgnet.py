#!/usr/bin/env  python
# -*- coding: utf-8 -*-
"""
nx_pgnet - Read/write support for PostGIS network schema in NetworkX.

B{Introduction}

nx_pgnet is module for reading and writing NetworkX graphs to and from PostGIS 
tables as specified by the Newcastle University PostGIS network schema.

Note that the terms 'graph' and 'network' are used interchangeably within the 
software and documentation. To some extent a 'graph' refers to a topological 
object (often in memory) with none or limited attribution, whilst a 'network' 
refers to a graph object with attribution of edges and nodes and with 
geography defined, although this is not always the case.

nx_pgnet operations

read: PostGIS (network schema) --> NetworkX

write: PostGIS (network schema) <-- NetworkX    


B{Description}

NetworkX is a python library for graph analysis. Using edge and node 
attribution it can be used for spatial network analysis (with geography stored 
as node/edge attributes). This module supports the use of NetworkX for the
development of network analysis of spatial networks stored in a PostGIS 
spatial database by acting as an interface to a predefined table structure 
(the schema) in a PostGIS database from NetworkX Graph classes.

B{PostGIS Schema}

This module assumes that the required PostGIS network schema is available 
within the target/source PostGIS database. The schema allows for a
collection of tables to represent a spatial network, storing
network geography and attributes. The definition of the schema and the 
associated scripts for network creation are outside the scope of this 
documentation however the schema can be briefly described as the following 
tables:
    - Graphs:
        Holds a reference to all networks in the database, referencing
        Edge, Edge_Geometry and Node tables.

    - Edges:
        Holds a representation of a network edge by storing source and
        destination nodes and edge attributes. Contains foreign keys 
        to graph and edge geometry

    - Edge_Geometry:
        Holds geometry (PostGIS binary LINESTRING/MULTILINESTRING 
        representation).
        Edge geometry is stored separately to edges for storage/retrieval 
        performance where more than one edge share the same geometry.
        
    - Interdependency:
        Holds interdependencies between networks.
        
    - Interdependency_Edges:
        Holds interdependency geometry. 

B{Module structure    }

The module is split into three key classes:

    - read:
        Contains methods to read data from PostGIS network schema to a NetworkX 
        graph.
        
    - write:
        Contains methods to write a NetworkX graph to PostGIS network schema 
        tables.
        
    - nisql:
        Contains methods which act as a wrapper to the special PostGIS network 
        schema functions. 
        
    - errors:
        Class containing error catching, reporting and logging methods. 
        

Detailed documentation for each class can be found below contained in class 
document strings. The highest level functions for reading and writing data are:

Read:    
    >>> nx_pgnet.read().pgnet()
    >>> # Reads a network from PostGIS network schema into a NetworkX graph instance.

Write:
    >>> nx_pgnet.write().pgnet()
    >>> # Writes a NetworkX graph instance to PostGIS network schema tables.

Write (via csv):
	>>> nx_pgnet.write().pgnet_via_csv()
	>>> # Writes a NetworkX graph instance to PostGIS network schema tables, using the COPY CSV function available in PostgreSQL
	
B{Database connections}

Connections to PostGIS are created using the OGR simple feature library and are
passed to the read() and write() classes. See http://www.gdal.org/ogr

Connections are mutually exclusive between read() and write() and are contained 
within each class (i.e. all methods within those classes inherit the :
connection), although you can of course read and write to the same database. 
You must pass a valid connection to the read or write classes for the module 
to work.

To create a connection using the OGR python bindings to a database
on localhost:
    
    >>> import osgeo.ogr as ogr
    >>> conn = ogr.Open("PG: host='127.0.0.1' dbname='database' user='postgres'
    >>>                    password='password'")
    
B{Examples}

The following are examples of read and write network operations. For
more detailed information see method documentation below.

Reading a network from PostGIS schema to a NetworkX graph instance:
    
    >>> import nx_pgnet
    >>> import osgeo.ogr as ogr
    
    >>> # Create a connection
    >>> conn = ogr.Open("PG: host='127.0.0.1' dbname='database' user='postgres'
    >>>                    password='password'")

    >>> # Read a network
    >>> # Note 'my_network' is the name of the network stored in the 'Graphs' table
    >>> network = nx_pgnet.read(conn).pgnet('my_network')    

Writing a NetworkX graph instance to a PostGIS schema:
    
Write the network to the same database but under a different name.
'EPSG' is the EPSE code for the output network geometry.
Note if 'overwrite=True' then an existing network in the database of the 
same name will be overwritten.
    
    >>> epsg = 27700
    >>> nx_pgnet.write(conn).pgnet(network, 'new_network', epsg, overwrite=False)

B{Dependencies}

Python 2.6 or later
NetworkX 1.6 or later
OGR 1.8.0 or later

B{Copyright (C)}

Tomas Holderness & Newcastle University

Developed by Tom Holderness at Newcastle University School of Civil Engineering
and Geosciences, geoinfomatics group:

David Alderson, Alistair Ford, Stuart Barr, Craig Robson.

B{License}

This software is released under a BSD style license. See LICENSE.TXT or type
nx_pgnet.license() for full details.

B{Credits}

Tomas Holderness, David Alderson, Alistair Ford, Stuart Barr and Craig Robson.

B{Contact}

tom.holderness@ncl.ac.uk
www.staff.ncl.ac.uk/tom.holderness

B{Development Notes}

Where possible the PEP8/PEP257 style guide has been implemented.\n
To do:
    1. Check attribution of nodes from schema and non-schema sources 
        (blank old id fields are being copied over).
        2. Error  / warnings module.
        3. Investigate bug: "Warning 1: Geometry to be inserted is of type 
            Line String, whereas the layer geometry type is Multi Line String.
        Insertion is likely to fail!"
        4. Multi and directed graph support.
        5. 3D geometry support.
    
"""
__created__ = "January 2012"
__version__ = "0.9.2"
__author__ = """\n""".join(['Tomas Holderness (tom.holderness@ncl.ac.uk)',
                                'David Alderson (david.alderson@ncl.ac.uk)',
                                'Alistair Ford (a.c.ford@ncl.ac.uk)',
                                 'Stuart Barr (stuart.barr@ncl.ac.uk)'])
__license__ = 'BSD style. See LICENSE.TXT'                                

import networkx as nx
import osgeo.ogr as ogr
import osgeo.gdal as gdal
import csv
import sys
import re

# Ask ogr to use Python exceptions rather than stderr messages.
ogr.UseExceptions()
    
class Error(Exception):
    '''Class to handle network IO errors. '''
    # Error class. 
    # Ref:http://en.wikibooks.org/wiki/Python_Programming/Exceptions
    
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return repr(self.parameter)
    

class nisql:
    '''Contains wrappers for PostGIS network schema functions.
    
    Where possible avoid using this class directly. Uses the read and write
    classes instead.'''
    
    def __init__(self, db_conn):
        '''Setup connection to be inherited by methods.'''
        self.conn = db_conn
        if self.conn == None:
            raise Error('No connection to database.')
            
    def sql_function_check(self, function_name):
        '''Checks Postgres database for existence of specified function, 
            if not found raises error.'''
            
        sql = ("SELECT * FROM pg_proc WHERE proname = '%s';" % (function_name))
        result = None
        for row in self.conn.ExecuteSQL(sql):
            result = row
        if result == None:
            raise Error('Database error: SQL function %s does not exist.' % 
                            function_name)
        else:
            return None
    
    def create_network_tables(self, prefix, epsg, directed,
        multigraph):
        '''Wrapper for ni_create_network_tables function.
        
        Creates empty network schema PostGIS tables.
        Requires graph 'prefix 'name and srid to create empty network schema
        PostGIS tables.
        
        Returns True if succesful.'''
        
        # Create network tables
        sql = ("SELECT * FROM ni_create_network_tables ('%s', %i, \
        CAST(%i AS BOOLEAN), CAST(%i AS BOOLEAN));" % (
        prefix, epsg, directed, multigraph))
        
        result = None
        for row in self.conn.ExecuteSQL(sql):   
        
            result = row.ni_create_network_tables
        '''
        # Add geometry column
        sql = ("SELECT * FROM ni_add_geometry_columns ('%s', %i);" % (prefix,
               epsg))
        print sql
        self.conn.ExecuteSQL(sql)
        # Add foreign key constraints
        sql = ("SELECT * FROM ni_add_fr_constraints ('%s');" % (prefix,))
        self.conn.ExecuteSQL(sql)        
        '''
        return result
        
    def create_node_view(self, prefix):
        '''Wrapper for ni_create_node_view function.
        
        Creates a view containing node attributes and geometry values including
        int primary key suitable for QGIS.
        
        Requires network name ('prefix').
        
        Returns view name if succesful.'''
       
        viewname = None
        sql = "SELECT * FROM ni_create_node_view('%s')" % prefix
        for row in self.conn.ExecuteSQL(sql):
            viewname = row.ni_create_node_view            
        if viewname == None:
            error = "Could not create node view for network %s" % prefix
            raise Error(error)    
        return viewname
        
    def create_edge_view(self, prefix):
        '''Wrapper for ni_create_edge_view function.
        
        Creates a view containing edge attributes and edge geometry values. 
        Requires network name ('prefix').
        
        Returns view name if succesful.'''        
        viewname = None
        sql = "SELECT * FROM ni_create_edge_view('%s')" % prefix

        for row in self.conn.ExecuteSQL(sql):
            viewname = row.ni_create_edge_view
        if viewname == None:
            error = "Could not create edge view for network %s" % prefix
            raise Error(error)
            
        return viewname
    
    def add_graph_record(self, prefix, directed=False, multipath=False):
        '''Wrapper for ni_add_graph_record function.
        
        Creates a record in the Graphs table based on graph attributes.
        
        Returns new graph id of succesful.'''  
    
        sql = ("SELECT * FROM ni_add_graph_record('%s', FALSE, FALSE);" % 
                (prefix))
                
        result = self.conn.ExecuteSQL(sql)        
        return result

    def ni_node_snap_geometry_equality_check(self, prefix, wkt, srs, snap):
        '''Wrapper for ni_node_snap_geometry_equality_check function.
        
        Checks if geometry already eixsts in nodes table, based on input wkt and snap distance
        
        If not, returns None'''
        sql = ("SELECT * FROM ni_node_snap_geometry_equality_check('%s', '%s', %s, %s);" 
                % (prefix, wkt, srs, snap))
        result = None
        
        for row in self.conn.ExecuteSQL(sql):            
            result = row.ni_node_snap_geometry_equality_check
        
        return result
        
    def node_geometry_equality_check(self, prefix, wkt, srs):
        '''Wrapper for ni_node_geometry_equality_check function.
        
        Checks if geometry already eixsts in nodes table.
        
        If not, returns None'''
        
        sql = ("SELECT * FROM ni_node_geometry_equality_check('%s', '%s', %s);" 
                % (prefix, wkt, srs))
        result = None
        
        for row in self.conn.ExecuteSQL(sql):            
            result = row.ni_node_geometry_equality_check           
        return result
    
    def ni_edge_snap_geometry_equality_check(self, prefix, wkt, srs, snap):
        '''Wrapper for ni_edge_snap_geometry_equality_check function.
        
        Checks if geometry already eixsts in edges table, based on input wkt and snap distance
        
        If not, returns None'''
        sql = ("SELECT * FROM ni_edge_snap_geometry_equality_check('%s', '%s', %s, %s);" 
                % (prefix, wkt, srs, snap))
        result = None
        
        for row in self.conn.ExecuteSQL(sql):            
            result = row.ni_edge_snap_geometry_equality_check
        
        return result
    
    def edge_geometry_equality_check(self, prefix, wkt, srs):
        '''Wrapper for ni_edge_geometry_equality_check function.
        
        Checks if geometry already eixsts in nodes table. 
        
        If not, return None'''
        
        sql = ("SELECT * FROM ni_edge_geometry_equality_check('%s', '%s', %s);" 
                % (prefix, wkt, srs))
                
        result = None
        for row in self.conn.ExecuteSQL(sql):
            result = row.ni_edge_geometry_equality_check
        return result       
    
    def delete_network(self, prefix):
        '''Wrapper for ni_delete_network function.
        
        Deletes a network entry from the Graphs table and drops associated 
        tables.'''
        
        sql = ("SELECT * FROM ni_delete_network('%s');" % (prefix))
        
        result = None
        for row in self.conn.ExecuteSQL(sql):
            result = row.ni_delete_network
        return result

class read:
    '''Class to read and build networks from PostGIS schema network tables.'''

    def __init__(self, db_conn):
        '''Setup connection to be inherited by methods.'''
        self.conn = db_conn
        
        if self.conn == None:
            raise Error('No connection to database.')
            
    def getfieldinfo(self, lyr, feature, flds):
        '''Get information about fields from a table (as OGR feature).'''
        f = feature
        return [f.GetField(f.GetFieldIndex(x)) for x in flds]

    def pgnet_edges(self, graph):
        '''Reads edges from edge and edge_geometry tables and add to graph.'''

        # Join Edges and Edge_Geom
        edge_tbl_view = nisql(self.conn).create_edge_view(self.prefix)
        
        # Get lyr by name
        lyr = self.conn.GetLayerByName(edge_tbl_view)

        # Add error catch here if lyr is None. 
        # Error reading from edge table view, is it broken?        
        
        # Get current feature        
        feat = lyr.GetNextFeature()
        # Get fields
        flds = [x.GetName() for x in lyr.schema]
        # Loop features
        while feat is not None:
            # Read edge attrs.
            flddata = self.getfieldinfo(lyr, feat, flds)
            attributes = dict(zip(flds, flddata))
            #attributes['network'] = network_name
            geom = feat.GetGeometryRef()
            
            #can be a case where there is a feature but there is no geometry for that feature            
            if geom is not None:            
                
                #multilinestring, so don't split in to individual linestring geometries
                if (ogr.Geometry.GetGeometryName(geom) == 'MULTILINESTRING'):               
                    attributes["Wkb"] = ogr.Geometry.ExportToWkb(geom)
                    attributes["Wkt"] = ogr.Geometry.ExportToWkt(geom)
                    attributes["Json"] = ogr.Geometry.ExportToJson(geom)
                    graph.add_edge(attributes['Node_F_ID'], attributes['Node_T_ID'], attributes)            
                
                # Line geometry
                elif (ogr.Geometry.GetGeometryName(geom) == 'LINESTRING'):
                    n = geom.GetPointCount()
                    attributes["Wkb"] = ogr.Geometry.ExportToWkb(geom)
                    attributes["Wkt"] = ogr.Geometry.ExportToWkt(geom)
                    attributes["Json"] = ogr.Geometry.ExportToJson(geom) 
                    graph.add_edge(attributes['Node_F_ID'], 
                                     attributes['Node_T_ID'], attributes)
            feat = lyr.GetNextFeature() 
            
    def pgnet_nodes(self, graph):
        '''Reads nodes from node table and add to graph.'''

        # Join Edges and Edge_Geom
        node_tbl = nisql(self.conn).create_node_view(self.prefix)
        # Get lyr by name
        lyr = self.conn.GetLayerByName(node_tbl)
        # Get fields
        flds = [x.GetName() for x in lyr.schema]
        # Get current feature
        feat = lyr.GetNextFeature()
        # Loop features
        while feat is not None:
            # Read node attrs.
            flddata = self.getfieldinfo(lyr, feat, flds)
            attributes = dict(zip(flds, flddata))
            #attributes['network'] = network_name
            geom = feat.GetGeometryRef()
            ##if geom != None:
            attributes["Wkb"] = ogr.Geometry.ExportToWkb(geom)
            attributes["Wkt"] = ogr.Geometry.ExportToWkt(geom)
            graph.add_node((attributes['NodeID']), attributes)
            feat = lyr.GetNextFeature()
        
    def graph_table(self, prefix):
        '''Reads the attributes of a graph from the graph table. 
        
        Returns attributes as a dict of variables.'''  
        
        graph = None
        sql = ('SELECT * FROM    "Graphs" WHERE "GraphName" = \'%s\';' % prefix)
        for row in self.conn.ExecuteSQL(sql):
            graph = row.items()

        return graph
    
    def pgnet(self, prefix):
        '''Read a network from PostGIS network schema tables. 
        
        Returns instance of networkx.Graph().'''
        
        # Set up variables
        self.prefix = prefix
        # Get graph attributes
        graph_attrs = self.graph_table(self.prefix)
        if graph_attrs == None:
            error = "Can't find network '%s' in Graph table" % self.prefix
            raise Error(error)
        # Create empty graph (directed/un-directed)
        if graph_attrs['Directed'] == 0:
            G = nx.Graph()
        else:
            G.nx.DiGraph()
        # To do: MultiGraph
        # Assign graph attributes to graph
        for key, value in graph_attrs.iteritems():
            G.graph[key] = value
        
        self.pgnet_edges(G)
        self.pgnet_nodes(G)

        return G

class write:
    '''Class to write NetworkX instance to PostGIS network schema tables.'''
    
    def __init__(self, db_conn):
        '''Setup connection to be inherited by methods.'''
        self.conn = db_conn        
        if self.conn == None:
            raise Error('No connection to database.')

    def getlayer(self, tablename):
        '''Get a PostGIS table by name and return as OGR layer.
        
           Else, return None. '''
    
        sql = "SELECT * from pg_tables WHERE tablename = '%s'" % tablename 
        
        for row in self.conn.ExecuteSQL(sql):
            if row.tablename is None:
                return None
            else:
                return self.conn.GetLayerByName(tablename)           
    
    def netgeometry(self, key, data):
        '''Create OGR geometry from a NetworkX Graph using Wkb/Wkt attributes.
        
        '''        
        
        # Borrowed from nx_shp.py.        
        if data.has_key('Wkb'):                        
            geom = ogr.CreateGeometryFromWkb(data['Wkb'])
        elif data.has_key('Wkt'):            
            geom = ogr.CreateGeometryFromWkt(data['Wkt'])
        elif type(key[0]) == 'tuple': # edge keys are packed tuples            
            geom = ogr.Geometry(ogr.wkbLineString)
            #geom = ogr.Geometry(ogr.wkbMultiLineString)
            _from, _to = key[0], key[1]
            geom.SetPoint_2D(0, *_from)
            geom.SetPoint_2D(1, *_to)
        else:                         
            geom = ogr.Geometry(ogr.wkbPoint)
            geom.SetPoint_2D(0, *key)
        return geom
    
    def create_feature(self, lyr, attributes = None, geometry = None):
        '''Wrapper for OGR CreateFeature function.
        
        Creates a feature in the specified table with geometry and attributes.
        '''
        
        feature = ogr.Feature(lyr.GetLayerDefn())
        if attributes is not None:
            for field, data in attributes.iteritems(): 
                feature.SetField(field, data)
        if geometry is not None:
            feature.SetGeometry(geometry)
        lyr.CreateFeature(feature)
        feature.Destroy()

    def create_attribute_map(self, lyr, g_obj, fields):
        '''Build a dict of attribute field names, data and OGR data types. 
        
        Accepts graph object (either node or edge), fields and 
        returns attribute dictionary.'''

        attrs = {}        
        OGRTypes = {int:ogr.OFTInteger, str:ogr.OFTString, float:ogr.OFTReal}
        for key, data in g_obj.iteritems():
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
                    
                    lyr.CreateField(newfield)
                     
                    attrs[key] = data
                # Create dict of single feature's attributes
                else:
                    attrs[key] = data
        
        return attrs
                
    def update_graph_table(self, graph):
        '''Update the Graph table and return newly assigned Graph ID.'''
        result = nisql(self.conn).add_graph_record(self.prefix)

        sql = ('SELECT "GraphID" FROM "Graphs" ORDER BY "GraphID" DESC\
                    LIMIT 1;')
        GraphID = None
        for row in self.conn.ExecuteSQL(sql):
            GraphID = row.GraphID

        return GraphID
        
    def pgnet_edge(self, edge_attributes, edge_geom):
        '''Write an edge to Edge and Edge_Geometry tables.'''

        edge_wkt = edge_geom.ExportToWkt()
        
        #get the edge wkt        
        edge_wkt = edge_geom.ExportToWkt()
        # Get table definitions        
        featedge = ogr.Feature(self.lyredges.GetLayerDefn())
        featedge_geom = ogr.Feature(self.lyredge_geom.GetLayerDefn())
        
        # Test for geometry existance       
        GeomID = nisql(self.conn).edge_geometry_equality_check(self.prefix, 
                        edge_wkt, self.srs)

        if GeomID == None: # Need to create new geometry:            
            featedge_geom.SetGeometry(edge_geom)            
            self.lyredge_geom.CreateFeature(featedge_geom)
            #Get created edge_geom primary key (GeomID)
            sql = ('SELECT "GeomID" FROM "%s" ORDER BY "GeomID" DESC LIMIT 1;'
                    % self.tbledge_geom)
            
            for row in self.conn.ExecuteSQL(sql):            
                GeomID = row.GeomID            
                 
        # Append the GeomID to the edges attributes    
        edge_attributes['Edge_GeomID'] = GeomID
        
        #Attributes to edges table
        ##for field, data in edge_attributes.iteritems():
        for field, data in edge_attributes.items():    
            featedge.SetField(field, data)

        self.lyredges.CreateFeature(featedge)
        
    def pgnet_node(self, node_attributes, node_geom):
        '''Write a node to a Node table.
        
        Return the newly assigned NodeID.
        '''        
        featnode = ogr.Feature(self.lyrnodes_def)        
        NodeID = nisql(self.conn).node_geometry_equality_check(self.prefix,node_geom,self.srs)        
        if NodeID == None: # Need to create new geometry:
            featnode.SetGeometry(node_geom)
            
            for field, data in node_attributes.iteritems():
                featnode.SetField(field, data)
            
            self.lyrnodes.CreateFeature(featnode)
            sql = ('SELECT "NodeID" FROM "%s" ORDER BY "NodeID" DESC LIMIT 1;'
                    % self.tblnodes)
            
            for row in self.conn.ExecuteSQL(sql):
                NodeID = row.NodeID
        
        return NodeID

    def pgnet(self, network, tablename_prefix, srs, overwrite=False,
        directed = False, multigraph = False):
            
        '''Write NetworkX instance to PostGIS network schema tables.
        
        Updates Graph table with new network.
    
        Note that schema constrains must be applied in database. 
        There are no checks for database errors here.
        '''

        # Disable pg use copy or NodeID not-null error will be raised
        if gdal.GetConfigOption("PG_USE_COPY") == "YES":
            raise Error('Attempting to write database schema with GDAL option '
                        '"PG_USE_COPY=YES". Please do: '
                        'gdal.SetConfigOption("PG_USE_COPY", "NO") and reset '
                        'database connection.')        
        
        # First create network tables in database
        self.prefix = tablename_prefix        
        self.tbledges = tablename_prefix+'_Edges'
        self.tblnodes = tablename_prefix+'_Nodes'
        self.tbledge_geom = tablename_prefix+'_Edge_Geometry'
        self.srs = srs
                
        result = nisql(self.conn).create_network_tables(self.prefix, self.srs, 
                        directed, multigraph)
        
        if result == 0 or result == None:
            if overwrite is True:
                nisql(self.conn).delete_network(self.prefix)
                nisql(self.conn).create_network_tables(self.prefix, self.srs, 
                                                        directed, multigraph)
            else:
                raise Error('Network already exists.')
        
        G = network # Use G as network, networkx convention.               
        graph_id = self.update_graph_table(network)
        
        if graph_id == None:
            raise Error('Could not load network from Graphs table.')
                
        self.lyredges = self.getlayer(self.tbledges)
        self.lyrnodes = self.getlayer(self.tblnodes)        
        self.lyredge_geom = self.getlayer(self.tbledge_geom)  
        self.lyrnodes_def =  self.lyrnodes.GetLayerDefn()
        
        node_fields = {'GraphID':ogr.OFTInteger}  
        edge_fields = {'Node_F_ID':ogr.OFTInteger, 'Node_T_ID':ogr.OFTInteger, 
                  'GraphID':ogr.OFTInteger, 'Edge_GeomID':ogr.OFTInteger}
        
        for e in G.edges(data=True):
            
            data = G.get_edge_data(*e)                        
            edge_geom = self.netgeometry(e, data)       
            
            # Insert the start node            
            node_attrs = self.create_attribute_map(self.lyrnodes, G.node[e[0]], 
                                                   node_fields)
            
            
            node_attrs['GraphID'] = graph_id 

            node_geom = self.netgeometry(e[0], G.node[e[0]])            
            node_id = self.pgnet_node(node_attrs, node_geom)                        
            G[e[0]][e[1]]['Node_F_ID'] = node_id
            
            # Insert the end node            
            node_attrs = self.create_attribute_map(self.lyrnodes, G.node[e[1]], 
                                                   node_fields)            
            node_attrs['GraphID'] = graph_id
            # Check attribution of nodes
            node_geom = self.netgeometry(e[1], G.node[e[1]])            
            node_id = self.pgnet_node(node_attrs, node_geom)
            G[e[0]][e[1]]['Node_T_ID'] = node_id
                        
            # Set graph id.
            G[e[0]][e[1]]['GraphID'] = graph_id

            edge_attrs = self.create_attribute_map(self.lyredges, e[2], 
                                                   edge_fields)
                                     
            self.pgnet_edge(edge_attrs, edge_geom)
            
        nisql(self.conn).create_node_view(self.prefix)            
        nisql(self.conn).create_edge_view(self.prefix)
    
    def add_attribute_fields(self, lyr, g_obj, fields):        
        attrs = {}        
        OGRTypes = {int:ogr.OFTInteger, str:ogr.OFTString, float:ogr.OFTReal}
        for key, data in g_obj.iteritems():            
            if (key != 'Json' and key != 'Wkt' and key != 'Wkb' 
                and key != 'ShpName'):
                if key not in fields:
                    if type(data) in OGRTypes:
                        fields[key] = OGRTypes[type(data)]
                    else:
                        fields[key] = ogr.OFTString
                    newfield = ogr.FieldDefn(key, fields[key])
                    lyr.CreateField(newfield)
                     
                    attrs[key] = data               
                else:
                    attrs[key] = data
        
        return attrs
    
    def pgnet_via_csv(self, network, tablename_prefix, srs, overwrite=False, directed = False, multigraph = False, output_csv_folder='D://Spyder//NetworkInterdependency//network_scripts//pgnet_via_csv//'):
        
        '''
        function to write networkx network instance (network) to the database schema, via COPY from CSV
        - node table written out as csv (to output_csv_folder + tablename_prefix + '_Nodes' e.g. OSMeridian2_Rail_CSV_w_nt_Nodes.csv)
        - edge table written out as csv (to output_csv_folder + tablename_prefix + '_Edges' e.g. OSMeridian2_Rail_CSV_w_nt_Edges.csv)
        - edge_geometry table written out as csv (to output_csv_folder + tablename_prefix + '_Edge_Geometry' e.g. OSMeridian2_Rail_CSV_w_nt_Edge_Geometry.csv)
        - use PostgreSQL COPY command to copy csv file to PostGIS / PostgreSQL tables
        '''
        
        # Disable pg use copy or NodeID not-null error will be raised
        if gdal.GetConfigOption("PG_USE_COPY") == "YES":
            raise Error('Attempting to write database schema with GDAL option '
                        '"PG_USE_COPY=YES". Please do: '
                        'gdal.SetConfigOption("PG_USE_COPY", "NO") and reset '
                        'database connection.')        
        
        # First create network tables in database
        self.prefix = tablename_prefix        
        self.tbledges = tablename_prefix+'_Edges'
        self.tblnodes = tablename_prefix+'_Nodes'
        self.tbledge_geom = tablename_prefix+'_Edge_Geometry'
        self.srs = srs
        
        #create the network tables in the database
        #this OK to leave in the CSV writing version of the function because we need the correct GraphID inside each CSV file
        result = nisql(self.conn).create_network_tables(self.prefix, self.srs, directed, multigraph)
        
        if result == 0 or result == None:
            if overwrite is True:
                nisql(self.conn).delete_network(self.prefix)
                nisql(self.conn).create_network_tables(self.prefix, self.srs, 
                                                        directed, multigraph)
            else:
                raise Error('Network already exists.')
        
        #set the node, edge and edge_geometry tables
        self.lyredges = self.getlayer(self.tbledges)
        self.lyrnodes = self.getlayer(self.tblnodes)        
        self.lyredge_geom = self.getlayer(self.tbledge_geom)  
        self.lyrnodes_def =  self.lyrnodes.GetLayerDefn()
        
        #set the network
        G = network
        
        #grab the node and edge data
        node_data = G.nodes(data=True)
        edge_data = G.edges(data=True)[2]
        
        #stores all field names to be written to csv, which are then written to PostGIS
        node_table_fieldnames = []
        edge_table_fieldnames = []
        edge_geometry_table_fieldnames = []
        
        #to store fieldnames specific to the data being loaded i.e. for nodes not "GraphID", "geom", "NodeID"
        node_table_specific_fieldnames = []
        #to store fieldnames specific to the data being loaded i.e. for edges not "Node_F_ID", "Node_T_ID", "GraphID", "Edge_GeomID", "EdgeID"
        edge_table_specific_fieldnames = []
                
        #add the base schema fields to the node table fieldnames dict
        node_table_fieldnames.insert(0, 'GraphID')
        node_table_fieldnames.append('geom')
        node_table_fieldnames.append('NodeID')
                
        #define the node fields
        for key, data in node_data:            
            if len(data) > 0:
                for datakey, data_ in data.iteritems():    
                    node_table_fieldnames.append(datakey)
                    node_table_specific_fieldnames.append(datakey)
                break;
        
        #add the base schema fields to the edge table fieldnames dict
        edge_table_fieldnames.insert(0, 'Node_F_ID')
        edge_table_fieldnames.insert(1, 'Node_T_ID')
        edge_table_fieldnames.insert(2, 'GraphID')
        edge_table_fieldnames.append('Edge_GeomID')
        edge_table_fieldnames.append('EdgeID')
        
        #define the edge table fields
        for key in edge_data[2].keys():
            if (key != 'Json' and key != 'Wkt' and key != 'Wkb' 
                    and key != 'ShpName'): 
                edge_table_fieldnames.append(key)
                edge_table_specific_fieldnames.append(key)
        
        #define the edge geometry table fields
        edge_geometry_table_fieldnames.append('geom')
        edge_geometry_table_fieldnames.append('GeomID')
        
        
        #define the file names and paths for csv files for nodes, edges, edge_geometry
        node_csv_filename = '%s%s.csv' % (output_csv_folder, self.tblnodes)
        edge_csv_filename = '%s%s.csv' % (output_csv_folder, self.tbledges)
        edge_geom_csv_filename = '%s%s.csv' % (output_csv_folder, self.tbledge_geom)
        
        #define node, edge, edge_geometry csv file
        node_csv_file = open(node_csv_filename, 'wb')
        edge_csv_file = open(edge_csv_filename, 'wb')
        edge_geom_csv_file = open(edge_geom_csv_filename, 'wb')
        
        #define node, edge, edge_geometry csv file writers
        node_csv_writer = csv.writer(node_csv_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        edge_csv_writer = csv.writer(edge_csv_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        edge_geom_csv_writer = csv.writer(edge_geom_csv_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        
        #write the headers to the node, edge and edge_geometry csv files
        node_csv_writer.writerow(node_table_fieldnames)
        edge_csv_writer.writerow(edge_table_fieldnames)
        edge_geom_csv_writer.writerow(edge_geometry_table_fieldnames)
            
        #this OK to leave in the CSV writing version of the function because we need the correct GraphID inside each CSV file
        graph_id = self.update_graph_table(network)
        
        if graph_id == None:
            raise Error('Could not load network from Graphs table.')
                
        #defines the 'base' fields for each table type (as is seen in the schema)
        node_fields = {'GraphID':ogr.OFTInteger}  
        edge_fields = {'Node_F_ID':ogr.OFTInteger, 'Node_T_ID':ogr.OFTInteger, 
                  'GraphID':ogr.OFTInteger, 'Edge_GeomID':ogr.OFTInteger}
        
        
        #to detect first edge
        first_edge = False
        
        #assign 1 as default starting id for nodes and edges
        current_node_id = 1
        current_edge_id = 1
        
        #reset the dictionaries storing the relevant data
        #GraphID .. .. .. geom
        node_from_attrs = []
        #GraphID .. .. .. geom
        node_to_attrs = []
        #Node_F_ID, Node_T_ID, GraphID, .. .. .., Edge_GeomID, EdgeID
        edge_attrs = []
        #GeomID, geom
        edge_geometry_attrs = []
        
        #to store records of all
        node_ids = []
        node_coords = []
        
        from_check = False
                
        #loop all edges in the network
        for e in G.edges(data=True):  
            
            #get the data for the current edge in the network
            data = G.get_edge_data(*e)                                    
            geom = self.netgeometry(e, data)

            node_from_geom = self.netgeometry(e[0], G.node[e[0]])             
            node_from_geom_wkt = ogr.Geometry.ExportToWkt(node_from_geom)               
            
            node_to_geom = self.netgeometry(e[1], G.node[e[1]])              
            node_to_geom_wkt = ogr.Geometry.ExportToWkt(node_to_geom)
                        
            #get point count for linestring
            n = geom.GetPointCount()
            
            #from node geometry for csv file            
            node_from_geom_wkt_final = 'srid=%s;%s' % (srs, node_from_geom_wkt)            
            
            #to node geometry for csv file            
            node_to_geom_wkt_final = 'srid=%s;%s' % (srs, node_to_geom_wkt)
            
            #increment current node id if not first edge
            if first_edge == True:
               current_node_id = current_node_id + 1
            
            #test if first edge
            if first_edge == False:        
                
                #add the edge table attributes to the edge table that are not in edge_fields
                edge_attrs_test = self.add_attribute_fields(self.lyredges, e[2], edge_fields)
                
                #loop until you find a node with a populated list of attributes
                for e_ in G.edges(data=True):
                    if len(G.node[e_[1]]) > 0:
                        #add the node table attributes to the node table that are not in node_fields
                        node_attrs_test = self.add_attribute_fields(self.lyrnodes, G.node[e_[1]], node_fields)
                        break;
                
                first_edge = True
                
        
            ##dealing with from nodes            
            node_from_attrs = []
            
            #perform check to see if node already exists
            if node_from_geom_wkt in node_coords:
                #from node already exists
                node_from_id = (node_ids[node_coords.index(node_from_geom_wkt)])                
                from_check = False
            else:                 
                #GraphID
                node_from_attrs.append(graph_id)        
                node_from_id = current_node_id                
                node_ids.append(node_from_id)
                node_coords.append(node_from_geom_wkt)
                current_node_id = node_from_id
                from_check = True            
                ######BIG CHANGE                            
                node_from_attrs.append(node_from_geom_wkt_final)                        
                node_from_attrs.append(node_from_id)
                
                ######BIG CHANGE    
                if len(G.node[e[0]]) > 0:            
                    #assign attributes related from the node from 
                    for key, node_from_data in G.node[e[0]].iteritems():                     
                        if (key != 'Json' and key != 'Wkt' and key != 'Wkb' 
                            and key != 'ShpName'):                     
                            node_from_attrs.append(node_from_data)
                #if there are no attributes, just fill up the array with empty values
                else:
                    for item in node_table_specific_fieldnames:
                        node_from_attrs.append(None)
            
            
            ##dealing with to nodes        
            node_to_attrs = []
            
            #perform check to see if node already exists
            if node_to_geom_wkt in node_coords:      
                #to node already exists
                node_to_id = (node_ids[node_coords.index(node_to_geom_wkt)])                   
            else:
                 #GraphID
                node_to_attrs.append(graph_id)
                if from_check == True:
                    node_to_id = current_node_id + 1               
                else:
                    node_to_id = current_node_id
                from_check = False                
                node_ids.append(node_to_id)
                node_coords.append(node_to_geom_wkt)
                current_node_id = node_to_id
                ######BIG CHANGE                    
                node_to_attrs.append(node_to_geom_wkt_final)    
                node_to_attrs.append(node_to_id)
                
                ######BIG CHANGE    
                if len(G.node[e[1]]) > 0:
                    #assign attributes related to the node to
                    for key, node_to_data in G.node[e[1]].iteritems():                
                        if (key != 'Json' and key != 'Wkt' and key != 'Wkb' 
                            and key != 'ShpName'):                                    
                            node_to_attrs.append(node_to_data)
                #if there are no attributes, just fill up the array with empty values
                else:
                    for item in node_table_specific_fieldnames:
                        node_to_attrs.append(None)
            
            
            edge_attrs = []
            #Node_F_ID
            edge_attrs.append(node_from_id)
            #Node_T_ID
            edge_attrs.append(node_to_id)
            #GraphID
            edge_attrs.append(graph_id)
            #Edge_GeomID
            edge_attrs.append(current_edge_id)
            #EdgeID
            edge_attrs.append(current_edge_id)
            
            #dealing with edge attributes ##NEW
            for edge_table_specific_key in edge_table_specific_fieldnames:                
                if data.has_key(edge_table_specific_key):                    
                    edge_attrs.append(data[edge_table_specific_key])
                else:
                    edge_attrs.append(None)
                            
            
            #import json
            edge_geom = self.netgeometry(e, data)
            edge_geom_wkt = ogr.Geometry.ExportToWkt(edge_geom)                        
            
            edge_geometry_attrs = []
            
            #geom                        
            edge_geom_wkt_final = 'srid=%s;%s' % (srs, str(edge_geom_wkt))
            edge_geometry_attrs.append(edge_geom_wkt_final)
            
            #GeomID
            edge_geometry_attrs.append(current_edge_id)
            
            #increment the edge id
            current_edge_id = current_edge_id + 1#self.pgnet_edge(edge_attrs, edge_geom)            
            
            if ((len(node_from_attrs) == 0) and (len(node_to_attrs) == 0)):
                current_node_id = current_node_id - 1
            
            if len(node_from_attrs) > 0:                   
                #need to write the contents of the node_from_attrs to the node table
                node_csv_writer.writerow(node_from_attrs)
            
            if len(node_to_attrs) > 0:                            
                #need to write the contents of the node_to_attrs to the node table
                node_csv_writer.writerow(node_to_attrs)
            
            #need to write the contents of the edge_geometry_attrs to the edge_geometry table
            edge_geom_csv_writer.writerow(edge_geometry_attrs)
            
            #need to write the contents of the edge_attrs to the edge table
            edge_csv_writer.writerow(edge_attrs)
                                    
        del node_ids
        del node_coords
        
        #close csv files
        node_csv_file.close()
        edge_geom_csv_file.close()
        edge_csv_file.close()
                
        #checking capitals for table names        
        matches = re.findall('[A-Z]', self.prefix)
        
        if len(matches) > 0:
            tblnodes = '"%s"' % self.tblnodes
            tbledge_geom = '"%s"' % self.tbledge_geom
            tbledges = '"%s"' % self.tbledges            
        else:
            tblnodes = self.tblnodes
            tbledge_geom = self.tbledge_geom
            tbledges = self.tbledge
        
        #load the nodes
        node_load_sql_from_csv = "COPY %s FROM '%s' DELIMITERS ',' CSV HEADER; " % (tblnodes, node_csv_filename)                    
        self.conn.ExecuteSQL(node_load_sql_from_csv)
        
        #load the edge geometry
        edge_geometry_load_sql_from_csv = "COPY %s FROM '%s' DELIMITERS ',' CSV HEADER; " % (tbledge_geom, edge_geom_csv_filename)                    
        self.conn.ExecuteSQL(edge_geometry_load_sql_from_csv)
        
        #load the edges
        edge_sql_from_csv = "COPY %s FROM '%s' DELIMITERS ',' CSV HEADER; " % (tbledges, edge_csv_filename)                    
        self.conn.ExecuteSQL(edge_sql_from_csv)
                
        nisql(self.conn).create_node_view(self.prefix)            
        nisql(self.conn).create_edge_view(self.prefix)
