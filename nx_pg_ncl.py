#!/usr/bin/env  python
# -*- coding: utf-8 -*-
"""
nx_pg - Generates a networkx.DiGraph from PostGIS table.

"""
__author__ = "Tom Holderness"
__created__ = "Thu Jan 19 15:55:13 2012"
__year__ = "2011"
__version__ = "0.1"

import networkx as nx
import osgeo.ogr as ogr
import pggkgetpass as gp
#import nx_shp
PGS = gp.getpass('login', 'pg-ceg-tyndall')
#PGS = 'postgres'

def getfieldinfo(lyr, feature, flds):
    ''' Get information about fields - borrowed from nx_shp.py'''
    f = feature
    return [f.GetField(f.GetFieldIndex(x)) for x in flds]
    
def read_pg(conn, table_edges, table_nodes=None, directed=True):
    '''Function to convert geometry from PostGIS table to Network.'''
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
                    pass
                else:
                    flddata = getfieldinfo(lyr, f, flds )
                    attributes = dict(zip(flds, flddata))
                    attributes["TableName"] = lyr.GetName()
                    # Get the geometry for that feature
                    geom = f.GetGeometryRef()
                    # We've got a Multiline geometry so split into line segments
                    if ogr.Geometry.GetGeometryName(geom) == 'MULTILINESTRING':
                    #print f.GetGeomertyTypeName()
                        for line in geom:
                            #print "Exporting multiline geometry"
                            # Get points in line
                            n = line.GetPointCount()
                            # Get the attributes (akin to nx_shp)
                            attributes["Wkb"] = ogr.Geometry.ExportToWkb(line)
                            attributes["Wkt"] = ogr.Geometry.ExportToWkb(line)
                            attributes["Json"] = ogr.Geometry.ExportToWkb(line)
                            #print type(line.GetPoint(0))
                            net.add_edge(line.GetPoint_2D(0), line.GetPoint_2D(n-1), attributes)
                    elif ogr.Geometry.GetGeometryName(geom) == 'LINESTRING':
                        #print "Exporting line geometry"
                        n = geom.GetPointCount()
                        attributes["Wkb"] = ogr.Geometry.ExportToWkb(geom)
                        attributes["Wkt"] = ogr.Geometry.ExportToWkb(geom)
                        attributes["Json"] = ogr.Geometry.ExportToWkb(geom) 
                        ###print geom.GetPoint_2D(0), attributes['FID'] 
                        net.add_edge(geom.GetPoint_2D(0), geom.GetPoint_2D(n-1), attributes)
                    elif ogr.Geometry.GetGeometryName(geom) == 'POINT':
                        #print "Exporting point geometry"
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
  
def update_graph_table(conn, graph, graph_name, edge_table, node_table):
    
    # Turn off buggy OGR exceptions for this call (shoudl just return Null)
    ogr.DontUseExceptions()
    tblgraphs = conn.GetLayerByName('graphs')
    ogr.UseExceptions()
    '''
    for layer in conn:
        print layer.GetName()
        if layer.GetName() == 'graphs':
            tblgraphs = layer
            break
        else:
            tblgraphs = None
    '''
    
    if tblgraphs is None:
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
    print 'read feature tblgraphs...'
    feature = ogr.Feature(tblgraphs.GetLayerDefn())
    
    feature.SetField('GraphName', graph_name)
    feature.SetField('Nodes', edge_table)
    feature.SetField('Edges', node_table)
    if nx.is_directed(graph):
        feature.SetField('Directed', 1)
    else:
        feature.SetField('Directed', 0)
    # Still needs to be implemented.
    feature.SetField('MultiGraph', 0)
    print "tblgraphs.CreateFeature()"
    tblgraphs.CreateFeature(feature)
    feature.Destroy()

def write_pg(conn, network, tablename_prefix, overwrite=False):
    '''Function to write Network with geometry to PostGIS edges and nodes tables.'''
    G = network
    tbledges = tablename_prefix+'_edges'
    tblnodes = tablename_prefix+'_nodes'
        
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

    ## For all the nodes add an index (based on FID?) attributes.
      # then pull this attributes from edge information to have start and end node.
      # for e i n G
      # limit on the number of nodes as run out of integers?
    nid = 0
    fields = {}
    attributes = {}
    OGRTypes = {int:ogr.OFTInteger, str:ogr.OFTString, float:ogr.OFTReal}
    for n in G.nodes(data=True):
        G.node[n[0]]['NodeID'] = nid
        data = G.node[n[0]]
        #print G.node[n[0]].values()
        #data = G.node[n[0]].values() or [{}]
        #print data
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

    #for e in G.edges(data=True):
         #print e
    fields = {}
    attributes = {}
    eid = 0
    for e in G.edges(data=True):
        data = G.get_edge_data(*e)
        #print 'edge data', data
        g = netgeometry(e, data)
        e0 = e[0]
        e1 = e[1]
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

    nodes, edges = None, None    

def main():
    '''Main function - testing OGR Python PostGIS API for passing data to NetworkX.'''
    # Create Connecton
    
    conn = ogr.Open("PG: host='ceg-tyndall' dbname='tyndall_data' user='postgres' password="+PGS+"")  
    
    print 'reading network'
    net = read_pg(conn, 'LightRail_Baseline') #, 'LightRail_Baseline_Stations')
    print 'writing network'
    #conn = ogr.Open("PG: host='127.0.0.1' dbname='MIDAS-SPATIAL' user='postgres' password="+PGS+"")  
    write_pg(conn, net, 'lightrail_baseline_nd', overwrite=True)    
    print "done."
    conn = None
    
if __name__ == "__main__":
    main()
