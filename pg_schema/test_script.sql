-----------------------RESET THE DATABASE--------------------------
SELECT * FROM ni_reset_database('public');

--delete old network
SELECT * FROM ni_delete_network('test1');
SELECT * FROM ni_delete_network('test2');

----------------------CREATE NETWORK test1----------------------------

--create a new set of network tables with table prefix "test"
SELECT * FROM ni_create_network_tables('test1', 27700, false, false);
--add geometry columns to the nodes and edge_geometry tables (cannot be created in parent table templates "Nodes" and "Edge_Geometry" because users may have different coordinate systems to the default value)
--SELECT * FROM ni_add_geometry_columns('test1', 27700);
--add the foreign key constraints between the nodes, edges, edge_geometry and graph tables
--SELECT * FROM ni_add_fr_constraints('test1');

--create a new graph (test_graph_1)
--SELECT * FROM ni_add_graph_record('test1', FALSE, FALSE);

--insert some nodes (test_graph_1)
INSERT INTO "test1_Nodes" ("GraphID", geom) VALUES((SELECT "GraphID" FROM "Graphs" ORDER BY "GraphID" DESC LIMIT 1), ST_GeomFromText('POINT(0 0)', 27700));
INSERT INTO "test1_Nodes" ("GraphID", geom) VALUES((SELECT "GraphID" FROM "Graphs" ORDER BY "GraphID" DESC LIMIT 1), ST_GeomFromText('POINT(0 1)', 27700));
INSERT INTO "test1_Nodes" ("GraphID", geom) VALUES((SELECT "GraphID" FROM "Graphs" ORDER BY "GraphID" DESC LIMIT 1), ST_GeomFromText('POINT(1 1)', 27700));
INSERT INTO "test1_Nodes" ("GraphID", geom) VALUES((SELECT "GraphID" FROM "Graphs" ORDER BY "GraphID" DESC LIMIT 1), ST_GeomFromText('POINT(1 0)', 27700));

--insert in to edge_geometry and edges tables (test_graph_1)
--always need to insert in to the edge_geometry table prior to inserting in to the edge table because we need the corresponding Edge_GeomID
INSERT INTO "test1_Edge_Geometry" (geom) VALUES (ST_GeomFromText('LINESTRING(0 0, 0 0.5, 0 1)', 27700));
INSERT INTO "test1_Edges" ("Node_F_ID", "Node_T_ID", "GraphID", "Edge_GeomID") VALUES (1, 2, (SELECT "GraphID" FROM "Graphs" ORDER BY "GraphID" DESC LIMIT 1), (SELECT "GeomID" FROM "test1_Edge_Geometry" ORDER BY "GeomID" DESC LIMIT 1)); 
INSERT INTO "test1_Edge_Geometry" (geom) VALUES (ST_GeomFromText('LINESTRING(0 1, 0.5 1, 1 1)', 27700));
INSERT INTO "test1_Edges" ("Node_F_ID", "Node_T_ID", "GraphID", "Edge_GeomID") VALUES (2, 3, (SELECT "GraphID" FROM "Graphs" ORDER BY "GraphID" DESC LIMIT 1), (SELECT "GeomID" FROM "test1_Edge_Geometry" ORDER BY "GeomID" DESC LIMIT 1));
INSERT INTO "test1_Edge_Geometry" (geom) VALUES (ST_GeomFromText('LINESTRING(1 1, 1 0.5, 1 0)', 27700));
INSERT INTO "test1_Edges" ("Node_F_ID", "Node_T_ID", "GraphID", "Edge_GeomID") VALUES (3, 4, (SELECT "GraphID" FROM "Graphs" ORDER BY "GraphID" DESC LIMIT 1), (SELECT "GeomID" FROM "test1_Edge_Geometry" ORDER BY "GeomID" DESC LIMIT 1));
INSERT INTO "test1_Edge_Geometry" (geom) VALUES (ST_GeomFromText('LINESTRING(1 0, 0.5 0, 0 0)', 27700));
INSERT INTO "test1_Edges" ("Node_F_ID", "Node_T_ID", "GraphID", "Edge_GeomID") VALUES (4, 1, (SELECT "GraphID" FROM "Graphs" ORDER BY "GraphID" DESC LIMIT 1), (SELECT "GeomID" FROM "test1_Edge_Geometry" ORDER BY "GeomID" DESC LIMIT 1));

--------------------------GRAPH 2---------------------------------


