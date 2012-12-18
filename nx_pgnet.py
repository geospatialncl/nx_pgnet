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

B{Module structure	}

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
	>>>					password='password'")
	
B{Examples}

The following are examples of read and write network operations. For
more detailed information see method documentation below.

Reading a network from PostGIS schema to a NetworkX graph instance:
	
	>>> import nx_pgnet
	>>> import osgeo.ogr as ogr
	
	>>> # Create a connection
	>>> conn = ogr.Open("PG: host='127.0.0.1' dbname='database' user='postgres'
	>>>					password='password'")

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

Tomas Holderness, David Alderson & Newcastle University

Developed by Tom Holderness & David Alderson at Newcastle University School of Civil Engineering
and Geosciences, geoinfomatics group:

Alistair Ford, Stuart Barr, Craig Robson.

B{License}

This software is released under a BSD style license. See LICENSE.TXT or type
nx_pgnet.license() for full details.

B{Credits}

Tomas Holderness, David Alderson, Alistair Ford, Stuart Barr and Craig Robson.

B{Contact}

tom.holderness@ncl.ac.uk
www.staff.ncl.ac.uk/tom.holderness

david.alderson@ncl.ac.uk\n
http://www.ncl.ac.uk/ceg/staff/profile/david.alderson

B{Development Notes}

Where possible the PEP8/PEP257 style guide has been implemented.\n
To do:
	1. Check attribution of nodes from schema and non-schema sources 
		(blank old id fields are being copied over).
		2. Error  / warnings module.
		3. Investigate bug: "Warning 1: Geometry to be inserted is of type 
			Line String, whereas the layer geometry type is Multi Line String.
		Insertion is likely to fail!"		
		5. 3D geometry support.
	
"""
__created__ = "January 2012"
__version__ = "0.9.2"
__author__ = """\n""".join(['David Alderson (david.alderson@ncl.ac.uk)', 'Tomas Holderness (tom.holderness@ncl.ac.uk)', 'Alistair Ford (a.c.ford@ncl.ac.uk)',		 'Stuart Barr (stuart.barr@ncl.ac.uk)','Craig Robson (c.a.robson1@ncl.ac.uk)'])
__license__ = 'BSD style. See LICENSE.TXT'								

import sys
import os
import networkx as nx
import osgeo.ogr as ogr
import osgeo.gdal as gdal
import csv
import re
import copy

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
		'''Setup connection to be inherited by methods.
		
		db_conn - ogr connection
		
		'''
		self.conn = db_conn
		if self.conn == None:
			raise Error('No connection to database.')
			
	def sql_function_check(self, function_name):
		'''Checks Postgres database for existence of specified function, 
			if not found raises error.
		
		function_name - string - name of function to check database for
			
		'''
			
		sql = ("SELECT * FROM pg_proc WHERE proname = '%s';" % (function_name))
		result = None
		for row in self.conn.ExecuteSQL(sql):
			result = row
		if result == None:
			raise Error('Database error: SQL function %s does not exist.' % 
							function_name)
		else:
			return None
	
	def create_network_tables(self, prefix, epsg=27700, directed=False,
		multigraph=False):
		'''Wrapper for ni_create_network_tables function.
		
		Creates empty network schema PostGIS tables.
		Requires graph 'prefix 'name and srid to create empty network schema
		PostGIS tables.
		
		Returns True if successful.
		
		prefix - string - name of graph/network, and will prefix all instance tables created in the database
		epsg - integer - epsg code of coordinate system of network data
		directed - boolean - true if a directed network is being written to the database
		multigraph - boolean - true if a multigraph network is being written to the database
		
		'''
		
		# Create network tables
		sql = ("SELECT * FROM ni_create_network_tables ('%s', %i, \
		CAST(%i AS BOOLEAN), CAST(%i AS BOOLEAN));" % (
		prefix, epsg, directed, multigraph))
		
		result = None
		for row in self.conn.ExecuteSQL(sql):   
		
			result = row.ni_create_network_tables
		
		return result
		
	def create_node_view(self, prefix):
		'''Wrapper for ni_create_node_view function.
		
		Creates a view containing node attributes and geometry values including
		int primary key suitable for QGIS.
		
		Requires network name ('prefix').
		
		Returns view name if successful.
		
		prefix - string - network name / table prefix
		
		'''
	   
		viewname = None
		sql = "SELECT * FROM ni_create_node_view('%s')" % prefix
		for row in self.conn.ExecuteSQL(sql):
			viewname = row.ni_create_node_view			
		if viewname == None:			
			raise Error("Could not create node view for network %s" % (prefix))	
		return viewname
		
	def create_edge_view(self, prefix):
		'''Wrapper for ni_create_edge_view function.
		
		Creates a view containing edge attributes and edge geometry values. 
		Requires network name ('prefix').
		
		Returns view name if successful.
		
		prefix - string - network name / table prefix
		
		'''		
		viewname = None
		sql = "SELECT * FROM ni_create_edge_view('%s')" % prefix

		for row in self.conn.ExecuteSQL(sql):
			viewname = row.ni_create_edge_view
		if viewname == None:
			raise Error("Could not create edge view for network %s" % (prefix))				
		return viewname
	
	def add_graph_record(self, prefix, directed=False, multipath=False):
		'''Wrapper for ni_add_graph_record function.
		
		Creates a record in the Graphs table based on graph attributes.
		
		Returns new graph id of successful.
		
		prefix - string - graph / network name to add to Graphs table
		directed - boolean - true if a directed network will be written, false otherwise
		multigraph - boolean - true if a multigraph network will be written, false otherwise
		
		'''  
	
		sql = ("SELECT * FROM ni_add_graph_record('%s', FALSE, FALSE);" % 
				(prefix))
				
		result = self.conn.ExecuteSQL(sql)		
		return result

	def ni_node_snap_geometry_equality_check(self, prefix, wkt, srs=27700, snap=0.1):
		'''Wrapper for ni_node_snap_geometry_equality_check function.
		
		Checks if geometry already eixsts in nodes table, based on input wkt and snap distance
		
		If not, returns None
		
		prefix - string - graph / network name
		wkt - string - point geometry to check as wkt
		srs - integer - epsg code of coordinate system of network data
		snap - float - snapping precision value
		
		'''
		sql = ("SELECT * FROM ni_node_snap_geometry_equality_check('%s', '%s', %s, %s);" 
				% (prefix, wkt, srs, snap))
		result = None
		
		for row in self.conn.ExecuteSQL(sql):			
			result = row.ni_node_snap_geometry_equality_check
		
		return result
		
	def node_geometry_equality_check(self, prefix, wkt, srs=27700):
		'''Wrapper for ni_node_geometry_equality_check function.
		
		Checks if geometry already eixsts in nodes table.
		
		If not, returns None
		
		prefix - string - graph / network name
		wkt - string - point geometry to check as wkt
		srs - integer - epsg code of coordinate system of network data
		
		'''
		
		sql = ("SELECT * FROM ni_node_geometry_equality_check('%s', '%s', %s);" 
				% (prefix, wkt, srs))
		result = None
		
		for row in self.conn.ExecuteSQL(sql):			
			result = row.ni_node_geometry_equality_check		   
		return result
	
	def ni_edge_snap_geometry_equality_check(self, prefix, wkt, srs=27700, snap=0.1):
		'''Wrapper for ni_edge_snap_geometry_equality_check function.
		
		Checks if geometry already eixsts in edges table, based on input wkt and snap distance
		
		If not, returns None
		
		prefix - string - graph / network name
		wkt - string - line geometry to check as wkt
		srs - integer - epsg code of coordinate system of network data
		snap - float - snap precision
		
		'''
		
		sql = ("SELECT * FROM ni_edge_snap_geometry_equality_check('%s', '%s', %s, %s);" 
				% (prefix, wkt, srs, snap))
		result = None
		
		for row in self.conn.ExecuteSQL(sql):			
			result = row.ni_edge_snap_geometry_equality_check
		
		return result
	
	def edge_geometry_equality_check(self, prefix, wkt, srs=27700):
		'''Wrapper for ni_edge_geometry_equality_check function.
		
		Checks if geometry already eixsts in nodes table. 
		
		If not, return None
		
		prefix - string - graph / network name
		wkt - string - line geometry to check as wkt
		srs - integer - epsg code of coordinate system of network data
		
		'''
		
		sql = ("SELECT * FROM ni_edge_geometry_equality_check('%s', '%s', %s);" 
				% (prefix, wkt, srs))
				
		result = None
		for row in self.conn.ExecuteSQL(sql):
			result = row.ni_edge_geometry_equality_check
		return result	   
	
	def delete_network(self, prefix):
		'''Wrapper for ni_delete_network function.
		
		Deletes a network entry from the Graphs table and drops associated 
		tables.
		
		prefix - string - graph / network name (as stored in Graphs table)
		
		'''
		
		sql = ("SELECT * FROM ni_delete_network('%s');" % (prefix))
		
		result = None
		for row in self.conn.ExecuteSQL(sql):
			result = row.ni_delete_network
		return result
	
	def graph_to_csv(self, prefix, output_path):
		'''Wrapper for the ni_graph_to_csv function.
		
		Outputs the tables related to the supplied prefix as .csv files, to the output path specified
		
		prefix - string - name of a network / graph as saved in the Graphs table
		output_path - string - path to save files to
		
		'''
		
		sql = ("SELECT * FROM ni_graph_to_csv('%s', '%s', '%s');" % (prefix, prefix, output_path))
		
		result = None
		for row in self.conn.ExecuteSQL(sql):
			result = row.ni_graph_to_csv
		return result
	
	
class import_graph:		
	'''
    Class to allow a user to import their network / graph from some other common format, that can then be written to PostGIS
    
    This class only allows importing of individual graphs i.e. we are not yet dealing with interdependencies etc through this
    
	Supported formats (for import and export) include:
	
		- GEXF
		- PAJEK - currently a single value or attribute can be used for edge attributes with Pajek format
		- YAML
		- GRAPHML
		- GML
		- GEPHI - compatible CSV node / edge lists
	
    '''
	# def __init__(self, db_conn):
		# '''Setup connection to be inherited by methods.'''
		# self.conn = db_conn
		# if self.conn == None:
			# raise Error('No connection to database.')

	def import_from_gexf(self, path, graphname, node_type=str, relabel=False):
		''' Import graph from Graph Exchange XML Format (GEXF) 
		
		path - string - path to GEXF file on disk
		graphname - string - name of graph to assign once created
		node_type - python type - denotes the Python-type that any string-based attributes will be converted to e.g. (int, float, long, str)
		relabel - boolean - if true relabel the nodes to use the GEXF node �label� attribute instead of the node �id� attribute as the NetworkX node label.
		
		'''
		
		#check if path to GEXF file exists		
		if os.path.isfile(path):
			#build network from raw gexf
			graph_from_raw_gexf = nx.read_gexf(path, node_type=node_type, relabel=relabel)
			#assign network name 
			graph_from_raw_gexf.graph['name'] = graphname
			#return network
			return graph_from_raw_gexf
		else:
			raise Error('The specified path %s does not exist' % (path))
			
	def import_from_pajek(self, path, graphname, encoding='UTF-8'):
		'''Import graph from pajek format (.net)
		
		path - string - path to Pajek file on disk
		graphname - string - name of graph to assign once created
		encoding - string - encoding option to 
		
		'''
		#check if path to Pajek file exists
		if os.path.isfile(path):
			
			#build network from raw gexf 
			graph_from_raw_pajek = nx.read_pajek(path, encoding=encoding)
			
			#create an empty graph (based on the type generated from the graphml input file)
			if isinstance(graph_from_raw_pajek, nx.classes.graph.Graph):
				graph = nx.Graph()
			elif isinstance(graph_from_raw_pajek, nx.classes.digraph.DiGraph):
				graph = nx.DiGraph()
			elif isinstance(graph_from_raw_pajek, nx.classes.multigraph.MultiGraph):
				graph = nx.MultiGraph()
			elif isinstance(graph_from_raw_graphml, nx.classes.multidigraph.MultiDiGraph):
				graph = nx.MultiDiGraph()
			else:
				raise Error('There was an error whilst trying to recognise the type of graph to be created. The Pajek file supplied is read into NetworkX, and so must contain data to create a: undirected graph (nx.Graph), directed graph (nx.DiGraph), undirected multigraph (nx.MultiGraph), directed multigraph (nx.MultiGraph). The type found was %s' % (str(type(graph_from_raw_pajek))))
			
			#read nodes from raw pajek network, and copy to output network
			for node in graph_from_raw_pajek.nodes(data=True):				
				coordinates = node[0]	
				#convert to tuple
				coordinates = eval(coordinates)
				if len(node) > 0:
					node_attributes = node[1]
				else:
					node_attributes = {}
				#add a node, with attribute dictionary
				graph.add_node(coordinates, node_attributes)
			
			#read edges from raw pajek network, and copy to output network
			for edge in graph_from_raw_pajek.edges(data=True):
				st_coordinates = edge[0]
				ed_coordinates = edge[1]
				#convert to tuple(s)
				st_coordinates = eval(st_coordinates)
				ed_coordinates = eval(ed_coordinates)
				
				#grab the attributes for that edge
				if len(edge) > 1:
					edge_attributes = edge[2]					
					#need to do something with the wkt
					if edge_attributes.has_key('Wkt'):
						wkt = edge_attributes['Wkt']						
					#need to do something with json
					if edge_attributes.has_key('Json'):
						json = edge_attributes['Json']						
				else:
					edge_attributes = {}
				
				#add an edge, and the attribute dictionary
				graph.add_edge(st_coordinates, ed_coordinates, edge_attributes)
			
			#set the graph name
			graph.graph['name'] = graphname
			return graph
		else:
			raise Error('The specified path %s does not exist' % (path))
	
	def import_from_yaml(self, path, graphname):
		'''Import graph from yaml format
		
		path - string - path to yaml file on disk
		graphname - string - name to assign to graph
		
		'''
		#check if path to yaml file exists
		if os.path.isfile(path):
			#build network from raw yaml file
			graph = nx.read_yaml(path)
			#assign network name
			graph.graph['name'] = graphname
			return graph
		else:
			raise Error('The specified path %s does not exist' % (path))
	
	def import_from_graphml(self, path, graphname, nodetype=str):
		'''Import graph from graphml format
		
		path - string - path to graphml file on disk
		graphname - string - name to assign to graph
		nodetype - type - default Python type to convert all string elements to.
		
		'''
		
		#check if the path to the graphml file exists
		if os.path.isfile(path):
					
			#create a graph by reading the raw graphml input file
			graph_from_raw_graphml = nx.read_graphml(path)
						
			#create an empty graph (based on the type generated from the graphml input file)
			if isinstance(graph_from_raw_graphml, nx.classes.graph.Graph):
				graph = nx.Graph()
			elif isinstance(graph_from_raw_graphml, nx.classes.digraph.DiGraph):
				graph = nx.DiGraph()
			elif isinstance(graph_from_raw_graphml, nx.classes.multigraph.MultiGraph):
				graph = nx.MultiGraph()
			elif isinstance(graph_from_raw_graphml, nx.classes.multidigraph.MultiDiGraph):
				graph = nx.MultiDiGraph()
			else:
				raise Error('There was an error whilst trying to recognise the type of graph to be created. The GraphML file supplied is read into NetworkX, and so must contain data to create a: undirected graph (nx.Graph), directed graph (nx.DiGraph), undirected multigraph (nx.MultiGraph), directed multigraph (nx.MultiGraph). The type found was %s' % (str(type(graph_from_raw_graphml))))
			
			#can we make the changes to the node ids here i.e. convert from string to tuple?
			for node in graph_from_raw_graphml.nodes(data=True):				
				coordinates = node[0]	
				#convert to tuple
				coordinates = eval(coordinates)
				if len(node) > 0:
					node_attributes = node[1]
				else:
					node_attributes = {}
				#add a node, and attributes
				graph.add_node(coordinates, node_attributes)
			
			for edge in graph_from_raw_graphml.edges(data=True):
				st_coordinates = edge[0]
				ed_coordinates = edge[1]
				#convert to tuple(s)
				st_coordinates = eval(st_coordinates)
				ed_coordinates = eval(ed_coordinates)
				
				#grab the attributes for that edge
				if len(edge) > 1:
					edge_attributes = edge[2]
				else:
					edge_attributes = {}
				
				#add an edge, and attributes
				graph.add_edge(st_coordinates, ed_coordinates, edge_attributes)
			
			graph.graph['name'] = graphname
			return graph
		else:
			raise Error('The specified path %s does not exist' % (path))
			
	def import_from_gml(self, path, graphname, relabel=False, encoding='UTF-8'):
		'''Import graph from gml format
		
			path - string - path to input GML file
			graphname - string - name to assign to graph
			relabel - boolean - If True use the GML node label attribute for node names otherwise use the node id.
			
		'''
		#check if the path to the input GML file exists
		if os.path.isfile(path):
			#create a graph from the raw input GML file
			graph = nx.read_gml(path, relabel=relabel, encoding=encoding)
			#assign graph given graph name
			graph.graph['name'] = graphname
			return graph
		else:
			raise Error('The specified path %s does not exist' % (path))
	
	def import_from_gephi_node_edge_lists(self, node_file_path, edge_file_path, graphname, node_file_geometry_text_key='geometry_text', edge_file_geometry_text_key='geometry_text', node_file_raw_geometry_key='geom', edge_file_raw_geometry_key='geom', directed=False):
		'''
		function to read a set of gephi-compatible csv files (nodes and edges separately) and create a network that can be stored wthin the database schema
	
		node_file_path - string - path to node gephi-compatible csv file		
		edge_file_path - string - path to edge gephi-compatible csv file
		graphname - string - name to be given to resultant graph / network created from gephi csv files
		node_file_geometry_text_key - string - column name / attribute name of node WKT geometry in input node csv file
		edge_file_geometry_text_key - string - column name / attribute name of node WKT geometry in input edge csv file (edge geometry must be a LINESTRING)
		node_file_raw_geometry_key - string - column name / attribute name of node raw geometry in input node csv file
		edge_file_raw_geometry_key - string - column name / attribute name of edge raw geometry in input edge csv file
		directed - boolean - denotes whether edges to be read from the input edge file are directed (mixed edge types are not allowed)
		'''
		#check that the input path to the node and edge csv files exist
		if ((os.path.isfile(node_file_path)) and (os.path.isfile(edge_file_path))):
			
			#currently no support for multigraph + gephi
			if directed == True:
				graph = nx.DiGraph()
			else:
				graph = nx.Graph()
			
			#node csv file open
			node_csv_file = open(node_file_path, 'r')			
			node_csv_reader = csv.reader(node_csv_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
			
			#geometry_text attribute should be a wkt version of the geometry representing either the node or the edge.
			
			node_csv_first_line = True
			node_header = []
			
			#set default index for each column in csv file
			NodeID_index = -1
			view_id_index = -1
			GraphID_index = -1			
			node_geometry_text_index = -1			
			wgs84_node_x_index = -1
			wgs84_node_y_index = -1			
			google_node_x_index = -1
			google_node_y_index = -1
			node_raw_geometry_index = -1
			#will store indices to remove from node attribute values
			node_attr_value_indices_to_remove = []
			
			for node_line in node_csv_reader:				
				if node_csv_first_line == True:
					#get the header from the node file
					node_header = list(node_line)
					
					if node_file_geometry_text_key in node_header:
						node_geometry_text_index = node_header.index('geometry_text')
					
					if 'NodeID' in node_header:
						NodeID_index = node_header.index('NodeID')						
						node_attr_value_indices_to_remove.append(NodeID_index)
					if 'view_id' in node_header:
						view_id_index = node_header.index('view_id')						
						node_attr_value_indices_to_remove.append(view_id_index)
					if 'GraphID' in node_header:
						GraphID_index = node_header.index('GraphID')						
						node_attr_value_indices_to_remove.append(GraphID_index)
					if 'wgs84_node_x' in node_header:
						wgs84_node_x_index = node_header.index('wgs84_node_x')						
						node_attr_value_indices_to_remove.append(wgs84_node_x_index)
					if 'wgs84_node_y' in node_header:
						wgs84_node_y_index = node_header.index('wgs84_node_y')						
						node_attr_value_indices_to_remove.append(wgs84_node_y_index)
					if 'google_node_x' in node_header:
						google_node_x_index = node_header.index('google_node_x')						
						node_attr_value_indices_to_remove.append(google_node_x_index)
					if 'google_node_y' in node_header:
						google_node_y_index = node_header.index('google_node_y')						
						node_attr_value_indices_to_remove.append(google_node_y_index)
					if node_file_raw_geometry_key in node_header:
						node_raw_geometry_index = node_header.index(node_file_raw_geometry_key)						
						node_attr_value_indices_to_remove.append(node_raw_geometry_index)
					
					#sort, then reverse indices to ensure last index is removed first
					node_attr_value_indices_to_remove.sort()
					node_attr_value_indices_to_remove.reverse()
					for index in node_attr_value_indices_to_remove:						
						node_header.pop(index)
					
					node_csv_first_line = False
				else:
					#check node file for geometry [node_file_geometry_key]
					if node_geometry_text_index > -1:
						
						#create a node geometry
						node_geom = ogr.CreateGeometryFromWkt(node_line[node_geometry_text_index])
						
						#node tuple containing node coordinates
						node_tuple = '(%s, %s)' % (node_geom.GetX(), node_geom.GetY())
						
						#this dictionary should ignore any attributes called:
						#NodeID
						#view_id
						#GraphID
						node_attr_values = list(node_line)
						
						for index in node_attr_value_indices_to_remove:
							node_attr_values.pop(index)
						
						#create a node attribute dictionary
						node_attrs = dict(zip(node_header, node_attr_values))
						
						#export this geometry to wkt, json, wkb
						#attach these as attributes to node
						graph.add_node(node_tuple, node_attrs)
					
					else:
						raise Error('There was no WKT geometry representation found in the node file %s, with WKT field name %s' % (node_file_path, node_file_geometry_text_key))
					
			#close the csv file
			node_csv_file.close()
			
			#edge csv file open
			edge_csv_file = open(edge_file_path, 'r')
			edge_csv_reader = csv.reader(edge_csv_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
			
			#set default index for each column in csv file
			GraphID_index = -1
			Edge_GeomID_index = -1
			EdgeID_index = -1
			Node_F_ID_index = -1
			Node_T_ID_index = -1
			view_id_index = -1
			edge_geometry_text_index = -1
			edge_geometry_raw_geometry_index = -1
			
			google_startpoint_x_index = -1
			google_startpoint_y_index =	-1		
			google_endpoint_x_index = -1
			google_endpoint_y_index = -1 
			
			wgs84_startpoint_x_index = -1
			wgs84_startpoint_y_index = -1 
			wgs84_endpoint_x_index = -1 
			wgs84_endpoint_y_index = -1
			
			edge_csv_first_line = True
			edge_header = []
			
			#will store indices to remove from node attribute values
			edge_attr_value_indices_to_remove = []
			
			for edge_line in edge_csv_reader:
				if edge_csv_first_line == True:
					#get the header from the edge file
					edge_header = list(edge_line)
					
					#check for WKT
					if edge_file_geometry_text_key in edge_header:
						edge_geometry_text_index = edge_header.index(edge_file_geometry_text_key)
					
					if 'GraphID' in edge_header:
						GraphID_index = edge_header.index('GraphID')						
						edge_attr_value_indices_to_remove.append(GraphID_index)
					if 'Edge_GeomID' in edge_header:
						Edge_GeomID_index = edge_header.index('Edge_GeomID')						
						edge_attr_value_indices_to_remove.append(Edge_GeomID_index)
					if 'EdgeID' in edge_header:
						EdgeID_index = edge_header.index('EdgeID')						
						edge_attr_value_indices_to_remove.append(EdgeID_index)
					if 'Node_F_ID' in edge_header:
						Node_F_ID_index = edge_header.index('Node_F_ID')					
						edge_attr_value_indices_to_remove.append(Node_F_ID_index)
					if 'Node_T_ID' in edge_header:
						Node_T_ID_index = edge_header.index('Node_T_ID')						
						edge_attr_value_indices_to_remove.append(Node_T_ID_index)
					if 'view_id' in edge_header:
						view_id_index = edge_header.index('view_id')						
						edge_attr_value_indices_to_remove.append(view_id_index)
					if 'google_startpoint_x' in edge_header:
						google_startpoint_x_index = edge_header.index('google_startpoint_x')						
						edge_attr_value_indices_to_remove.append(google_startpoint_x_index)
					if 'google_startpoint_y' in edge_header:
						google_startpoint_y_index = edge_header.index('google_startpoint_y')						
						edge_attr_value_indices_to_remove.append(google_startpoint_y_index)
					if 'google_endpoint_x' in edge_header:
						google_endpoint_x_index = edge_header.index('google_endpoint_x')						
						edge_attr_value_indices_to_remove.append(google_endpoint_x_index)
					if 'google_endpoint_y' in edge_header:
						google_endpoint_y_index = edge_header.index('google_endpoint_y')						
						edge_attr_value_indices_to_remove.append(google_endpoint_y_index)
					if 'wgs84_startpoint_x' in edge_header:
						wgs84_startpoint_x_index = edge_header.index('wgs84_startpoint_x')						
						edge_attr_value_indices_to_remove.append(wgs84_startpoint_x_index)
					if 'wgs84_startpoint_y' in edge_header:
						wgs84_startpoint_y_index = edge_header.index('wgs84_startpoint_y')						
						edge_attr_value_indices_to_remove.append(wgs84_startpoint_y_index)
					if 'wgs84_endpoint_x' in edge_header:
						wgs84_endpoint_x_index = edge_header.index('wgs84_endpoint_x')						
						edge_attr_value_indices_to_remove.append(wgs84_endpoint_x_index)
					if 'wgs84_endpoint_y' in edge_header:
						wgs84_endpoint_y_index = edge_header.index('wgs84_endpoint_y')						
						edge_attr_value_indices_to_remove.append(wgs84_endpoint_y_index)
					if edge_file_raw_geometry_key in edge_header:
						edge_geometry_raw_geometry_index = edge_header.index(edge_file_raw_geometry_key)						
						edge_attr_value_indices_to_remove.append(edge_geometry_raw_geometry_index)
					
					#sort, then reverse indices to ensure last index is removed first
					edge_attr_value_indices_to_remove.sort()
					edge_attr_value_indices_to_remove.reverse()
					
					#remove all column headings (attributes) that are not to be transferred to db
					for index in edge_attr_value_indices_to_remove:						
						edge_header.pop(index)					
					
					edge_csv_first_line = False
					
				else:
					
					#check edge file for geometry ['geometry_text']
					if edge_geometry_text_index > -1:
					
						#create edge geometry
						edge_geom = ogr.CreateGeometryFromWkt(edge_line[edge_geometry_text_index])
						
						#point count of edge
						point_count = edge_geom.GetPointCount()  
						
						#grab start point of edge
						start_point_edge_geom = edge_geom.GetPoint_2D(0)
						
						#grab end point of edge
						end_point_edge_geom = edge_geom.GetPoint_2D(point_count-1)
						
						#create tuples of start and end point coordinates
						start_point_edge_tuple = '(%s, %s)' % (start_point_edge_geom[0], start_point_edge_geom[1])
						end_point_edge_tuple = '(%s, %s)' % (end_point_edge_geom[0], end_point_edge_geom[1])
						
						#grab the csv line as a list
						edge_attr_values = list(edge_line)
						
						#remove all values from current line that are not to be transferred to db
						for index in edge_attr_value_indices_to_remove:
							edge_attr_values.pop(index)
						
						#create a node attribute dictionary
						edge_attrs = dict(zip(edge_header, edge_attr_values))
						
						graph.add_edge(start_point_edge_tuple, end_point_edge_tuple, edge_attrs)
					else:
						raise Error('There was no WKT geometry representation found in the edge file %s, with WKT field name %s' % (edge_file_path, edge_file_geometry_text_key))
			
			#close edge file
			edge_csv_file.close()
						
			graph.graph['name'] = graphname
			return graph	
		
		else:
			raise Error('The specified path to the node file (%s) or the path to the edge file (%s) does not exist. Please check that these files exist at the locations specified' % (node_file_path, edge_file_path))
	
	
class export_graph:
	'''Class to export networkx instances to chosen format supported by networkx
	
	Supported formats (for import and export) include:
	
		- GEXF
		- PAJEK - currently a single value or attribute can be used for edge attributes with Pajek format
		- YAML
		- GRAPHML
		- GML
		- GEPHI - compatible CSV node / edge lists
	
	'''
	def __init__(self, db_conn):
		'''Setup connection to be inherited by methods.'''
		self.conn = db_conn
		if self.conn == None:
			raise Error('No connection to database.')
	
	def export_to_gexf(self, graph, path, output_filename, encoding='utf-8', prettyprint=True):
		'''
		Export the given graph to the given path, in Graph Exchange XML Format (GEXF)
		
		graph - graph to export
		path - path to export to
		output_filename - output GEXF file name
		encoding - string encoding e.g. utf-8
		prettyprint - boolean - if true, use line breaks and indenting in output GEXF file
		
		'''
		#check the output path exists
		if os.path.isdir(path):
			
			#set the full output path to save the gexf file to
			full_path = '%s/%s.gexf' % (path, output_filename)
			
			#create a deepcopy of the graph to export
			#graph_copy = copy.deepcopy(graph)
			
			#create a networkx copy of the graph to export
			graph_copy = nx.copy(graph)
			
			#currently converting None type to "None"
			for edge in graph_copy.edges(data=True):
				edge_attrs = edge[2]

				#remove the wkb attr from the edge attributes
				if edge_attrs.has_key('Wkb'):
					del edge[2]['Wkb']
				
				#convert edge values from None to "None" so they can be handled by NetworkX gexf writer (NoneType unsupported)
				for edge_key in edge_attrs.keys():
					edge_value = edge_attrs[edge_key]											
					if edge_value == None:
						edge_value = 'None'
						edge_attrs[edge_key] = edge_value						
			
			#convert node values from None to "None" so they can be handled by NetworkX gexf writer (NoneType unsupported)
			for node in graph_copy.nodes(data=True):
				node_attrs = node[1]					
				for node_key in node_attrs.keys():
					node_value = node_attrs[node_key]											
					if node_value == None:
						node_value = 'None'
						node_attrs[node_key] = node_value	
			
			#write the gexf file
			nx.write_gexf(graph_copy, full_path, encoding=encoding, prettyprint=prettyprint)
			return full_path
		else:
			raise Error('The specified path %s does not exist' % (path))
	
	'''worked - although there is an issue with exporting the edge geometry'''
	def export_to_pajek(self, graph, path, output_filename, node_attribute_label=None, edge_attribute_weight=1.0, encoding='utf-8'):
		'''
		Export the given graph to the given path as Pajek format
		all attribute values are dropped ... this is not great - how can we keep attributes...
		
		graph - graph to export
		path - path to export to
		output_filename - output pajek file name
		node_attribute_label - name of attribute of node data to use as label for nodes in pajek (instead of just using coordinates) (can be a list)
		edge_attribute_weight - name of attribute of edge data to use as weight between start and end nodes of edge (can be a value to apply to all edges, or can be a single attribute name)
		
		'''
		
		#check the output path exists
		if os.path.isdir(path):
			
			#set the full output path to save the Pajek file to
			full_path = '%s/%s.net' % (path, output_filename)						
			
			#checking input graph type (regular graph)
			if isinstance(graph, nx.classes.graph.Graph):				
				graph_copy = nx.Graph()
			#checking input graph type (directed graph)
			elif isinstance(graph, nx.classes.digraph.DiGraph):				
				graph_copy = nx.DiGraph()
			#checking input graph type (multi graph)
			elif isinstance(graph, nx.classes.multigraph.MultiGraph):				
				graph_copy = nx.MultiGraph()
			#checking input graph type (multi directed graph)	
			elif isinstance(graph, nx.classes.multidigraph.MultiDiGraph):				
				graph_copy = nx.MultiDiGraph()
			else:
				raise Error('There was an error whilst trying to recognise the type of graph to be created. The graph to be exported must be one of the following types: undirected graph (nx.Graph), directed graph (nx.DiGraph), undirected multigraph (nx.MultiGraph), directed multigraph (nx.MultiGraph). The type found was %s' % (str(type(graph))))
			
			
			#copy the nodes to the graph to be output as Pajek i.e. remove all node attributes
			#keep x and y to ensure the network 
			for node in graph.nodes(data=True):								
				if node_attribute_label is not None or node_attribute_label != '':
					key = '%s' % str(node_attribute_label)
					raw_value = str(node[1][node_attribute_label]).rstrip().lstrip()	
					#add the node to the graph, with associated attribute
					graph_copy.add_node(node[0], {'x': float(node[0][0]), 'y':float(node[0][1]), key:raw_value})					
				else:
					#add the node to the graph
					graph_copy.add_node(node[0], {'x': float(node[0][0]), 'y':float(node[0][1])})					
							
			#copy the edges to the graph to be output as Pajek i.e. remove all edge attributes
			for edge in graph.edges(data=True):				
				#user has specified an attribute name to use as values for edge weights							
				if type(edge_attribute_weight) == str:
					#add the edge to the graph
					graph_copy.add_edge(edge[0], edge[1], {'weight': edge[2][edge_attribute_weight]})
				#user has supplied a constant value
				else:					
					#add the edge to the graph
					graph_copy.add_edge(edge[0], edge[1], {'weight': edge_attribute_weight})
			
			#write the copy to the output path i.e. the graph now without the wkb element
			nx.write_pajek(graph_copy, full_path, encoding=encoding)				
			return full_path
		else:
			raise Error('The specified path %s does not exist' % (path))
	
	'''worked'''
	def export_to_yaml(self, graph, path, output_filename, encoding='UTF-8'):
		'''
		Export the given graph to the given path as Yaml format
		
		graph - networkx graph
		path - string - output path on disk to write YAML file to
		output_filename - string - name of output YAML file to write to disk
		encoding - string - encoding to use for strings
		
		'''		
		#check that the output path exists
		if os.path.isdir(path):
		
			#set the full output path to save the YAML file to
			full_path = '%s/%s.yaml' % (path, output_filename)
		
			#create a deepcopy of the graph to export
			#graph_copy = copy.deepcopy(graph)
			
			#create a networkx copy of the graph to export
			graph_copy = nx.copy(graph)

			#remove wkb attribute from edge			
			for edge in graph_copy.edges(data=True):					
				if len(edge) > 1:					
					edge_attrs = edge[2]												
					if edge_attrs.has_key('Wkb'):
						del edge[2]['Wkb']
			
			#write out the graph to YAML format
			nx.write_yaml(graph_copy, full_path, encoding)
			
			return full_path
			
		else:
			raise Error('The specified path %s does not exist' % (path))
	
	'''working - has to change None types to "None" string to prevent graphml.py of networkx write function from failing on "None" types'''
	def export_to_graphml(self, graph, path, output_filename, encoding='UTF-8', prettyprint=True):
		'''
		Export the given graph to the given path as GraphML format
		
		graph - networkx graph
		path - string - output path on disk to write GraphML file to
		output_filename - string - name of output GraphML file to write
		encoding - string - encoding of string outputs
		prettyprint - boolean - if true use line breaks and indentation in output GraphML
		
		'''
		
		#check that the output path exists
		if os.path.isdir(path):
			#create a deepcopy of the graph to export
			#graph_copy = copy.deepcopy(graph)
			
			#set the full output path to save the GraphML file to
			full_path = '%s/%s.graphml' % (path, output_filename)
			
			#create a networkx copy of the graph to export
			graph_copy = nx.copy(graph)
			
			#remove the Wkb element from the edge attributes			
			for edge in graph_copy.edges(data=True):					
				if len(edge) > 1:					
					edge_attrs = edge[2]												
					if edge_attrs.has_key('Wkb'):
						del edge[2]['Wkb']
						
			#currently converting None type to "None"
			for edge in graph_copy.edges(data=True):
				edge_attrs = edge[2]						
				for edge_key in edge_attrs.keys():
					edge_value = edge_attrs[edge_key]											
					if edge_value == None:
						edge_value = 'None'
						edge_attrs[edge_key] = edge_value						
			
			#currently converting None type to "None"
			for node in graph_copy.nodes(data=True):
				node_attrs = node[1]					
				for node_key in node_attrs.keys():
					node_value = node_attrs[node_key]											
					if node_value == None:
						node_value = 'None'
						node_attrs[node_key] = node_value						
			
			#write out the graph to GraphML format			
			nx.write_graphml(graph_copy, full_path, encoding=encoding, prettyprint=prettyprint)
			return full_path
		else:
			raise Error('The specified path %s does not exist' % (path))
	
	'''
	working
	'''
	def export_to_gml(self, graph, path, output_filename):
		'''
		Export the given graph to the given path as GML format
		
		--graph - networkx graph
		--path - folder to save gml file to
		--output_filename - gml output file name (no extension)
		
		'''
		
		#check that the output path exists
		if os.path.isdir(path):
			#create a deepcopy of the graph to export
			#graph_copy = copy.deepcopy(graph)			
			
			#set the full output path to write the GML file to
			full_path = '%s/%s.gml' % (path, output_filename)
			
			#create a networkx copy of the graph to export
			graph_copy = nx.copy(graph)
			
			#currently deleting the Wkb element from the edge attributes
			for edge in graph_copy.edges(data=True):					
				if len(edge) > 1:					
					edge_attrs = edge[2]									
					#currently removes the wkb element to allow writing to pajek
					if edge_attrs.has_key('Wkb'):
						del edge[2]['Wkb']
			
			#need to ensure that the nodes have coordinates added to them on the way out e.g. as JSON and WKT
			for node in graph_copy.nodes(data=True):
				#grab the node coordinates
				node_coordinates = node[0]
				#grab the node attributes (testing these for wkt and json keys)
				node_attrs = node[1]				
				
				if not node_attrs.has_key('Wkt') and not node_attrs.has_key('Json'):					
					#create an empty point geometry
					geom = ogr.Geometry(ogr.wkbPoint)
					#set the coordinates of the geometry
					geom.SetPoint_2D(0, *node_coordinates)
					
					#assign a wkt attribute to the node
					if not node_attrs.has_key('Wkt'):
						node_wkt = ogr.Geometry.ExportToWkt(geom)
						node_attrs['Wkt'] = node_wkt
						
					#assign a json attribute to the node
					if not node_attrs.has_key('Json'):
						node_json = ogr.Geometry.ExportToJson(geom)
						node_attrs['Json'] = node_json										
				
			#need to do something to convert the node data coordinates to a "label" (currently converting to integer)
			graph_copy = nx.relabel.convert_node_labels_to_integers(graph_copy, first_label=1, ordering='default', discard_old_labels=False)

			#write out the graph as GML to the given path
			nx.write_gml(graph_copy, full_path)
			
			return full_path
		else:
			raise Error('The specified path %s does not exist' % (path))
	
	
	def export_to_gephi_node_edge_lists(self, path, node_viewname, edge_viewname, node_geometry_column_name='geom', edge_geometry_column_name='geom', directed=False):
		'''
		
		--path - string - output folder location
		--node_viewname - string - name of node view in database e.g. <network_name>_View_Nodes
		--edge_viewname - string - name of edge view in database e.g. <network_name>_View_Edges_Edge_Geometry
		--node_geometry_column_name - string - name of geometry column of node view e.g. geom
		--edge_geometry_column_name - string - name of geometry column of edge view e.g. geom
		--directed - boolean - denotes if outpout
		
		export the edge/edge_geometry view along with the node view for direct import to Gephi
		the files will be created within the same name as the tables
		node table has all attributes of node table +
			#google map projection x coordinate (900913) = google_node_x
			#google map projection y coordinate (900913) = google_node_y
			#wgs84 map projection x coordinate (4326) = wgs84_node_x
			#wgs84 map projection y coordinate (4326) = wgs84_node_y
		
		edge table has all attributes of edge table ("Node_F_ID" = "Source", "Node_T_ID" = "Target") + 
			#google map projection x coordinate startpoint (900913) = google_startpoint_x
			#google map projection y coordinate startpoint (900913) = google_startpoint_y
			#google map projection x coordinate endpoint (900913) = google_endpoint_x
			#google map projection y coordinate endpoint (900913) = google_endpoint_y
			
			#wgs84 map projection x coordinate startpoint (4326) = wgs84_startpoint_x
			#wgs84 map projection x coordinate startpoint (4326) = wgs84_startpoint_y
			#wgs84 map projection x coordinate endpoint (4326) = wgs84_endpoint_x
			#wgs84 map projection x coordinate endpoint (4326) = wgs84_endpoint_y
		'''
		
		#check if graph is directed/undirected (cannot have mixed graph types (Directed + Undirected edges) in the same graph)
		if directed == False:
			gephi_directed_value = 'Undirected'
		else:
			gephi_directed_value = 'Directed'
		
		#define the output file name and path for the Gephi-compatible csv dump of the node view
		node_file_name = '%s%s.csv' % (path, node_viewname)
		
		#define the sql to execute for generating a Gephi-compatible csv dump of the node view
		node_sql = ("COPY (SELECT node_table.*, ST_AsText(node_table.%s) as geometry_text, ST_SRID(node_table.%s) as srid, ST_X(ST_AsText(ST_Transform(node_table.%s, 900913))) as google_node_x, ST_Y(ST_AsText(ST_Transform(node_table.%s, 900913))) as google_node_y, ST_X(ST_AsText(ST_Transform(node_table.%s, 4326))) as wgs84_node_x, ST_Y(ST_AsText(ST_Transform(node_table.%s, 4326))) as wgs84_node_y FROM \"%s\" AS node_table) TO '%s' DELIMITER AS ',' CSV HEADER;" % (node_geometry_column_name, node_geometry_column_name, node_geometry_column_name, node_geometry_column_name, node_geometry_column_name, node_geometry_column_name, node_viewname, node_file_name))
		
		#define the output file name and path for the Gephi-compatible csv dump of the edge view
		edge_file_name = '%s%s.csv' % (path, edge_viewname)
		
		#define the sql to execute for generating a Gephi-compatible csv dump of the edge view
		edge_sql = ("COPY (SELECT edge_table.*, ST_AsText(edge_table.%s) as geometry_text, ST_SRID(edge_table.%s) as srid, \"Node_F_ID\" as \"Source\", \"Node_T_ID\" as \"Target\", '%s' as \"Type\", ST_X(ST_Transform(ST_StartPoint(edge_table.%s), 900913)) as google_startpoint_x, ST_Y(ST_Transform(ST_StartPoint(edge_table.%s), 900913)) as google_startpoint_y, ST_X(ST_Transform(ST_EndPoint(edge_table.%s), 900913)) as google_endpoint_x, ST_Y(ST_Transform(ST_EndPoint(edge_table.%s), 900913)) as google_endpoint_y, ST_X(ST_Transform(ST_StartPoint(edge_table.%s), 4326)) as wgs84_startpoint_x, ST_Y(ST_Transform(ST_StartPoint(edge_table.%s), 4326)) as wgs84_startpoint_y, ST_X(ST_Transform(ST_EndPoint(edge_table.%s), 4326)) as wgs84_endpoint_x, ST_Y(ST_Transform(ST_EndPoint(edge_table.%s), 4326)) as wgs84_endpoint_y FROM \"%s\" AS edge_table) TO '%s' DELIMITER AS ',' CSV HEADER" % (edge_geometry_column_name, edge_geometry_column_name, gephi_directed_value, edge_geometry_column_name, edge_geometry_column_name, edge_geometry_column_name, edge_geometry_column_name, edge_geometry_column_name, edge_geometry_column_name, edge_geometry_column_name, edge_geometry_column_name, edge_viewname, edge_file_name))
		
		print 'node_sql: %s', node_sql
		
		#execute the node view to csv query
		node_result = self.conn.ExecuteSQL(node_sql)  
		
		#execute the edge view to csv query
		edge_result = self.conn.ExecuteSQL(edge_sql)
		
		#check if output files exist
		if os.path.isfile(node_file_name) and os.path.isfile(edge_file_name):
			return [node_file_name, edge_file_name]
		else:
			raise Error('Error exporting data from node view (%s, geom_column: %s) to file at (%s) and edge view (%s, geom_column: %s) to file at (%s)', (node_viewname, node_geometry_column_name, node_file_name, edge_viewname, edge_geometry_column_name, edge_file_name))
		
class read:
	'''Class to read and build networks from PostGIS schema network tables.'''

	def __init__(self, db_conn):
		'''Setup connection to be inherited by methods.
		
		db_conn - ogr connection
		
		'''
		self.conn = db_conn
		
		if self.conn == None:
			raise Error('No connection to database.')
			
	def getfieldinfo(self, lyr, feature, flds):
		'''Get information about fields from a table (as OGR feature).
		
		lyr - OGR Layer
		feature - OGR feature to query
		flds - dict - dictionary of fields
		
		'''
		f = feature
		return [f.GetField(f.GetFieldIndex(x)) for x in flds]

	def pgnet_edges(self, graph):
		'''Reads edges from edge and edge_geometry tables and add to graph.
		
		graph - networkx graph/network
		
		'''

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
		'''Reads nodes from node table and add to graph.
		
		graph - networkx graph/network
		
		'''

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
		
		Returns attributes as a dict of variables.
		
		prefix - string - graph / network name, as stored in Graphs table
		
		'''  
		
		graph = None
		sql = ('SELECT * FROM	"Graphs" WHERE "GraphName" = \'%s\';' % prefix)
		for row in self.conn.ExecuteSQL(sql):
			graph = row.items()

		return graph
	
	def pgnet(self, prefix):
		'''Read a network from PostGIS network schema tables. 
		
		Returns instance of networkx.Graph().
		
		prefix - string - graph / network name
		
		'''
		
		# Set up variables
		self.prefix = prefix
		# Get graph attributes
		graph_attrs = self.graph_table(self.prefix)
		if graph_attrs == None:
			error = "Can't find network '%s' in Graph table" % self.prefix
			raise Error(error)
		#ORIGINAL
		# Create empty graph (directed/un-directed)
		#if graph_attrs['Directed'] == 0:
			#G = nx.Graph()
		#else:
			#G.nx.DiGraph()
		
		#NEW handles multi and directed graphs
		if ((graph_attrs['Directed'] == 0) and (graph_attrs['MultiGraph'] == 0)):			
			G = nx.Graph()
		elif ((graph_attrs['Directed'] == 1) and (graph_attrs['MultiGraph'] == 0)):			
			G = nx.DiGraph()
		elif ((graph_attrs['Directed'] == 0) and (graph_attrs['MultiGraph'] == 1)):			
			G = nx.MultiGraph()
		elif ((graph_attrs['Directed'] == 1) and (graph_attrs['MultiGraph'] == 1)):			
			G = nx.MultiDiGraph()
			
		# Assign graph attributes to graph
		for key, value in graph_attrs.iteritems():
			G.graph[key] = value
		
		self.pgnet_edges(G)
		self.pgnet_nodes(G)

		return G
	
	#create a network x graph instance by reading the csv input files
	def pgnet_via_csv(self, network_name, node_csv_file_name, edge_csv_file_name, edge_geometry_csv_file_name, directed=False, multigraph=False):
		'''Read a network from a csv formatted file (as if output from the schema, but could be manually created
		
			- ensures the node file has columns: 
				- GraphID
				- geom
			- ensures the edge file has columns:
				- Node_F_ID
				- Node_T_ID
				- GraphID
				- Edge_GeomID
			- ensures the edge geometry file has columns:
				- GeomID
				- geom
		
		network_name - string - name of network to create
		node_csv_file_name - string - csv file path to node file
		edge_csv_file_name - string - csv file path to edge file
		edge_geometry_csv_file_name - string - csv file path to edge_geometry file
		directed - boolean - denotes whether network to be created is a directed, or undirected network (True=directed, False=undirected)
		multigraph - boolean - denotes whether network to be created is a multigraph, or regular graph (True=multigraph, False=regular graph)
		
		'''
		
		#check that the input node csv file exists before proceeding
		if not os.path.isfile(node_csv_file):
			raise Error('The input node file does not exist at: %s' % (node_csv_file))
			
		#check that the input edge csv file exists before proceeding
		if not os.path.isfile(edge_csv_file):
			raise Error('The input edge file does not exist at: %s' % (edge_csv_file))
		
		#check that the input edge geometry csv file exists before proceeding
		if not os.path.isfile(edge_geometry_csv_file):
			raise Error('The input edge geometry file does not exist at: %s' % (edge_geometry_csv_file))
		
		
		#not directed, not multigraph
		if ((directed == False) and (multigraph == False)):			
			net = nx.Graph()
		#not directed, multigraph
		elif ((directed == False) and (multigraph == True)):			
			net = nx.MultiGraph()	
		#directed, not multigraph
		elif ((directed == True) and (multigraph == False)):			
			net = nx.DiGraph()
		#directed, multigraph
		elif ((directed == True) and (multigraph == True)):			
			net = nx.MultiDiGraph()
		
		#define node, edge, and edge geometry files
		node_csv_file = open(node_csv_file_name, 'r')
		edge_csv_file = open(edge_csv_file_name, 'r')
		edge_geometry_csv_file = open(edge_geometry_csv_file_name, 'r')
		
		#define node, edge, edge_geometry csv file readers
		node_csv_reader = csv.DictReader(node_csv_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
		edge_csv_reader = csv.DictReader(edge_csv_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
		edge_geometry_csv_reader = csv.DictReader(edge_geometry_csv_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
		
		#generic Node table attributes
		generic_node_fieldnames = []
		generic_node_fieldnames.append("GraphID")
		generic_node_fieldnames.append("geom")
		
		#generic Edge table attributes
		generic_edge_fieldnames = []
		generic_edge_fieldnames.append("Node_F_ID")
		generic_edge_fieldnames.append("Node_T_ID")
		generic_edge_fieldnames.append("GraphID")
		generic_edge_fieldnames.append("Edge_GeomID")
		
		#generic Edge_Geometry table attributes
		generic_edge_geometry_fieldnames = []
		generic_edge_geometry_fieldnames.append("GeomID")
		generic_edge_geometry_fieldnames.append("geom")
		
		#need to check that the node csv file header contains at least the minimum generic node fieldnames
		node_first_line = True		
		missing_node_fieldname = False	
		node_first_line_contents = []
		#loop rows in node table
		for node_row in node_csv_reader:			
			##perform a check to see that the node specific fieldnames exist in the node csv file
			if node_first_line == True:
				node_first_line_contents = node_row
				node_first_line = False				
				for generic_node_fieldname in generic_node_fieldnames:
					if generic_node_fieldname not in node_row:
						#print 'error: generic node fieldname does not exist: %s', generic_node_fieldname
						raise Error('The field name %s does not exist in the input node csv file (%s)' % (generic_node_fieldname, node_csv_file_name))
						missing_node_fieldname = True
						break;
				if missing_node_fieldname == True:
					node_csv_file.close()
					raise Error('A mandatory node field name (one of %s) is missing from input node csv file (%s)' % (generic_node_fieldnames, node_csv_file_name))
					break;
			##process the rest of the file
			else:								
				#grab the attributes for that node
				node_attrs = node_row
				
				#grab the node geometry
				node_geom_wkt_raw = str(node_row['geom'])
				node_geom_srid = node_geom_wkt_raw[:node_geom_wkt_raw.find(';')]
				node_geom_wkt = node_geom_wkt_raw[node_geom_wkt_raw.find(';')+1:]
				
				#create an OGR Point geometry from
				node_geom = ogr.CreateGeometryFromWkt(node_geom_wkt)
				
				#create a wkb and json version to store as node attributes
				node_geom_wkb = ogr.Geometry.ExportToWkb(node_geom)
				node_geom_json = ogr.Geometry.ExportToJson(node_geom)
				
				#add the wkb and json versions to the node attributes
				node_attrs["Wkb"] = node_geom_wkb
				node_attrs["Wkt"] = node_geom_wkt
				node_attrs["Json"] = node_geom_json
				
				node_coord = node_geom.GetPoint_2D(0)				
				node_coord_tuple=(node_coord[0], node_coord[1])
				
				#add the node to the network, with attributes
				net.add_node(node_coord_tuple, node_attrs)
		
		#close the node csv file
		node_csv_file.close()
		del node_csv_file
		
		#need to check that the edge_geometry csv file header contains at least the minimum edge_geometry fieldnames
		edge_geometry_first_line = True
		missing_edge_geometry_fieldname = False
		edge_geometry_first_line_contents = []	 

		coords = {}
		
		#need some way of being able to attach the correct edge geometry wkt, wkb and json version of the geometry to the attributes of the correct edge
		#edge Edge_GeomID should match GeomID of edge_geometry
		#loop rows in edge geometry table
		for edge_geometry_row in edge_geometry_csv_reader:
			if edge_geometry_first_line == True:
				edge_geometry_first_line_contents = edge_geometry_row
				edge_geometry_first_line = False				
				for generic_edge_geometry_fieldname in generic_edge_geometry_fieldnames:
					if generic_edge_geometry_fieldname not in edge_geometry_row:
						#print 'error: generic edge geometry fieldname does not exist: %s', generic_edge_geometry_fieldname
						raise Error('The field name %s does not exist in the input edge geometry csv file (%s)' % (generic_edge_geometry_fieldname, edge_geometry_csv_file_name))
						missing_edge_geometry_fieldname = True
					break;
				if missing_edge_geometry_fieldname == True:
					edge_geometry_csv_file.close()
					raise Error('A mandatory edge geometry field name (one of %s) is missing from input edge geometry csv file (%s)' % (generic_edge_geometry_fieldnames, edge_geometry_csv_file_name))
					break;
			#process the rest of the file
			else:
			   
				#grab the geomid
				edge_geometry_geom_id = edge_geometry_row['GeomID']
				
				#grab the edge_geometry attributes
				edge_geometry_attrs = edge_geometry_row
				
				#grab the node geometry
				edge_geometry_wkt_raw = edge_geometry_row['geom']
				edge_geometry_srid = edge_geometry_wkt_raw[:edge_geometry_wkt_raw.find(';')]
				edge_geometry_wkt = edge_geometry_wkt_raw[edge_geometry_wkt_raw.find(';')+1:]
												
				#create an OGR LineString geometry
				edge_geometry = ogr.CreateGeometryFromWkt(edge_geometry_wkt)
				
				edge_geometry_wkb = ogr.Geometry.ExportToWkb(edge_geometry)
				edge_geometry_json = ogr.Geometry.ExportToJson(edge_geometry)
				
				#get the first point of the edge
				node_from_geom = edge_geometry.GetPoint_2D(0)
				node_from_geom_coord_tuple = (node_from_geom[0], node_from_geom[1])
				
				#count the number of points in the edge
				n = edge_geometry.GetPointCount()	   
				
				#get the last point of the edge
				node_to_geom = edge_geometry.GetPoint_2D(n-1)				
				node_to_geom_coord_tuple = (node_to_geom[0], node_to_geom[1])
				
				#assign edge attributes
				edge_geometry_attrs["Wkb"] = edge_geometry_wkb
				edge_geometry_attrs["Wkt"] = edge_geometry_wkt
				edge_geometry_attrs["Json"] = edge_geometry_json
								
				#add the edge with the attributes from edge_geometry csv file
				net.add_edge(node_from_geom_coord_tuple, node_to_geom_coord_tuple, edge_geometry_attrs)
								
				coords[edge_geometry_geom_id] = [node_from_geom_coord_tuple, node_to_geom_coord_tuple]
				
				#add the edge without the attributes from the edge_geometry csv file
				#net.add_edge(node_from_geom_coord_tuple, node_to_geom_coord_tuple)
		
		#close the edge geometry csv file
		edge_geometry_csv_file.close()		
		del edge_geometry_csv_file
		
		#need to check that the edge csv file header contains at least the minimum generic edge fieldnames
		edge_first_line = True
		missing_edge_fieldname = False   
		edge_first_line_contents = []
		
		#loop rows in the edge table
		for edge_row in edge_csv_reader:
			if edge_first_line == True:
				edge_first_line_contents = edge_row
				edge_first_line = False				
				for generic_edge_fieldname in generic_edge_fieldnames:
					if generic_edge_fieldname not in edge_row:
						#print 'error: generic edge fieldname does not exist: %s', generic_edge_fieldname
						raise Error('The field name %s does not exist in the input edge csv file (%s)' % (generic_edge_fieldname, edge_csv_file_name))
						missing_edge_fieldname = True
					break;
				if missing_edge_fieldname == True:
					edge_csv_file.close()
					raise Error('A mandatory node field name (one of %s) is missing from input edge geometry csv file (%s)' % (generic_edge_fieldnames, edge_csv_file_name))
					break;
			#process the rest of the file
			else:				
				
				#grab the edge_geomid
				edge_geom_id = edge_row['Edge_GeomID']
				
				#grab the attributes for that edge
				edge_attrs = edge_row
				
				matched_edge_tuples = coords[edge_geom_id]
				current_matched_edge_attributes = net[matched_edge_tuples[0]][matched_edge_tuples[1]]
				new_edge_attributes = dict(current_matched_edge_attributes, **edge_attrs)				
				net[matched_edge_tuples[0]][matched_edge_tuples[1]] = new_edge_attributes
							
		#close the edge csv file
		edge_csv_file.close()
		del edge_csv_file
		
		return net		
		
		
class write:
	'''Class to write NetworkX instance to PostGIS network schema tables.'''
	
	def __init__(self, db_conn):
		'''Setup connection to be inherited by methods.
		
		db_conn - OGR connection
		
		'''
		self.conn = db_conn		
		if self.conn == None:
			raise Error('No connection to database.')

	def getlayer(self, tablename):
		'''Get a PostGIS table by name and return as OGR layer.
		
		   Else, return None. 
		   
		   tablename - string - name of table to return as OGR Layer
		   
		   '''
	
		sql = "SELECT * from pg_tables WHERE tablename = '%s'" % tablename 
		
		for row in self.conn.ExecuteSQL(sql):
			if row.tablename is None:
				return None
			else:
				return self.conn.GetLayerByName(tablename)		   
	
	def netgeometry(self, key, data):
		'''Create OGR geometry from a NetworkX Graph using Wkb/Wkt attributes.
		
		key - could be str or tuple
		data - attribute dictionary
		
		'''	
		
		# Borrowed from nx_shp.py.		
		if data.has_key('Wkb'):								
			geom = ogr.CreateGeometryFromWkb(data['Wkb'])
		elif data.has_key('Wkt'):						
			geom = ogr.CreateGeometryFromWkt(data['Wkt'])
		#elif type(key[0]) == 'tuple': # edge keys are packed tuples		
		#CHANGED FOR FIXING PAJEK IMPORT (29/11/2012)
		elif ((type(key[0]) == 'tuple') or (type(key[0]) == tuple)): # edge keys are packed tuples						
			geom = ogr.Geometry(ogr.wkbLineString)
			#geom = ogr.Geometry(ogr.wkbMultiLineString)
			_from, _to = key[0], key[1]
			geom.SetPoint_2D(0, *_from)
			geom.SetPoint_2D(1, *_to)				
		#CHANGED FOR FIXING GEXF IMPORT (04/12/2012)
		elif ((type(key) == 'str') or (type(key) == str)):			
			coordinate_tuple = eval(key)			
			geom = ogr.Geometry(ogr.wkbPoint)
			geom.SetPoint_2D(0, *coordinate_tuple)
		#CHANGED FOR FIXING GEPHI IMPORT (05/12/2012)
		elif ((type(key[0]) == 'str') or (type(key[0]) == str)):
			geom = ogr.Geometry(ogr.wkbLineString)
			_from, _to = eval(key[0]), eval(key[1])
			geom.SetPoint_2D(0, *_from)
			geom.SetPoint_2D(1, *_to)
			
		else:						 			
			geom = ogr.Geometry(ogr.wkbPoint)
			geom.SetPoint_2D(0, *key)
		return geom
	
	def create_feature(self, lyr, attributes = None, geometry = None):
		'''Wrapper for OGR CreateFeature function.
		
		Creates a feature in the specified table with geometry and attributes.
		
		lyr - OGR layer to add fields to
		attributes - dict - dictionary of attributes to add to feature
		geometry - OGR Geometry - sets geometry for a feature
		
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
		returns attribute dictionary.
		
		lyr - OGR layer to add fields to
		g_obj - dict - contains data-specific fields to add to lyr
		fields - dict - contains generic node, edge or edge_geometry fields
		
		'''

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
		'''Update the Graph table and return newly assigned Graph ID.
		
		graph - networkx graph
		
		'''
		#add a graph record based on the prefix (graph / network name)
		result = nisql(self.conn).add_graph_record(self.prefix)

		sql = ('SELECT "GraphID" FROM "Graphs" ORDER BY "GraphID" DESC\
					LIMIT 1;')
		GraphID = None
		for row in self.conn.ExecuteSQL(sql):
			GraphID = row.GraphID

		return GraphID
		
	def pgnet_edge(self, edge_attributes, edge_geom):
		'''Write an edge to Edge and Edge_Geometry tables.
		
		edge_attributes - dictionary of edge attributes to add to edge feature
		edge_geom - OGR geometry - geometry of node to write to database
		
		'''
		
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
			if type(data) == unicode:
				data = data.encode('utf-8')
				
			featedge.SetField(field, data)

		self.lyredges.CreateFeature(featedge)
		
	def pgnet_node(self, node_attributes, node_geom):
		'''Write a node to a Node table.
		
		Return the newly assigned NodeID.
		
		node_attributes - dict - dictionary of node attributes to add to a node feature
		node_geom - OGR geometry - geometry of node to write to database
		
		'''		
		
		
		featnode = ogr.Feature(self.lyrnodes_def)		
		NodeID = nisql(self.conn).node_geometry_equality_check(self.prefix,node_geom,self.srs)	
		
		if NodeID == None: # Need to create new geometry:
			featnode.SetGeometry(node_geom)
		
			for field, data in node_attributes.iteritems():
				#added to handle when reading back in from graphml or similar
				if type(data) == unicode:
					data = data.encode('utf-8')
				
				featnode.SetField(field, data)
			
			self.lyrnodes.CreateFeature(featnode)
			sql = ('SELECT "NodeID" FROM "%s" ORDER BY "NodeID" DESC LIMIT 1;'
					% self.tblnodes)
			
			for row in self.conn.ExecuteSQL(sql):
				NodeID = row.NodeID
		
		return NodeID

	def pgnet(self, network, tablename_prefix, srs=27700, overwrite=False,
		directed = False, multigraph = False):
			
		'''Write NetworkX instance to PostGIS network schema tables.
		
		Updates Graph table with new network.
	
		Note that schema constrains must be applied in database. 
		There are no checks for database errors here.
		
		network - networkx network
		tablename_prefix - string - name to give to graph / network when stored in the database
		srs - integer - epsg code of input graph / network
		overwrite - boolean - true to overwrite graph / network of same name in database, false otherwise
		directed - boolean - true to write a directed graph / network, false otherwise
		multigraph - boolean - true to write a multigraph, false otherwise
		
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
		
		result = nisql(self.conn).create_network_tables(self.prefix, self.srs, directed, multigraph)
		
		#check if network tables were created
		if result == 0 or result == None:
			if overwrite is True:
				nisql(self.conn).delete_network(self.prefix)
				result = nisql(self.conn).create_network_tables(self.prefix, self.srs, directed, multigraph)
			else:
				raise Error('Network already exists.')
		
		G = network # Use G as network, networkx convention.
		#grab graph / network id from database
		graph_id = self.update_graph_table(network)
		
		if graph_id == None:
			raise Error('Could not load network from Graphs table.')
				
		self.lyredges = self.getlayer(self.tbledges)
		self.lyrnodes = self.getlayer(self.tblnodes)		
		self.lyredge_geom = self.getlayer(self.tbledge_geom)  
		self.lyrnodes_def =  self.lyrnodes.GetLayerDefn()
		
		#define default field types for Node and Edge fields
		node_fields = {'GraphID':ogr.OFTInteger}  
		edge_fields = {'Node_F_ID':ogr.OFTInteger, 'Node_T_ID':ogr.OFTInteger, 'GraphID':ogr.OFTInteger, 'Edge_GeomID':ogr.OFTInteger}
		
		for e in G.edges(data=True):
			if not multigraph:
				data = G.get_edge_data(*e)				
			else:
				data = G.get_edge_data(e[0], e[1], e[2]['uuid'])
			
			#define the edge geometry
			edge_geom = self.netgeometry(e, data)	   
			
			# Insert the start node			
			node_attrs = self.create_attribute_map(self.lyrnodes, G.node[e[0]], 
												   node_fields)
						
			node_attrs['GraphID'] = graph_id 
			#grab the node geometry
			node_geom = self.netgeometry(e[0], G.node[e[0]])
			#write the geometry to the database, and return the id
			node_id = self.pgnet_node(node_attrs, node_geom)						
			
			G[e[0]][e[1]]['Node_F_ID'] = node_id
			
			# Insert the end node			
			node_attrs = self.create_attribute_map(self.lyrnodes, G.node[e[1]], node_fields)			
			node_attrs['GraphID'] = graph_id
						
			#grab the node geometry
			node_geom = self.netgeometry(e[1], G.node[e[1]])			
			#write the geometry to the database, and return the id
			node_id = self.pgnet_node(node_attrs, node_geom)
			
			G[e[0]][e[1]]['Node_T_ID'] = node_id
						
			# Set graph id.
			G[e[0]][e[1]]['GraphID'] = graph_id

			#set the edge attributes
			edge_attrs = self.create_attribute_map(self.lyredges, e[2], edge_fields)
			
			#add the edge and attributes to the database
			self.pgnet_edge(edge_attrs, edge_geom)
			
		#execute create node view
		nisql(self.conn).create_node_view(self.prefix)			
		
		#execute create edge view
		nisql(self.conn).create_edge_view(self.prefix)
	
	def add_attribute_fields(self, lyr, g_obj, fields):
		'''
		function to add fields to a layer
		
		lyr - OGR layer to add fields to
		g_obj - dict - contains data-specific fields to add to lyr
		fields - dict - contains generic node, edge or edge_geometry fields
		
		'''
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
	
	def pgnet_via_csv(self, network, tablename_prefix, srs=27700, overwrite=False, directed = False, multigraph = False, output_csv_folder='D://Spyder//NetworkInterdependency//network_scripts//pgnet_via_csv//'):
		
		'''
		function to write networkx network instance (network) to the database schema, via COPY from CSV
		- node table written out as csv (to output_csv_folder + tablename_prefix + '_Nodes' e.g. OSMeridian2_Rail_CSV_w_nt_Nodes.csv)
		- edge table written out as csv (to output_csv_folder + tablename_prefix + '_Edges' e.g. OSMeridian2_Rail_CSV_w_nt_Edges.csv)
		- edge_geometry table written out as csv (to output_csv_folder + tablename_prefix + '_Edge_Geometry' e.g. OSMeridian2_Rail_CSV_w_nt_Edge_Geometry.csv)
		- use PostgreSQL COPY command to copy csv file to PostGIS / PostgreSQL tables
		
		network - networkx graph/network
		tablename_prefix - string - name to give as prefix to network tables created in database
		srs - integer - epsg code for coordinate system of graph/network
		overwrite - boolean - true to overwrite network of same name, false otherwise
		directed - boolean - true to denote a directed graph/network, false otherwise
		multigraph - boolean - true to denote a multigraph, false otherwise
		output_csv_folder - string - path to folder on disk, where intermediate csv files can be written to
		'''
		
		# Disable pg use copy or NodeID not-null error will be raised
		if gdal.GetConfigOption("PG_USE_COPY") == "YES":
			raise Error('Attempting to write database schema with GDAL option '
						'"PG_USE_COPY=YES". Please do: '
						'gdal.SetConfigOption("PG_USE_COPY", "NO") and reset '
						'database connection.')		
		
		#check that the output csv folder exists before proceeding
		if not os.path.isdir(output_csv_folder):
			raise Error('The output path does not exist at: %s' % (output_csv_folder))
		
		# First create network tables in database
		self.prefix = tablename_prefix		
		self.tbledges = tablename_prefix+'_Edges'
		self.tblnodes = tablename_prefix+'_Nodes'
		self.tbledge_geom = tablename_prefix+'_Edge_Geometry'
		self.srs = srs
		
		#create the network tables in the database
		#this OK to leave in the CSV writing version of the function because we need the correct GraphID inside each CSV file
		result = nisql(self.conn).create_network_tables(self.prefix, self.srs, directed, multigraph)
		
		#create network tables
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
			#do we need to do this slightly differently for a directed multigraph?
			
			#get the data for the current edge in the network
			#ORIGINAL
			
			if not multigraph:
				data = G.get_edge_data(*e)
			else:
				data = G.get_edge_data(e[0], e[1], e[2]['uuid'])						
			
			#get edge geometry
			geom = self.netgeometry(e, data)

			#get from node geometry as wkt
			node_from_geom = self.netgeometry(e[0], G.node[e[0]])			 
			node_from_geom_wkt = ogr.Geometry.ExportToWkt(node_from_geom)			   
			
			#get to node geometry as wkt
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
							
						
			edge_geom = self.netgeometry(e, data)
			edge_geom_wkt = ogr.Geometry.ExportToWkt(edge_geom)						
			
			#define empty edge geometry attribute dictionary
			edge_geometry_attrs = []
			
			#edge geometry as wkt						
			edge_geom_wkt_final = 'srid=%s;%s' % (srs, str(edge_geom_wkt))
			
			#add wkt version of edge_geometry
			edge_geometry_attrs.append(edge_geom_wkt_final)
			
			#add GeomID
			edge_geometry_attrs.append(current_edge_id)
			
			#increment the edge id
			current_edge_id = current_edge_id + 1
			
			#check if node from, or node to attributes have been defined
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
									
		#delete dictionaries of node ids and coordinates
		del node_ids
		del node_coords
		
		#close csv files
		node_csv_file.close()
		edge_geom_csv_file.close()
		edge_csv_file.close()
				
		#checking capitals for table names		
		matches = re.findall('[A-Z]', self.prefix)
		
		#determine if to add double-quotes to table names
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
		
		#execute create node view sql
		nisql(self.conn).create_node_view(self.prefix)			
		
		#execute create edge view sql
		nisql(self.conn).create_edge_view(self.prefix)
