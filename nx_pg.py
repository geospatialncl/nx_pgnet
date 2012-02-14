#!/usr/bin/env  python
# -*- coding: utf-8 -*-
"""
nx_pg - Generates a networkx.DiGraph from PostGIS table.

"""
__author__ = "Tom Holderness"
__created__ = "Thu Jan 19 15:55:13 2012"
__year__ = "2011"
__version__ = "1.0"

import networkx as nx
import osgeo.ogr as ogr
#import pggkgetpass as gp
#import nx_shp
#PGS = gp.getpass('login', 'postgres')
PGS = 'postgres'
ogr.UseExceptions()

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
                        net.add_edge(line.GetPoint_2D(0), line.GetPoint_2D(n-1), attributes)
                elif ogr.Geometry.GetGeometryName(geom) == 'LINESTRING':
                    n = geom.GetPointCount()
                    attributes["Wkb"] = ogr.Geometry.ExportToWkb(geom)
                    attributes["Wkt"] = ogr.Geometry.ExportToWkb(geom)
                    attributes["Json"] = ogr.Geometry.ExportToWkb(geom)  
                    net.add_edge(geom.GetPoint_2D(0), geom.GetPoint_2D(n-1), attributes)
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

def main():
    '''Main function - testing OGR Python PostGIS API for passing data to NetworkX.'''
    
    # Create Connecton
    conn = ogr.Open("PG: host='localhost' dbname='tyndall_data' user='postgres' password='postgres'")    
    #conn.CreateLayer("test")
    net = read_pg(conn, 'LightRail_Baseline')
    #write_pg(conn, net, 'test4', overwrite=True)    
    print net
    conn = None
    
    #print net.size()
    #nx_shp.write_shp(net, '/home/tom/')
                
                    
    
if __name__ == "__main__":
    main()
