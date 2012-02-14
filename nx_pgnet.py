#!/usr/bin/env  python
# -*- coding: utf-8 -*-
"""
nx_pgnet - Module for NetworkX read/write of PostGIS tables.

Reads/writes both standard tables and tables within network schema, see network
schema documentation for more details.

Development notes.

1) Based on nx_pg_ncl.py (developmental version).

2) Outputs do not currently specify CRS/EPSG. Use a friendly GIS (QGIS) to set
on load.

3) Have tried to adhere to Python PEP8 style as much as possible.

4) Included main function is just for development and will be removed.

"""
__author__ = "Tom Holderness"
__created__ = "Thu Jan 19 15:55:13 2012"
__version__ = "0.2.1"

import sys
import networkx as nx
import osgeo.ogr as ogr
import nx_pgnet_sql

#for testing
import test_suite_nx_pgnet

# Ask ogr to use Python exceptions rather than stderr messages.
##ogr.UseExceptions()

#To do:
    # Add src_id/SRS/EPSG support
    # Update delete function (fix Graphs table)- Dave
    # Talk to Dave about boolean pg types in Graphs table.
    # Update create function to append to geometry table - Dave
    # Read function from schema to networkx.
    # Bring classes into one module

class nisql:
    '''Class with wrapper functions for postgis network functions. As a user 
    don't access these functions directly. Use the complete methods in 
    read/write classes.'''
    
    def __init__(self, db_conn):
        self.conn = db_conn
    
    def create_network_tables(self, prefix, epsg):
        '''Takes database connection, graph name and srid and creates network 
        tables (requires schema in database) returns true if succesful.'''
        # Create network tables
        sql = ("SELECT * FROM ni_create_network_tables ('%s', %i);" % (prefix,
               epsg))
        result = 0
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
        '''Takes network prefix and creates a view containing edge attributes 
        and edge_geometry values. Returns view name if succesful.'''
        '''
        viewname = prefix+'_Edges_View'        
        edge_tbl_name = prefix+'_Edges'
        edge_geom_tbl_name = prefix+'_Edge_Geometry'
        # Get SRS from Edge_Geometry table for the view
        epsg = 27700
        # Create view from join
        sql = 'CREATE OR REPLACE VIEW %s AS SELECT * FROM "%s", "%s" WHERE \
        "EdgeID" = "GeomID"' % (viewname, edge_geom_tbl_name, edge_tbl_name)
        self.conn.ExecuteSQL(sql)
        # Add view to geometry_columns table
        ##sql = ("SELECT * FROM ni_add_geometry_columns ('%s', %i);" % (viewname,
        ##       epsg))
        ##self.conn.ExecuteSQL(sql)
        '''
        viewname = None
        
        sql = "SELECT * FROM ni_create_edge_view('%s')" % prefix
        for row in self.conn.ExecuteSQL(sql):
            viewname = row.ni_create_edge_view 
        return viewname
    
    def add_graph_record(self, prefix, directed=False, multipath=False):
        '''Takes graph attributes and creates a record in the graph table, if 
        result none (i.e. no errors) returns new graph id'''  
    
        sql = ("SELECT * FROM ni_add_graph_record('%s', FALSE, FALSE);" % 
                (prefix))
                
        result = self.conn.ExecuteSQL(sql)
        '''
        for row in self.conn.ExecuteSQL(sql):
            result = row.ni_add_graph_record
        '''
        return result
        
    def node_geometry_equaility_check(self, prefix, wkt, srs):
        '''Takes table prefix and geometry as Wkt and checks to see if 
        geometry already eixsts in nodes table, if not return None'''
        
        sql = ("SELECT * FROM ni_node_geometry_equality_check('%s', '%s', %s);" % 
                (prefix, wkt, srs))
        result = None
        print sql
        for row in self.conn.ExecuteSQL(sql):
            
            result = row.ni_node_geometry_equality_check
        return result

    def edge_geometry_equaility_check(self, prefix, wkt, srs):
        '''Takes table prefix and geometry as Wkt and checks to see if 
        geometry already eixsts in nodes table, if not return None'''
        
        sql = ("SELECT * FROM ni_edge_geometry_equality_check('%s', '%s', %s);" % 
                (prefix, wkt, srs))
        result = None
        for row in self.conn.ExecuteSQL(sql):
            result = row.ni_edge_geometry_equality_check
        return result       
    
    def delete_network(self, prefix):
        '''Takes table prefix and uses ni_delete_network function to delete
        associated network tables.'''
        
        sql = ("SELECT * FROM ni_delete_network('%s');" % (prefix))
        
        result = None
        for row in self.conn.ExecuteSQL(sql):
            result = row.ni_delete_network
        return result

