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
<<<<<<< HEAD
__author__ = "Tom Holderness"
__created__ = "Thu Jan 19 15:55:13 2012"
__year__ = "2011"
__version__ = "0.2"
=======
__created__ = "January 2012"
__version__ = "0.9.2"
__author__ = """\n""".join(['Tomas Holderness (tom.holderness@ncl.ac.uk)',
	                            'David Alderson (david.alderson@ncl.ac.uk)',
	                            'Alistair Ford (a.c.ford@ncl.ac.uk)',
                                 'Stuart Barr (stuart.barr@ncl.ac.uk)'])
__license__ = 'BSD style. See LICENSE.TXT'                                
>>>>>>> nx_pg_sql_create

import networkx as nx
import osgeo.ogr as ogr

# Ask ogr to use Python exceptions rather than stderr messages.
##ogr.UseExceptions()
    
class net_error:
    '''Class to handle network IO errors. '''
    # Error class. To do
    def __init__(self):
        pass
    
    def connection_error(self):
        pass
    

class nisql:
    '''Contains wrappers for PostGIS network schema functions.
    
    Where possible avoid using this class directly. Uses the read and write
    classes instead.'''
    
    def __init__(self, db_conn):
        '''Setup connection to be inherited by methods.'''
        self.conn = db_conn
    
    def create_network_tables(self, prefix, epsg):
        '''Wrapper for ni_create_network_tables function.
        
        Creates empty network schema PostGIS tables.
        Requires graph 'prefix 'name and srid to create empty network schema
        PostGIS tables.
        
        Returns True if succesful.'''
        
        # Create network tables
        sql = ("SELECT * FROM ni_create_network_tables ('%s', %i);" % (prefix,
               epsg))
        result = 0
        print sql
        for row in self.conn.ExecuteSQL(sql):
            result = row.ni_create_network_tables
        
        # Add geometry column
        sql = ("SELECT * FROM ni_add_geometry_columns ('%s', %i);" % (prefix,
               epsg))
        self.conn.ExecuteSQL(sql)
        # Add foreign key constraints
        sql = ("SELECT * FROM ni_add_fr_constraints ('%s');" % (prefix,))
        self.conn.ExecuteSQL(sql)        
        
        # To do: error checking
        # what to return here?
        return result
        
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
    
    def getfieldinfo(self, lyr, feature, flds):
        '''Get information about fields from a table (as OGR feature).'''
        f = feature
        return [f.GetField(f.GetFieldIndex(x)) for x in flds]

    def pgnet_edges(self, graph):
        '''Reads edges from edge and edge_geometry tables and add to graph.'''
        
        # Join Edges and Edge_Geom
        edge_tbl_view = nisql(self.conn).create_edge_view(self.prefix)
        # Get lyr by name
        #edge_tbl_view = "lightrail_baseline_edges_view"
        lyr = self.conn.GetLayerByName(edge_tbl_view)
        # Get fields
        flds = [x.GetName() for x in lyr.schema]
        # Get the number of features in the layer
        for findex in xrange(lyr.GetFeatureCount()):
            # Get a specific feature
            f = lyr.GetFeature(findex+1)
            if f is None:
                pass # Catch any returned features which are None. 
            else:
                # Read edge attrs.
                flddata = self.getfieldinfo(lyr, f, flds)
                attributes = dict(zip(flds, flddata))
                #attributes['network'] = network_name
                geom = f.GetGeometryRef()
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
                    attributes["Json"] = ogr.Geometry.ExportToJson(
                                                                geom) 
                    graph.add_edge(attributes['Node_F_ID'], 
                                     attributes['Node_T_ID'], attributes)
    
    def pgnet_nodes(self, graph):
        '''Reads nodes from node table and add to graph.'''
        
        # Join Edges and Edge_Geom
        ##edge_tbl_view = nisql(self.conn).create_edge_view(self.prefix)
        # Get lyr by name
        node_tbl = "LightRail_Baseline_Nodes"
        lyr = self.conn.GetLayerByName(node_tbl)
        # Get fields
        flds = [x.GetName() for x in lyr.schema]
        # Get the number of features in the layer
        for findex in xrange(lyr.GetFeatureCount()):
            # Get a specific feature
            #f = lyr.GetFeature(findex+1)
            #print 'findex',findex
            f = lyr.GetFeature(findex)
            if f is None:
                pass # Catch any returned features which are None. 
            else:
                # Read edge attrs.
                flddata = self.getfieldinfo(lyr, f, flds)
                attributes = dict(zip(flds, flddata))
                #attributes['network'] = network_name
                geom = f.GetGeometryRef()
                ##if geom != None:
                attributes["Wkb"] = ogr.Geometry.ExportToWkb(geom)
                attributes["Wkt"] = ogr.Geometry.ExportToWkt(geom)
                graph.add_node((attributes['NodeID']), attributes)
     
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
            print "Error reading Graph table, does specified network exist?"
            exit(1)
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
        print G.node[1]
        print G.node[2]
        return G

class write:
    '''Class to write NetworkX instance to PostGIS network schema tables.'''
    
    def __init__(self, db_conn):
        '''Setup connection to be inherited by methods.'''
        self.conn = db_conn

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
        
