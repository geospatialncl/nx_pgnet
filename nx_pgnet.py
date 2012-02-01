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
__year__ = "2011"
__version__ = "0.2.1"

import sys
import networkx as nx
import osgeo.ogr as ogr

#for testing
import test_suite_nx_pgnet

# Ask ogr to use Python exceptions rather than stderr messages.
#ogr.UseExceptions()

#To do:
    # Fix write_pgnet edge and node ID - applied by DB?
    # Remove create table statements and apply as updates only (tables should 
    #   already exist)
    # Add write_pg function (from nx_pg) but integrated within class
    # Add src_id support
    # Build wrapper functions round Dave's plpgsql for create/drop graphs etc.

class read:
    '''Class with methods to read and build networks from either non-network
    vector line table or from schema defined network tables.'''

    def __init__(self, db_conn):
        self.conn = db_conn
    
    def getfieldinfo(self, lyr, feature, flds):
        '''Get information about fields (borrowed from nx_shp.py'''
        f = feature
        return [f.GetField(f.GetFieldIndex(x)) for x in flds]
    
    def read_pg(self, edges_tbl, nodes_tbl = None, directed=True):
        '''Read PostGIS vector line/point tables and return networkx graph.'''        
        # Create Directed graph to store output
        if directed is True:
            net = nx.DiGraph()
        else:
            net = nx.Graph()
        # Empty attributes dict
        for lyr in self.conn:
            if lyr.GetName() == edges_tbl or lyr.GetName() == nodes_tbl:
                sys.stdout.write("Reading features from %s\n" % lyr.GetName())
                flds = [x.GetName() for x in lyr.schema]
                # Get the number of features in the layer
                for findex in xrange(lyr.GetFeatureCount()):
                    # Get a specific feature
                    f = lyr.GetFeature(findex+1)
                    if f is None:
                        pass # Catch any returned features which are None. 
                    else:
                        flddata = self.getfieldinfo(lyr, f, flds )
                        attributes = dict(zip(flds, flddata))
                        attributes["TableName"] = lyr.GetName()
                        # Get the geometry for that feature
                        geom = f.GetGeometryRef()
                        
                        # Multiline geometry so split into line segments
                        if (ogr.Geometry.GetGeometryName(geom) ==
                            'MULTILINESTRING'):
                            for line in geom:
                                # Get points in line
                                n = line.GetPointCount()
                                # Get the attributes (akin to nx_shp)
                                attributes["Wkb"] = ogr.Geometry.ExportToWkb(
                                                                        line)
                                attributes["Wkt"] = ogr.Geometry.ExportToWkt(
                                                                        line)
                                attributes["Json"] = ogr.Geometry.ExportToJson(
                                                                        line)
                                net.add_edge(line.GetPoint_2D(0), 
                                             line.GetPoint_2D(n-1), attributes)
                        # Line geometry
                        elif (ogr.Geometry.GetGeometryName(geom) ==
                            'LINESTRING'):
                            n = geom.GetPointCount()
                            attributes["Wkb"] = ogr.Geometry.ExportToWkb(geom)
                            attributes["Wkt"] = ogr.Geometry.ExportToWkt(geom)
                            attributes["Json"] = ogr.Geometry.ExportToJson(
                                                                        geom) 
                            net.add_edge(geom.GetPoint_2D(0), 
                                             geom.GetPoint_2D(n-1), attributes)
                        # Point geometry                    
                        elif ogr.Geometry.GetGeometryName(geom) == 'POINT':
                            net.add_node((geom.GetPoint_2D(0)), attributes)
                        else:
                            raise (ValueError, 
                                   "PostGIS geometry type not supported.")
        return net        
    
    def read_pgnet(self, network_name):
        '''Read postgis graph tables as defined by schema and return networkx
            graph.'''
        pass

