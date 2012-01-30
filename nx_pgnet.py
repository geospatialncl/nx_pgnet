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
__version__ = "0.1"

import networkx as nx
import osgeo.ogr as ogr

class read:
    '''Class with methods to read and build networks from either non-network
    vector line table or from schema defined network tables.'''

    def __init__(self, db_conn):
        self.conn = db_conn
    
    def getfieldinf(lyr, feature, flds):
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
        for lyr in conn:
            if lyr.GetName() == table_edges or lyr.GetName() == table_nodes:
                print "reading features from %s" % lyr.GetName()
                flds = [x.GetName() for x in lyr.schema]
                # Get the number of features in the layer
                for findex in xrange(lyr.GetFeatureCount()):
                    # Get a specific feature
                    f = lyr.GetFeature(findex+1)
                    if f is None:
                        pass # Catch any returned features which are None. 
                    else:
                        flddata = getfieldinfo(lyr, f, flds )
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
    
    def read_pg_net(self, network_name):
        '''Read postgis graph tables as defined by schema and return networkx
            graph.'''
        pass

    
def read_pg(conn, table_edges, table_nodes=None, directed=True):
    

def netgeometry(key, data):
    '''Create OGR geometry from NetworkX Graph Wkb/Wkt attributes.

    Borrowed from nx_shp.py.    
    '''
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
    '''Create an OGR feature in specified layer with geometry and attributes.'''
    feature = ogr.Feature(lyr.GetLayerDefn())
    feature.SetGeometry(geometry)
    if attributes != None:
        for field, data in attributes.iteritems(): 
            feature.SetField(field, data)
    lyr.CreateFeature(feature)
    feature.Destroy()

def getlayer(conn, layername):
    '''Get a PostGIS table (layer) by name and return as OGR layer,
        else return None.
    
    "An attempt to fix OGR inconsistent error reporting'''
    # Disable Error if table is none - this doesn't work. 
    # (SWIG binding docs are poorly constructed.)
    # Will run, but will throw user warning if table doesn't exist.
    # Updated question on gis.stackexchange. 
    # REF: http://t.co/O8chm6x
    ogr.DontUseExceptions()
    layer = conn.GetLayerByName(layername)
    ogr.UseExceptions()
    return layer
  
def update_graph_table(conn, graph, graph_name, edge_table, node_table):
    '''Update graph table or create if doesn't exist with agreed schema.'''
    
    tblgraphs = getlayer(conn, 'graphs')
    #ogr.UseExceptions()
    # tblgraphs doesn't exist so create with new features.
    # This is hard coded - should be reworked to be dynamic, similar style to..
        #...write_pg attributes)
    if tblgraphs is None:
        # tblgraphs is ogr.wkbNone (i.e. non-spatial)
        tblgraphs = conn.CreateLayer('graphs', None, ogr.wkbNone)
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

def write_pg(conn, network, tablename_prefix, overwrite=False):
    '''Write NetworkX (with geom) to PostGIS edges and nodes tables.
    
    Will also update graph table.

    Note that schema constrains must be applied in database - there are no 
    checks for database errors here!
    '''

    G = network # Use G as network, convention from earlier code.
    tbledges = tablename_prefix+'_edges'
    tblnodes = tablename_prefix+'_nodes'
    
    edges = getlayer(conn, tbledges)
    nodes = getlayer(conn, tblnodes)    

    if edges is None:
        edges = conn.CreateLayer(tbledges, None, ogr.wkbLineString)
    else:    
        if overwrite is True:
            conn.DeleteLayer(tbledges)
            edges = conn.CreateLayer(tbledges, None, ogr.wkbLineString)
            
    if nodes is None:
        nodes = conn.CreateLayer(tblnodes, None, ogr.wkbPoint)
    else:    
        if overwrite is True:
            conn.DeleteLayer(tblnodes)
            nodes = conn.CreateLayer(tblnodes, None, ogr.wkbPoint)

    # For all the nodes add an index.
    # Warning! This will limit unique node index to sys.maxint 
    nid = 0
    fields = {}
    attributes = {}
    OGRTypes = {int:ogr.OFTInteger, str:ogr.OFTString, float:ogr.OFTReal}
    for n in G.nodes(data=True):
        G.node[n[0]]['NodeID'] = nid
        data = G.node[n[0]]
        g = netgeometry(n[0], data)
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
        create_feature(g, nodes, attributes)
        nid += 1
    # Repeat similar operation for Edges (should put in function at some point!)
    fields = {}
    attributes = {}
    eid = 0 # edge_id
    for e in G.edges(data=True):
        data = G.get_edge_data(*e)
        #print 'edge data', data
        g = netgeometry(e, data)
        e0 = e[0]   # edge start node
        e1 = e[1]   # edge end node
        # Add attributes as defined in schema
        G[e0][e1]['EdgeID'] = eid
        G[e0][e1]['Node_F'] = G.node[e[0]]['NodeID']
        G[e0][e1]['Node_T'] = G.node[e[1]]['NodeID']
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
        eid += 1
         # Create the feature with attributes
        create_feature(g, edges, attributes)
    update_graph_table(conn, G, tablename_prefix, tbledges, tblnodes)
    # Done, clear pointers
    nodes, edges = None, None    