--create a new set of network tables with table prefix "test2"
SELECT * FROM ni_create_network_tables('test2', 27700, false, false);
--add geometry columns to the nodes and edge_geometry tables (cannot be created in parent table templates "Nodes" and "Edge_Geometry" because users may have different coordinate systems to the default value)
--SELECT * FROM ni_add_geometry_columns('test2', 27700);
--add the foreign key constraints between the nodes, edges, edge_geometry and graph tables
--SELECT * FROM ni_add_fr_constraints('test2');

--create a new graph (test_graph_1)
--SELECT * FROM ni_add_graph_record('test2', FALSE, FALSE);

--insert some nodes (test_graph_2)
INSERT INTO "test2_Nodes" ("GraphID", geom) VALUES((SELECT "GraphID" FROM "Graphs" ORDER BY "GraphID" DESC LIMIT 1), ST_GeomFromText('POINT(1 1)', 27700));
INSERT INTO "test2_Nodes" ("GraphID", geom) VALUES((SELECT "GraphID" FROM "Graphs" ORDER BY "GraphID" DESC LIMIT 1), ST_GeomFromText('POINT(1 2)', 27700));
INSERT INTO "test2_Nodes" ("GraphID", geom) VALUES((SELECT "GraphID" FROM "Graphs" ORDER BY "GraphID" DESC LIMIT 1), ST_GeomFromText('POINT(2 2)', 27700));
INSERT INTO "test2_Nodes" ("GraphID", geom) VALUES((SELECT "GraphID" FROM "Graphs" ORDER BY "GraphID" DESC LIMIT 1), ST_GeomFromText('POINT(2 1)', 27700));

--insert in to edge_geometry and edges tables
--always need to insert in to the edge_geometry table prior to inserting in to the edge table because we need the corresponding Edge_GeomID
INSERT INTO "test2_Edge_Geometry" (geom) VALUES (ST_GeomFromText('LINESTRING(1 1, 1 1.5, 1 2)', 27700));
INSERT INTO "test2_Edges" ("Node_F_ID", "Node_T_ID", "GraphID", "Edge_GeomID") VALUES (1, 2, (SELECT "GraphID" FROM "Graphs" ORDER BY "GraphID" DESC LIMIT 1), (SELECT "GeomID" FROM "test2_Edge_Geometry" ORDER BY "GeomID" DESC LIMIT 1)); 
INSERT INTO "test2_Edge_Geometry" (geom) VALUES (ST_GeomFromText('LINESTRING(1 2, 1.5 2, 2 2)', 27700));
INSERT INTO "test2_Edges" ("Node_F_ID", "Node_T_ID", "GraphID", "Edge_GeomID") VALUES (2, 3, (SELECT "GraphID" FROM "Graphs" ORDER BY "GraphID" DESC LIMIT 1), (SELECT "GeomID" FROM "test2_Edge_Geometry" ORDER BY "GeomID" DESC LIMIT 1));
INSERT INTO "test2_Edge_Geometry" (geom) VALUES (ST_GeomFromText('LINESTRING(2 2, 2 1.5, 2 1)', 27700));
INSERT INTO "test2_Edges" ("Node_F_ID", "Node_T_ID", "GraphID", "Edge_GeomID") VALUES (3, 4, (SELECT "GraphID" FROM "Graphs" ORDER BY "GraphID" DESC LIMIT 1), (SELECT "GeomID" FROM "test2_Edge_Geometry" ORDER BY "GeomID" DESC LIMIT 1));
INSERT INTO "test2_Edge_Geometry" (geom) VALUES (ST_GeomFromText('LINESTRING(2 1, 1.5 1, 1 1)', 27700));
INSERT INTO "test2_Edges" ("Node_F_ID", "Node_T_ID", "GraphID", "Edge_GeomID") VALUES (4, 1, (SELECT "GraphID" FROM "Graphs" ORDER BY "GraphID" DESC LIMIT 1), (SELECT "GeomID" FROM "test2_Edge_Geometry" ORDER BY "GeomID" DESC LIMIT 1));

--check the tables
SELECT * FROM ni_check_network_tables('test1');
SELECT * FROM ni_check_network_tables('test2');

--create an interdependency between network 1 and network 2
SELECT * FROM ni_create_interdependency_tables('test1', 'test2');