class read:
    '''Class with methods to read and build networks from either non-network
    vector line table or from schema defined network tables.'''

    def __init__(self, db_conn):
        self.conn = db_conn
    
    def getfieldinfo(self, lyr, feature, flds):
        '''Get information about fields (borrowed from nx_shp.py'''
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
        '''Reads edges from edge and edge_geometry tables and add to graph.'''
        
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
            f = lyr.GetFeature(findex+1)
            if f is None:
                pass # Catch any returned features which are None. 
            else:
                # Read edge attrs.
                flddata = self.getfieldinfo(lyr, f, flds)
                attributes = dict(zip(flds, flddata))
                #attributes['network'] = network_name
                geom = f.GetGeometryRef()
                graph.add_node((attributes['NodeID']), attributes)
     
    def graph_table(self, prefix):
        '''Reads the standard attributes of a sepcified graph from the graph 
             table. Returns attributes as a dict of variables.'''  
        
        graph = None
        sql = ('SELECT * FROM	"Graphs" WHERE "GraphName" = \'%s\';' % prefix)
        for row in self.conn.ExecuteSQL(sql):
             graph = row.items()

        return graph
    
    def pgnet(self, prefix):
        '''Read postgis graph tables as defined by schema and returns networkx
            graph.'''
        
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

        return G

