#!/usr/bin/env  python
# -*- coding: utf-8 -*-
"""
--------
nx_pgnet - NetworkX PostGIS network IO module (PostGIS network schema).
--------
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

------------
Introduction
------------
NetworkX is a python library for graph analysis. Using edge and node 
attribution it can be used for spatial network analysis (with geography stored 
as node/edge attributes). This module supports the use of NetworkX for the
development of network analysis of spatial networks stored in a PostGIS 
spatial database by acting as an interface to a predefined table structure 
(the schema) in a PostGIS database from NetworkX Graph classes.

--------------
PostGIS Schema
--------------
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
        Holds interdependencies between networks. Not currently supported.
        
    - Interdependency_Edges:
        Holds interdependency geometry. Not currently supported.

----------------
Module structure    
----------------
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
        Note: do not use this class unless you know what you are
        doing! Use the higher-level read/write functions results in less chance
        of breaking your networks.
        
    - errors:
        Class containing error catching, reporting and logging methods. 
        Note: Not yet implemented.

Detailed documentation for each class can be found below contained in class 
document strings. The highest level functions for reading and writing data are:

    Read:    
    nx_pgnet.read().pgnet()
    Reads a network from PostGIS network schema into a NetworkX graph instance.
    
    Write:
    nx_pgnet.write().pgnet()
    Writes a NetworkX graph instance to PostGIS network schema tables.
    
--------------------
Database connections
--------------------
Connections to PostGIS are created using the OGR simple feature library and are
passed to the read() and write() classes. See http://www.gdal.ogr/ogr

Connections are mutually exclusive between read() and write() and are contained 
within each class (i.e. all methods within those classes inherit the :
connection), although you can of course read and write to the same database. 
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

Reading a network from PostGIS schema to a NetworkX graph instance:
    
    import nx_pgnet
    import osgeo.ogr as ogr
    
    # Create a connection
    conn = ogr.Open("PG: host='127.0.0.1' dbname='database' user='postgres'
                    password='password'")

    # Read a network
    # Note 'my_network' is the name of the network stored in the 'Graphs' table
    
    network = nx_pgnet.read(conn).pgnet('my_network')    

Writing a NetworkX graph instance to a PostGIS schema:
    
    # Write the network to the same database but under a different name.
    # Note 'EPSG' id the epsg code for the output network geometry.
    # Note if 'overwrite=True' then an existing network in the database of the 
    # same name will be overwritten.
    
    epsg = 27700
    nx_pgnet.write(conn).pgnet(network, 'new_network', epsg, overwrite=False)

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

David Alderson, Alistair Ford, Stuart Barr, Craig Robson.

-------
License
-------
This software is released under a BSD style license. See LICENSE.TXT or type
nx_pgnet.license() for full details.

-------
Credits
-------
Tomas Holderness, David Alderson, Alistair Ford, Stuart Barr and Craig Robson.

-------
Contact
-------
tom.holderness@ncl.ac.uk
www.staff.ncl.ac.uk/tom.holderness

-----------------
Development Notes
-----------------
Where possible the PEP8/PEP257 style guide has been implemented.
To do:
    1) Check attribution of nodes from schema and non-schema sources 
    (blank old id fields are being copied over).
    2) Error  / warnings module.
    3) Investigate bug: "Warning 1: Geometry to be inserted is of type 
    Line String, whereas the layer geometry type is Multi Line String.
    Insertion is likely to fail!"
    3) Multi and directed graph support.
    4) 3D geometry support.
    
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
        
        result = 0
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
        # To do: error checking
        # what to return here?
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
        return viewname
        
    def create_edge_view(self, prefix):
        '''Wrapper for ni_create_edge_view function.
        
        Creates a view containing edge attributes and edge geometry values. 
        Requires network name ('prefix').
        
        Returns view name if succesful.'''
        
        ##viewname = prefix+'_Edges_View'        
        ##edge_tbl_name = prefix+'_Edges'
        ##edge_geom_tbl_name = prefix+'_Edge_Geometry'
        ### Get SRS from Edge_Geometry table for the view
        ##epsg = 27700
        ### Create view from join
        ##sql = 'CREATE OR REPLACE VIEW %s AS SELECT * FROM "%s", "%s" WHERE \
        ##"EdgeID" = "GeomID"' % (viewname, edge_geom_tbl_name, edge_tbl_name)
        ##self.conn.ExecuteSQL(sql)
        ### Add view to geometry_columns table
        ####sql = ("SELECT * FROM ni_add_geometry_columns ('%s', %i);"%(viewname,
        ####       epsg))
        ####self.conn.ExecuteSQL(sql)
        viewname = None
        sql = "SELECT * FROM ni_create_edge_view('%s')" % prefix
        ##print sql
        for row in self.conn.ExecuteSQL(sql):
            viewname = row.ni_create_edge_view
            
            
        return viewname
    
    def add_graph_record(self, prefix, directed=False, multipath=False):
        '''Wrapper for ni_add_graph_record function.
        
        Creates a record in the Graphs table based on graph attributes.
        
        Returns new graph id of succesful.'''  
    
        sql = ("SELECT * FROM ni_add_graph_record('%s', FALSE, FALSE);" % 
                (prefix))
                
        result = self.conn.ExecuteSQL(sql)
        ##for row in self.conn.ExecuteSQL(sql):
        ##    result = row.ni_add_graph_record
        return result
        
    def node_geometry_equaility_check(self, prefix, wkt, srs):
        '''Wrapper for ni_node_geometry_equality_check function.
        
        Checks if geometry already eixsts in nodes table.
        
        If not, returns None'''
        
        sql = ("SELECT * FROM ni_node_geometry_equality_check('%s', '%s', %s);" 
                % (prefix, wkt, srs))
        result = None
        for row in self.conn.ExecuteSQL(sql):
            
            result = row.ni_node_geometry_equality_check
        return result

    def edge_geometry_equaility_check(self, prefix, wkt, srs):
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

    def pgnet_edges(self, graph, geography=True):
        '''Reads edges from edge and edge_geometry tables and add to graph.'''
        print 'reading edges'
        # Join Edges and Edge_Geom
        edge_tbl_view = nisql(self.conn).create_edge_view(self.prefix)
        # Get lyr by name
        lyr = self.conn.GetLayerByName(edge_tbl_view)
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
            # Multiline geometry so split into line segments
            if (ogr.Geometry.GetGeometryName(geom) ==
                'MULTILINESTRING'):
                for line in geom:
                    # Get points in line
                    n = line.GetPointCount()
                    # Get the attributes (akin to nx_shp)
                    attributes["Wkb"] = ogr.Geometry.ExportToWkb(line)
                    attributes["Wkt"] = ogr.Geometry.ExportToWkt(line)
                    attributes["Json"] = ogr.Geometry.ExportToJson(line)
                    graph.add_edge(attributes['Node_F_ID'], 
                                 attributes['Node_T_ID'], attributes)
            # Line geometry
            elif (ogr.Geometry.GetGeometryName(geom) ==
                'LINESTRING'):
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
        sql = ('SELECT * FROM	"Graphs" WHERE "GraphName" = \'%s\';' % prefix)
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
            raise Error("Can't find network in Graph table")
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
            _from, _to = key[0], key[1]
            geom.SetPoint(0, *_from)
            geom.SetPoint(1, *_to)
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

        ##if result is None:
        sql = ('SELECT "GraphID" FROM "Graphs" ORDER BY "GraphID" DESC\
                    LIMIT 1;')
        GraphID = None
        for row in self.conn.ExecuteSQL(sql):
            GraphID = row.GraphID

        ##else: 
        # throw an error?
        ##  print 'add_graph_record broke!'

        return GraphID
        
    def pgnet_edge(self, edge_attributes, edge_geom):
        '''Write an edge to Edge and Edge_Geometry tables.'''
        ##print "pg net edge"
        edge_wkt = edge_geom.ExportToWkt()
        # Get table definitions        
        featedge = ogr.Feature(self.lyredges.GetLayerDefn())
        featedge_geom = ogr.Feature(self.lyredge_geom.GetLayerDefn())
       
        # Test for geometry existance       
        GeomID = nisql(self.conn).edge_geometry_equaility_check(self.prefix, 
                        edge_wkt, self.srs)
        ##print 'tested for geom equality'                
        if GeomID == None: # Need to create new geometry:
            ##print 'setting geom'
            featedge_geom.SetGeometry(edge_geom)
            
            ##for field, data in edge_attributes.iteritems():
             ##   featedge_geom.SetField(field, data)
            ##print 'creating feature'
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
        # Does the node already exist?
            # If yes return NodeID
        # Else: Insert node
        ## OGR BUG? GIS Stackexchange question: http://t.co/G6u20Y6
        #featnode = ogr.Feature(self.lyrnodes.GetLayerDefn())
        featnode = ogr.Feature(self.lyrnodes_def)
        node_wkt = node_geom.ExportToWkt()
        NodeID = nisql(self.conn).node_geometry_equaility_check(self.prefix,
                        node_wkt,self.srs)
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
        # First create network tables in database
        
        self.prefix = tablename_prefix        
        self.tbledges = tablename_prefix+'_Edges'
        self.tblnodes = tablename_prefix+'_Nodes'
        self.tbledge_geom = tablename_prefix+'_Edge_Geometry'
        self.srs = srs

        result = nisql(self.conn).create_network_tables(self.prefix, self.srs, 
                        directed, multigraph)
        if result == 0:
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
            #print 'edge data', data
            edge_geom = self.netgeometry(e, data)
            # Insert the start node
            node_attrs = self.create_attribute_map(self.lyrnodes, G.node[e[0]], 
                                                   node_fields)
            node_attrs['GraphID'] = graph_id 
            # Check attribution of nodes?
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
        