--insert some interdependency edges between test1 network and test2 network
--between node 1 of test1 and node 1 of test2 0 0 to 1 1
INSERT INTO "test1_test2_Interdependency_Edges" (geom) VALUES (ST_GeomFromText('LINESTRING(0 0, 0.5 0.5, 1 1)', 27700));
--between node 1 of test 1 and node 1 of test2 0 0 to 1 1
INSERT INTO "test1_test2_Interdependency" ("Interdependency_Graphs_F_GraphID", "Interdependency_Graphs_T_GraphID", "Interdependency_Nodes_F_NodeID", "Interdependency_Nodes_T_NodeID", "GeomID") VALUES ((SELECT "GraphID" FROM "Graphs" WHERE "GraphName" = 'test1'), (SELECT "GraphID" FROM "Graphs" WHERE "GraphName" = 'test2'), 1, 1, (SELECT "GeomID" FROM "test1_test2_Interdependency_Edges" ORDER BY "GeomID" DESC LIMIT 1));
--between node 2 of test1 and node 2 of test2 0 1 to 1 2
INSERT INTO "test1_test2_Interdependency_Edges" (geom) VALUES (ST_GeomFromText('LINESTRING(0 1, 0.5 1.5, 1 2)', 27700));
--between node 2 of test1 and node 2 of test2 0 1 to 1 2
INSERT INTO "test1_test2_Interdependency" ("Interdependency_Graphs_F_GraphID", "Interdependency_Graphs_T_GraphID", "Interdependency_Nodes_F_NodeID", "Interdependency_Nodes_T_NodeID", "GeomID") VALUES ((SELECT "GraphID" FROM "Graphs" WHERE "GraphName" = 'test1'), (SELECT "GraphID" FROM "Graphs" WHERE "GraphName" = 'test2'), 2, 2, (SELECT "GeomID" FROM "test1_test2_Interdependency_Edges" ORDER BY "GeomID" DESC LIMIT 1));
--between node 3 of test1 and node 3 of test2 1 1 to 2 2
INSERT INTO "test1_test2_Interdependency_Edges" (geom) VALUES (ST_GeomFromText('LINESTRING(1 1, 1.5 1.5, 2 2)', 27700));
--between node 3 of test1 and node 3 of test2 1 1 to 2 2
INSERT INTO "test1_test2_Interdependency" ("Interdependency_Graphs_F_GraphID", "Interdependency_Graphs_T_GraphID", "Interdependency_Nodes_F_NodeID", "Interdependency_Nodes_T_NodeID", "GeomID") VALUES ((SELECT "GraphID" FROM "Graphs" WHERE "GraphName" = 'test1'), (SELECT "GraphID" FROM "Graphs" WHERE "GraphName" = 'test2'), 3, 3, (SELECT "GeomID" FROM "test1_test2_Interdependency_Edges" ORDER BY "GeomID" DESC LIMIT 1));
--between node 4 of test1 and node 4 of test2 1 0 to 2 1
INSERT INTO "test1_test2_Interdependency_Edges" (geom) VALUES (ST_GeomFromText('LINESTRING(1 0, 1.5 0.5, 2 1)', 27700));
--between node 4 of test1 and node 4 of test2 1 0 to 2 1
INSERT INTO "test1_test2_Interdependency" ("Interdependency_Graphs_F_GraphID", "Interdependency_Graphs_T_GraphID", "Interdependency_Nodes_F_NodeID", "Interdependency_Nodes_T_NodeID", "GeomID") VALUES ((SELECT "GraphID" FROM "Graphs" WHERE "GraphName" = 'test1'), (SELECT "GraphID" FROM "Graphs" WHERE "GraphName" = 'test2'), 4, 4, (SELECT "GeomID" FROM "test1_test2_Interdependency_Edges" ORDER BY "GeomID" DESC LIMIT 1));
--insert some corresponding interdependencies between the two networks, test1 and test2

--check the tables
SELECT * FROM ni_check_interdependency_tables('test1', 'test2');

--create a view of edge and edge_geometry joined for test1 network
SELECT * FROM ni_create_edge_view('test1');

--create a view of edge and edge_geometry joined for test2 network
SELECT * FROM ni_create_edge_view('test2');

--create a view of the node table (to help visualise in qGIS)
SELECT * FROM ni_create_node_view('test1');

--create a view of the node table (to help visualise in qGIS)
SELECT * FROM ni_create_node_view('test2');

--create a view of the interdependency join table (to help visualise in qGIS)
SELECT * FROM ni_create_interdependency_edge_view('test1_test2');