class write:
    ''''Class with methods to write networks to either non-network
    vector line and points tables or to schema defined network tables.'''
    
    def __init__(self, db_conn):
        self.conn = db_conn
        
    
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
            geom.SetPoint(0, *key)
        return geom
    
    def create_feature(self, lyr, attributes = None, geometry = None):
        '''Create an OGR feature in specified layer with geometry and 
            attributes.'''
        feature = ogr.Feature(lyr.GetLayerDefn())
        if attributes is not None:
            for field, data in attributes.iteritems(): 
                feature.SetField(field, data)
        if geometry is not None:
            feature.SetGeometry(geometry)
        lyr.CreateFeature(feature)
        feature.Destroy()
        
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

    def getlayer(self, tablename):
        '''Get a PostGIS table by name and return as OGR layer,
            else return None. '''
    
        sql = "SELECT * from pg_tables WHERE tablename = '%s'" % tablename 
        
        for row in self.conn.ExecuteSQL(sql):
            if row.tablename is None:
                return None
            else:
                return self.conn.GetLayerByName(tablename)                
                
    def update_graph_table(self, graph, graph_name, edge_table, node_table):
        '''Update graph table or create if doesn't exist with agreed schema.'''
        
        tblgraphs = self.getlayer('graphs')
        #ogr.UseExceptions()
        # tblgraphs doesn't exist so create with new features.
        # This is hard coded - should be reworked to be dynamic, similar style to..
            #...write_pg attributes)
        if tblgraphs is None:
            # tblgraphs is ogr.wkbNone (i.e. non-spatial)
            tblgraphs = self.conn.CreateLayer('graphs', None, ogr.wkbNone)
            Field_GraphName = ogr.FieldDefn('GraphName', ogr.OFTString)
            tblgraphs.CreateField(Field_GraphName)
            
            Field_Nodes = ogr.FieldDefn('Nodes', ogr.OFTString)
            tblgraphs.CreateField(Field_Nodes)    
        
            Field_Edges = ogr.FieldDefn('Edges', ogr.OFTString)
            tblgraphs.CreateField(Field_Edges)
            
            Field_Directed = ogr.FieldDefn('Directed', ogr.OFTInteger)
            tblgraphs.CreateField(Field_Directed)
        
            Field_MultiGraph = ogr.FieldDefn('MultiGraph', ogr.OFTString)
            tblgraphs.CreateField(Field_MultiGraph)
        # Now add the data. 
        feature = ogr.Feature(tblgraphs.GetLayerDefn())
        feature.SetField('GraphName', graph_name)
        feature.SetField('Nodes', edge_table)
        feature.SetField('Edges', node_table)
        if nx.is_directed(graph):
            feature.SetField('Directed', 1)
        else:
            feature.SetField('Directed', 0)
        # Multigraph still needs to be implemented.
        feature.SetField('MultiGraph', 0)
        # Create feature, clear pointer.
        tblgraphs.CreateFeature(feature)
        feature.Destroy()
    
    def write_pgnet_edge(self, edge_attributes, edge_geom):
        '''Method to write an edge to edge tables as defined by schema.'''
        
        # Get table definitions        
        featedge = ogr.Feature(self.lyredges.GetLayerDefn())
        featedge_geom = ogr.Feature(self.lyredge_geom.GetLayerDefn())

        #1) Does the geometry already exist
            # check_geom_equality.        
        
        #2) Write edge_geom 
        featedge_geom.SetGeometry(edge_geom)
        
        self.lyredge_geom.CreateFeature(featedge_geom)
        featedge_geom.Destroy()
        
        #3) Get created edge_geom primary key (GeomID)
        sql = ('SELECT "GeomID" FROM "%s" ORDER BY "GeomID" DESC LIMIT 1;' % 
                                                            self.tbledge_geom)
                                                            
        for row in self.conn.ExecuteSQL(sql):
            GeomID = row.GeomID                        
                                    
            # Append the GeomID to the edges attributes
        edge_attributes['Edge_GeomID'] = GeomID
        
        #4) attributes to edges table
        for field, data in edge_attributes.iteritems():
            featedge.SetField(field, data)
        self.lyredges.CreateFeature(featedge)
        featedge.Destroy()
        
    def write_pgnet_node(self, node_attributes, node_geom):
        '''Write NetworkX node to node table as defined by schema. Return the
        NodeID as assigned by the database
        
        '''
        # Does the node already exist?
            # If yes return NodeID
        # Else: Insert node
        ## OGR BUG? GIS Stackexchange question: http://t.co/G6u20Y6
        featnode = ogr.Feature(self.lyrnodes.GetLayerDefn())
        out_srs = ogr.osr.SpatialReference()
        out_srs.ImportFromEPSG(27700)
        node_geom.AssignSpatialReference(out_srs)
        featnode.SetGeometry(node_geom)
        
        for field, data in node_attributes.iteritems():
            featnode.SetField(field, data)
        
        self.lyrnodes.CreateFeature(featnode)
        featnode.Destroy()
        
        sql = ('SELECT "NodeID" from "%s" ORDER BY "NodeID" DESC LIMIT 1;' %
                                                            self.tblnodes)
                                                            
        for row in self.conn.ExecuteSQL(sql):
            return row.NodeID
    
    def write_pgnet_graph(self):
        pass

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

    def write_pgnet(self, network, tablename_prefix, overwrite=False):
        '''Write NetworkX (with geom) to PostGIS graph tables as defined by schema.
        
        Will also update graph table.
    
        Note that schema constrains must be applied in database - there are no 
        checks for database errors here!
        '''
    
        G = network # Use G as network, networkx convention.
        ## Table name prefix not implemented yet (waiting for plpgsql wrappers)        
        ##tbledges = tablename_prefix+'_edges'
        ##tblnodes = tablename_prefix+'_nodes'
        ##tbledge_geom = tablename_prefix+'edge_geometry'
        
        # Working on network_interdependency on CEG-Tyndall. 
        # Note that no db instance is created (using template for data write)

        graph_id = self.write_pgnet_graph()     
        graph_id = 1
        
        self.tbledges = 'Edges'
        self.tblnodes = 'Nodes'
        self.tbledge_geom = 'Edge_Geometry'
        
        ##self.edge_geom = self.getlayer(self.tbledge_geom)
        ##self.edges = self.getlayer(self.tbledges)

        self.lyredges = self.getlayer(self.tbledges)
        self.lyrnodes = self.getlayer(self.tblnodes)
        self.lyredge_geom = self.getlayer(self.tbledge_geom)   
        

        node_fields = {'GraphID':ogr.OFTInteger}  
        edge_fields = {'Node_F_ID':ogr.OFTInteger, 'Node_T_ID':ogr.OFTInteger, 
                  'GraphID':ogr.OFTInteger, 'Edge_GeomID':ogr.OFTInteger}
                  
        
        for e in G.edges(data=True):
            data = G.get_edge_data(*e)
            #print 'edge data', data
            edge_geom = self.netgeometry(e, data)
            
            # Insert the start node
            node_ref = e[0]
            #node_attrs
            node_data = G.node[node_ref]   # edge start node
            node_data['GraphID'] = 1 
            
            node_geom = self.netgeometry(node_ref, node_data)            
            node_id = self.write_pgnet_node(node_data, node_geom)
            G[e[0]][e[1]]['Node_F_ID'] = node_id
            
            # Insert the end node
            node_ref = e[1]
            node_data = G.node[node_ref]   # edge start node
            node_data['GraphID'] = graph_id           
            node_geom = self.netgeometry(node_ref, node_data)            
            node_id = self.write_pgnet_node(node_data, node_geom)
            G[e[0]][e[1]]['Node_T_ID'] = node_id

            G[e[0]][e[1]]['GraphID'] = graph_id
            
            edge_attrs = self.create_attribute_map(self.lyredges, e[2], 
                                                                   edge_fields)
                                                                   
           
            ''''
            for key, data in e[2].iteritems():
                # Reject data not for attribute table
                if (key != 'Json' and key != 'Wkt' and key != 'Wkb' 
                    and key != 'ShpName'):
                      # Add new attributes for each feature
                      if key not in edge_fields:
                         if type(data) in OGRTypes:
                             edge_fields[key] = OGRTypes[type(data)]
                         else:
                             edge_fields[key] = ogr.OFTString
                         newfield = ogr.FieldDefn(key, edge_fields[key])
                         self.lyredges.CreateField(newfield)
                         
                         edge_attrs[key] = data
                      # Create dict of single feature's attributes
                      else:
                         edge_attrs[key] = data
            '''
            self.write_pgnet_edge(edge_attrs, edge_geom)            
            
        exit(0)
        ''''
            e1 = e[1]   # edge end node
            NodeID_e0 = self.write_pgnet_node(G.node[e0],
        
        #edge_geom_lyr = self.getlayer(self.tbledge_geom)
        #edges_lyr = self.getlayer(self.tbledges)
        #nodes = self.getlayer(self.tblnodes)    
        
    
        ### Removed indexing.
        ##nid = 0
        
        # Fields as defined in schema
        fields = {'NodeID':ogr.OFTInteger, 'GraphID':ogr.OFTInteger}
        attributes = {}
        OGRTypes = {int:ogr.OFTInteger, str:ogr.OFTString, float:ogr.OFTReal}
        for n in G.nodes(data=True):
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
            #self.create_feature(self.lyrnodes, attributes,g)
            ##nid += 1
        # Repeat similar operation for Edges (should put in function at some point!)
        ##edge_id_field = ogr.FieldDefn('EdgeID',ogr.OFTInteger)
        ##self.lyredge_geom.CreateField(edge_id_field)        
        
        # Fields as defined in schema
        fields = {'Node_F_ID':ogr.OFTInteger, 'Node_T_ID':ogr.OFTInteger, 
                  'GraphID':ogr.OFTInteger, 'Edge_GeomID':ogr.OFTInteger}
        attributes = {}
        for e in G.edges(data=True):
            data = G.get_edge_data(*e)
            #print 'edge data', data
            g = self.netgeometry(e, data)
            e0 = e[0]   # edge start node
            e1 = e[1]   # edge end node
            # Add attributes as defined in schema
            G[e0][e1]['Node_F_ID'] = G.node[e[0]]['NodeID']
            G[e0][e1]['Node_T_ID'] = G.node[e[1]]['NodeID']
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
                         lyredges.CreateField(newfield)
                         
                         attributes[key] = data
                      # Create dict of single feature's attributes
                      else:
                         attributes[key] = data
            ##eid += 1
             # Create the feature with attributes
            ##self.create_feature(edges, attributes)
            ##edge_id = {'EdgeID':attributes['EdgeID']}
            self.write_pgnet_edge(attributes, g)
            ##self.create_feature(edge_geom, edge_id, g)
        #self.update_graph_table(G, tablename_prefix, self.tbledges, self.tblnodes)
        # Done, clear pointers
        nodes, edges = None, None    
        '''
if __name__ == "__main__":
    test_suite_nx_pgnet.main()