<<<<<<< HEAD
    def write_pg(self, network, tablename_prefix, overwrite=False):
        '''Function to write Network with geometry to PostGIS edges and node 
        tables.'''
        G = network
        tbledges = tablename_prefix+'_edges'
        tblnodes = tablename_prefix+'_nodes'
    
        if overwrite is True:
          self.conn.DeleteLayer(tbledges)
          self.conn.DeleteLayer(tblnodes)
          
        edges = self.conn.CreateLayer(tbledges, None, ogr.wkbLineString)
        nodes = self.conn.CreateLayer(tblnodes, None, ogr.wkbPoint)
        
        for n in G:
            data = G.node[n].values() or [{}]
            g = self.netgeometry(n, data[0])
            self.create_feature(nodes, None, g)
        
        fields = {}
        attributes = {}
        OGRTypes = {int:ogr.OFTInteger, str:ogr.OFTString, float:ogr.OFTReal}
        for e in G.edges(data=True):
            data = G.get_edge_data(*e)
            g = self.netgeometry(e, data)
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
            
            self.create_feature(edges, attributes, g)
    
        nodes, edges = None, None 
        
=======
        Accepts graph object (either node or edge), fields and 
        returns attribute dictionary.'''
>>>>>>> nx_pg_sql_create

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
        edge_wkt = edge_geom.ExportToWkt()
        # Get table definitions        
        featedge = ogr.Feature(self.lyredges.GetLayerDefn())
        featedge_geom = ogr.Feature(self.lyredge_geom.GetLayerDefn())
       
        # Test for geometry existance       
        GeomID = nisql(self.conn).edge_geometry_equaility_check(self.prefix, 
                        edge_wkt, self.srs)
        if GeomID == None: # Need to create new geometry:
            
            featedge_geom.SetGeometry(edge_geom)
            
            ##for field, data in edge_attributes.iteritems():
             ##   featedge_geom.SetField(field, data)
            self.lyredge_geom.CreateFeature(featedge_geom)
            #Get created edge_geom primary key (GeomID)
            sql = ('SELECT "GeomID" FROM "%s" ORDER BY "GeomID" DESC LIMIT 1;'
                    % self.tbledge_geom)
            for row in self.conn.ExecuteSQL(sql):
                GeomID = row.GeomID
                # Append the GeomID to the edges attributes 
                
        edge_attributes['Edge_GeomID'] = GeomID
        
        #Attributes to edges table
        for field, data in edge_attributes.iteritems():
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

    def pgnet(self, network, tablename_prefix, srs, overwrite=False):
        '''Write NetworkX instance to PostGIS network schema tables.
        
        Updates Graph table with new network.
    
        Note that schema constrains must be applied in database. 
        There are no checks for database errors here.
        '''
<<<<<<< HEAD
    
        G = network # Use G as network, convention from earlier code.
        ## Table name prefix not implemented yet        
        ##tbledges = tablename_prefix+'_edges'
        ##tblnodes = tablename_prefix+'_nodes'
        ##tbledge_geom = tablename_prefix+'edge_geometry'
        
        edge_geom = self.getlayer(tbledge_geom)
        edges = self.getlayer(tbledges)
        nodes = self.getlayer(tblnodes)    
    
        # For all the nodes add an index.
        # Warning! This will limit unique node index to sys.maxint 
        nid = 0
        fields = {}
        attributes = {}
        OGRTypes = {int:ogr.OFTInteger, str:ogr.OFTString, float:ogr.OFTReal}
        for n in G.nodes(data=True):
            G.node[n[0]]['NodeID'] = nid
            data = G.node[n[0]]
            g = self.netgeometry(n[0], data)
            # Loop through data in nodes
            for key, data in n[1].iteritems():
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
                         nodes.CreateField(newfield)
                         attributes[key] = data
                      # Create dict of single feature's attributes
                      else:
                         attributes[key] = data
            self.create_feature(nodes, attributes,g)
            nid += 1
        # Repeat similar operation for Edges (should put in function at some point!)
        edge_id_field = ogr.FieldDefn('EdgeID',ogr.OFTInteger)
        edge_geom.CreateField(edge_id_field)        
        
        fields = {}
        attributes = {}
        eid = 0 # edge_id
=======
        # First create network tables in database
        
        self.prefix = tablename_prefix        
        self.tbledges = tablename_prefix+'_Edges'
        self.tblnodes = tablename_prefix+'_Nodes'
        self.tbledge_geom = tablename_prefix+'_Edge_Geometry'
        self.srs = srs

        result = nisql(self.conn).create_network_tables(self.prefix, self.srs)
        if result == 0:
            if overwrite is True:
                nisql(self.conn).delete_network(self.prefix)
                nisql(self.conn).create_network_tables(self.prefix, self.srs)
            else:
                print 'Network already exists, will now exit.'
                exit(0)

        G = network # Use G as network, networkx convention.
        
        graph_id = self.update_graph_table(network)     
        if graph_id == None:
            print 'GraphID not pulled from Graphs table, will now exit.'
            exit(1)
        
        self.lyredges = self.getlayer(self.tbledges)
        self.lyrnodes = self.getlayer(self.tblnodes)
        self.lyredge_geom = self.getlayer(self.tbledge_geom)  
        self.lyrnodes_def =  self.lyrnodes.GetLayerDefn()
        
        node_fields = {'GraphID':ogr.OFTInteger}  
        edge_fields = {'Node_F_ID':ogr.OFTInteger, 'Node_T_ID':ogr.OFTInteger, 
                  'GraphID':ogr.OFTInteger, 'Edge_GeomID':ogr.OFTInteger}
                  
>>>>>>> nx_pg_sql_create
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
