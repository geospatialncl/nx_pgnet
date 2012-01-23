#!/usr/bin/env  python
# -*- coding: utf-8 -*-
"""
nx_pg_ncl - Procedural module for NetworkX read/write of PostGIS tables.

Development notes.

1) Based on nx_shp.py from NetworkX source.
    - Should be converted to OO/Class based module in the future for better 
        functionality
2) Currently (v 0.1) contains minimal error checking! 

3) When using read_pg() only include a nodes table if this corresponds to 
network nodes (i.e. edge junctions) otherwise output nodes table will break!

4) Outputs do not currently specify CRS/EPSG. Use a friendly GIS (QGIS) to set
on load.

5) Have tried to adhere to Python PEP8 style as much as possible.

6) Included main function is just for development and will be removed.

"""
__author__ = "Tom Holderness"
__created__ = "Thu Jan 19 15:55:13 2012"
__year__ = "2011"
__version__ = "0.1"

import networkx as nx
import osgeo.ogr as ogr
import pggkgetpass as gp

# Get database password from gnomekeyring (for development purposes only).
# REF: http://www.students.ncl.ac.uk/tom.holderness/pythongnomekeyring.php
PGS = gp.getpass('login', 'pg-ceg-tyndall')

def getfieldinfo(lyr, feature, flds):
    ''' Get information about fields - borrowed from nx_shp.py'''
    f = feature
    return [f.GetField(f.GetFieldIndex(x)) for x in flds]
    
def read_pg(conn, table_edges, table_nodes=None, directed=True):
    '''Read PostGIS table and return NetworkX graph.'''
    # Create Directed graph to store output
    if directed is True:
        net = nx.Graph()
    else:
        net = nx.DiGraph()
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
                    pass # Hack to catch any returned features which are None. 
                else:
                    flddata = getfieldinfo(lyr, f, flds )
                    attributes = dict(zip(flds, flddata))
                    attributes["TableName"] = lyr.GetName()
                    # Get the geometry for that feature
                    geom = f.GetGeometryRef()
                    
                    # Multiline geometry so split into line segments
                    if ogr.Geometry.GetGeometryName(geom) == 'MULTILINESTRING':
                        for line in geom:
                            # Get points in line
                            n = line.GetPointCount()
                            # Get the attributes (akin to nx_shp)
                            attributes["Wkb"] = ogr.Geometry.ExportToWkb(line)
                            attributes["Wkt"] = ogr.Geometry.ExportToWkb(line)
                            attributes["Json"] = ogr.Geometry.ExportToWkb(line)
                            net.add_edge(line.GetPoint_2D(0), 
                                         line.GetPoint_2D(n-1), attributes)
                    # Line geometry
                    elif ogr.Geometry.GetGeometryName(geom) == 'LINESTRING':
                        n = geom.GetPointCount()
                        attributes["Wkb"] = ogr.Geometry.ExportToWkb(geom)
                        attributes["Wkt"] = ogr.Geometry.ExportToWkb(geom)
                        attributes["Json"] = ogr.Geometry.ExportToWkb(geom) 
                        net.add_edge(geom.GetPoint_2D(0), 
                                         geom.GetPoint_2D(n-1), attributes)
                    # Point geometry                    
                    elif ogr.Geometry.GetGeometryName(geom) == 'POINT':
                        net.add_node((geom.GetPoint_2D(0)), attributes)
                    else:
                        raise ValueError, "PostGIS geometry type not supported."
    return net

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
            feature.SetField(field,data)
    lyr.CreateFeature(feature)
    feature.Destroy()

def getlayer(conn, layername):
    '''Get a PostGIS table (layer) by name and return as OGR layer,
        else return None.
    
    "Fixes (i.e. hacks)" OGR inconsistent error reporting'''
    # Disable Error if table is none.
    ogr.DontUseExceptions()
    layer = conn.GetLayerByName(layername)
    ogr.UseExceptions()
    return layer
  
def update_graph_table(conn, graph, graph_name, edge_table, node_table):
    '''Update graph table or create if doesn't exist with agreed schema.'''
    '''
    ogr.DontUseExceptions()
    tblgraphs = conn.GetLayerByName('graphs')
    ogr.UseExceptions()
    '''
    tblgraphs = getlayer(conn, 'graphs')
    '''
    for layer in conn:
        print layer.GetName()
        if layer.GetName() == 'graphs':
            tblgraphs = layer
            break
        else:
            tblgraphs = None
    '''
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
    print nx.is_directed(graph)
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
    '''

    G = network # Use G as network, convention from earlier code.
    tbledges = tablename_prefix+'_edges'
    tblnodes = tablename_prefix+'_nodes'
    
    edges = getlayer(conn, tbledges)
    nodes = getlayer(conn, tblnodes)    

    '''
    for layer in conn:    
        if layer.GetName() == tbledges:
            edges = layer
            break
        else:
            edges = None
    
    for layer in conn:
        if layer.GetName() == tblnodes:
            nodes = layer
            break
        else:
            nodes = None
    '''
    
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