class write:
    ''''Class with methods to write networks to either non-network
    vector line and points tables or to schema defined network tables.'''
    
    def __init__(self, db_conn):
        self.conn = db_conn

    def getlayer(self, tablename):
        '''Get a PostGIS table by name and return as OGR layer,
            else return None. '''
    
        sql = "SELECT * from pg_tables WHERE tablename = '%s'" % tablename 
        
        for row in self.conn.ExecuteSQL(sql):
            if row.tablename is None:
                return None
            else:
                return self.conn.GetLayerByName(tablename)           
    
    def netgeometry(self, key, data):
        '''Create OGR geometry from NetworkX Graph Wkb/Wkt attributes.
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
        '''wrapper for OGR CreateFeature to create a feature in specified 
        layer with geometry and attributes.'''
        
        feature = ogr.Feature(lyr.GetLayerDefn())
        if attributes is not None:
            for field, data in attributes.iteritems(): 
                feature.SetField(field, data)
        if geometry is not None:
            feature.SetGeometry(geometry)
        lyr.CreateFeature(feature)
        feature.Destroy()

    def create_attribute_map(self, lyr, g_obj, fields):
        '''Helper method to build map of attribute field names, data and OGR
        data types. Accepts graph object (either node or edge), fields and 
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
        '''Update graph table, return new graph ID.'''
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
        '''Method to write an edge to edge tables as defined by schema.'''
        edge_wkt = edge_geom.ExportToWkt()
        # Get table definitions        
        featedge = ogr.Feature(self.lyredges.GetLayerDefn())
        featedge_geom = ogr.Feature(self.lyredge_geom.GetLayerDefn())
       
        # Test for geometry existance       
        #GeomID = nx_pgnet_sql.ni_edge_geometry_equaility(self.conn, self.prefix, edge_wkt)
        GeomID = nisql(self.conn).edge_geometry_equaility_check(self.prefix, edge_wkt, self.srs)
        if GeomID == None: # Need to create new geometry:
            
            featedge_geom.SetGeometry(edge_geom)
            
            ##for field, data in edge_attributes.iteritems():
             ##   featedge_geom.SetField(field, data)
            self.lyredge_geom.CreateFeature(featedge_geom)
            #Get created edge_geom primary key (GeomID)
            sql = ('SELECT "GeomID" FROM "%s" ORDER BY "GeomID" DESC LIMIT 1;' % 
                                                            self.tbledge_geom)
            for row in self.conn.ExecuteSQL(sql):
                GeomID = row.GeomID
                # Append the GeomID to the edges attributes 
                
        edge_attributes['Edge_GeomID'] = GeomID
        
        #Attributes to edges table
        for field, data in edge_attributes.iteritems():
            featedge.SetField(field, data)
        self.lyredges.CreateFeature(featedge)
        
    def pgnet_node(self, node_attributes, node_geom):
        '''Write NetworkX node to node table as defined by schema. Return the
        NodeID as assigned by the database
        '''
        # Does the node already exist?
            # If yes return NodeID
        # Else: Insert node
        ## OGR BUG? GIS Stackexchange question: http://t.co/G6u20Y6
        #featnode = ogr.Feature(self.lyrnodes.GetLayerDefn())
        featnode = ogr.Feature(self.lyrnodes_def)
        node_wkt = node_geom.ExportToWkt()
        NodeID = nisql(self.conn).node_geometry_equaility_check(self.prefix,node_wkt,self.srs)
        if NodeID == None: # Need to create new geometry:
            featnode.SetGeometry(node_geom)
            for field, data in node_attributes.iteritems():
                featnode.SetField(field, data)
            self.lyrnodes.CreateFeature(featnode)
            sql = ('SELECT "NodeID" FROM "%s" ORDER BY "NodeID" DESC LIMIT 1;' % 
                                                            self.tblnodes)
            for row in self.conn.ExecuteSQL(sql):
                NodeID = row.NodeID
        
        return NodeID

    def pgnet(self, network, tablename_prefix, srs, overwrite=False):
        '''Write NetworkX (with geom) to PostGIS graph tables as defined by schema.
        
        Will also update graph table.
    
        Note that schema constrains must be applied in database - there are no 
        checks for database errors here!
        '''
        # First create network tables in database
        
        self.prefix = tablename_prefix        
        self.tbledges = tablename_prefix+'_Edges'
        self.tblnodes = tablename_prefix+'_Nodes'
        self.tbledge_geom = tablename_prefix+'_Edge_Geometry'
        self.srs = srs

        result = nisql(self.conn).create_network_tables(self.prefix,self.srs)
        if result == 0:
            if overwrite is True:
                nisql(self.conn).delete_network(self.prefix)
                nisql(self.conn).create_network_tables(self.prefix,self.srs)
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
                  
        for e in G.edges(data=True):
            data = G.get_edge_data(*e)
            #print 'edge data', data
            edge_geom = self.netgeometry(e, data)
            
            # Insert the start node
            node_attrs = self.create_attribute_map(self.lyrnodes,G.node[e[0]], 
                                                   node_fields)
            node_attrs['GraphID'] = graph_id 
            node_geom = self.netgeometry(e[0], node_attrs)            
            node_id = self.pgnet_node(node_attrs, node_geom)
            G[e[0]][e[1]]['Node_F_ID'] = node_id
            
            # Insert the end node
            node_attrs = self.create_attribute_map(self.lyrnodes,G.node[e[1]], 
                                                   node_fields)            
            node_attrs['GraphID'] = graph_id           
            node_geom = self.netgeometry(e[1], node_attrs)            
            node_id = self.pgnet_node(node_attrs, node_geom)
            G[e[0]][e[1]]['Node_T_ID'] = node_id

            # Set graph id.
            G[e[0]][e[1]]['GraphID'] = graph_id
            
            edge_attrs = self.create_attribute_map(self.lyredges, e[2], edge_fields)
            self.pgnet_edge(edge_attrs, edge_geom) 
            
            #self.lyredge_geom, self.lyredges, self.lyrnodes = None, None, None
            
if __name__ == "__main__":
    test_suite_nx_pgnet.main()