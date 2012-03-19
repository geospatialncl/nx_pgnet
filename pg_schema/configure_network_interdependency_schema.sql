--function to reset the database, based on the supplied schema name
--$1 = schema name to perform the reset operation on e.g. 'public'
CREATE OR REPLACE FUNCTION ni_reset_database(varchar)
RETURNS void AS 
$BODY$
DECLARE

    --ALIAS for schema_name input parameter
    schema_name ALIAS for $1;
    
    --for storing records from the information_schema table
    information_schema_record RECORD;
    
    --generic network interdependency tables
    parent_node_table_name varchar := 'Nodes';
    parent_edges_table_name varchar := 'Edges';
    parent_edge_geometry_table_name varchar := 'Edge_Geometry';
    graphs_table_name varchar := 'Graphs';
    global_interdependency_table_name varchar := 'Global_Interdependency';
    interdependency_table_name varchar := 'Interdependency';
    interdependency_edge_table_name varchar := 'Interdependency_Edges';
    
    --generic view suffixes
    edge_edge_geometry_view_suffix varchar := '_View_Edges_Edge_Geometry';
    interdependency_interdependency_edge_view_suffix varchar := '_View_Interdependency_Interdependency_Edges';
    
    --generic postgis tables - NOT TO DELETE
    geography_columns_table_name varchar := 'geography_columns';
    geometry_columns_table_name varchar := 'geometry_columns';
    spatial_ref_sys_table_name varchar := 'spatial_ref_sys';

BEGIN

    --delete tables, not including Nodes, Edges, Edge_Geometry, Graphs, Global Interdependency, geometry_columns, geography_columns, spatial_ref_sys
    FOR information_schema_record IN EXECUTE 'SELECT * FROM information_schema.tables WHERE table_type != ''VIEW'' AND table_schema = '||quote_literal(schema_name)||' AND table_name != '||quote_literal(parent_node_table_name)||' AND table_name != '||quote_literal(parent_edges_table_name)||' AND table_name != '||quote_literal(parent_edge_geometry_table_name)||' AND table_name != '||quote_literal(graphs_table_name)||' AND table_name != '||quote_literal(global_interdependency_table_name)||' AND table_name != '||quote_literal(geometry_columns_table_name)||' AND table_name != '||quote_literal(spatial_ref_sys_table_name)||' AND table_name != '||quote_literal(geography_columns_table_name)||' AND table_name != '||quote_literal(interdependency_table_name)||' AND table_name != '||quote_literal(interdependency_edge_table_name) LOOP
        --remove the table and dependencies using CASCADE        
        EXECUTE 'DROP TABLE IF EXISTS '||quote_ident(information_schema_record.table_name)||' CASCADE';
    END LOOP;
    
    --need to write some code to remove the views between edge and edge_geometry, and interdependency and interdependency_edge    
    FOR information_schema_record IN EXECUTE 'SELECT * FROM information_schema.views WHERE table_schema = '||quote_literal(schema_name)||' AND table_name LIKE ''%'||edge_edge_geometry_view_suffix||''' OR table_name LIKE ''%'||interdependency_interdependency_edge_view_suffix||'''' LOOP
        --remove the interdependency and edge views
        EXECUTE 'DROP VIEW IF EXISTS'||quote_ident(information_schema_record.table_name)||' CASCADE';
        EXECUTE 'DELETE FROM '||quote_ident(geometry_columns_table_name)||' WHERE f_table_name = '||quote_literal(information_schema_record.table_name);
    END LOOP;
    
    --remove all records from the graph table
    --remove all records from the geometry_columns table        
    EXECUTE 'DELETE FROM '||quote_ident(global_interdependency_table_name);
    EXECUTE 'DELETE FROM '||quote_ident(graphs_table_name);
    EXECUTE 'DELETE FROM '||quote_ident(geometry_columns_table_name);
    
    --reset graph sequence
    --reset global interdependency sequence
    ALTER SEQUENCE "Graphs_GraphID_seq" RESTART WITH 1;
    ALTER SEQUENCE "Global_Interdependency_InterdependencyID_seq" RESTART WITH 1;

    
END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
ALTER FUNCTION ni_reset_database(varchar) OWNER TO postgres; 



--function to delete a network (only removes the _Nodes, _Edges, _Edge_Geometry tables); 
--$1 = table_prefix
CREATE OR REPLACE FUNCTION ni_delete_network(varchar)
RETURNS void AS
$BODY$
DECLARE
    --table prefix to assign to nodes, edge and edge_geometry table
    table_prefix ALIAS for $1;
    
    --constant node table suffix
    node_table_suffix varchar := '_Nodes';
    --constant edge table suffix
    edge_table_suffix varchar := '_Edges';
    --constant edge_geometry table suffix
    edge_geometry_table_suffix varchar := '_Edge_Geometry';
    
    --constant interdependency suffix
    interdependency_table_suffix varchar := '_Interdependency';
    --constant interdependency edge suffix
    interdependency_edge_table_suffix varchar := '_Interdependency_Edges';
    
    --generic view suffixes
    node_view_suffix varchar := '_View_Nodes';
    edge_edge_geometry_view_suffix varchar := '_View_Edges_Edge_Geometry';
    interdependency_interdependency_edge_view_suffix varchar := '_View_Interdependency_Interdependency_Edges';
    
    --to determine which interdependency tables to delete
    interdependency_prefix_like_comparator varchar := '';
    interdependency_suffix_like_comparator varchar := '';
    interdependency_edge_suffix_like_comparator varchar := '';
    
    --node table name (table_prefix+node_table_suffix)
    node_table_name_to_delete varchar := '';
    --edge table name (table_prefix+edge_table_suffix)
    edge_table_name_to_delete varchar := '';
    --edge geometry table name (table_prefix+edge_geometry_table_suffix)
    edge_geometry_table_name_to_delete varchar := '';
    
    --record from the information_schema table
    information_schema_record RECORD;
    
    --network graph id
    graph_id integer := 0;
    
    --network graph count
    graph_count integer := -1;
    
    --constant geometry column table name
    geometry_column_table_name varchar := 'geometry_columns';
    
    --database schema name
    schema_name varchar := '';
BEGIN

    --delete the associated interdependencies
    --find all tables in the public schema with table prefix in    
    interdependency_prefix_like_comparator := table_prefix||'%';
    interdependency_suffix_like_comparator := '%'||interdependency_table_suffix;
    interdependency_edge_suffix_like_comparator := '%'||interdependency_edge_table_suffix;
    
    
    --remove the views from the geometry columns table
    FOR information_schema_record IN EXECUTE 'SELECT * FROM information_schema.views WHERE table_schema = '||quote_literal(schema_name)||' AND table_name LIKE ''%'||edge_edge_geometry_view_suffix||''' OR table_name LIKE ''%'||interdependency_interdependency_edge_view_suffix||''' OR table_name LIKE ''%'||node_view_suffix||'''' LOOP
        --remove the interdependency and edge views
        EXECUTE 'DROP VIEW IF EXISTS'||quote_ident(information_schema_record.table_name)||' CASCADE';
        EXECUTE 'DELETE FROM '||quote_ident(geometry_column_table_name)||' WHERE f_table_name = '||quote_literal(information_schema_record.table_name);
    END LOOP;
    
    --remove the tables from information_schema
    FOR information_schema_record IN EXECUTE 'SELECT table_name FROM information_schema.tables WHERE table_schema = '||quote_literal(schema_name)||' AND table_name LIKE '||quote_literal(interdependency_prefix_like_comparator)||' AND (table_name LIKE '||quote_literal(interdependency_suffix_like_comparator)||' OR table_name LIKE '||quote_literal(interdependency_edge_suffix_like_comparator)||')' LOOP
        --drop the interdependency table        
        EXECUTE 'DROP TABLE IF EXISTS '||quote_ident(information_schema_record.table_name)||' CASCADE';
        
    END LOOP;
    
    
    --determine if there are any graphs of that name
    EXECUTE 'SELECT count(*) FROM "Graphs" WHERE "GraphName" = '||quote_literal(table_prefix) INTO graph_count;
    --if there are graphs, then get the ID of it and delete the interdependency records 
    IF graph_count > 0 THEN
        
        --determine the graph id for the current graph/network to be deleted
        EXECUTE 'SELECT "GraphID" FROM "Graphs" WHERE "GraphName" = '||quote_literal(table_prefix) INTO graph_id;
        
        --remove the records from Global_Interdependency table that reference the network to be deleted
        EXECUTE 'DELETE FROM "Global_Interdependency" WHERE "InterdependencyFromGraphID" = '||graph_id||' OR "InterdependencyToGraphID" = '||graph_id;
    
    END IF;
    
    --create node table name
    node_table_name_to_delete := table_prefix||node_table_suffix;
    
    --create edge table name
    edge_table_name_to_delete := table_prefix||edge_table_suffix;
    
    --create edge_geometry table name
    edge_geometry_table_name_to_delete := table_prefix||edge_geometry_table_suffix;
    
    --delete the edge table
    EXECUTE 'DROP TABLE IF EXISTS '||quote_ident(edge_table_name_to_delete)||' CASCADE';
    
    --remove the edge_geometry table
    EXECUTE 'DROP TABLE IF EXISTS '||quote_ident(edge_geometry_table_name_to_delete)||' CASCADE';
    
    --remove the node table
    EXECUTE 'DROP TABLE IF EXISTS '||quote_ident(node_table_name_to_delete);
    
    --remove the records from the graphs table
    EXECUTE 'DELETE FROM "Graphs" WHERE "GraphName" = '||quote_literal(table_prefix);
    
    RETURN;
END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
ALTER FUNCTION ni_delete_network(varchar) OWNER TO postgres; 


--function to check that the supplied SRID number, matches a record in the spatial_ref_sys table
--$1 = SRID (integer) value to check e.g. 27700
CREATE OR REPLACE FUNCTION ni_check_srid(integer)
RETURNS boolean AS
$BODY$
DECLARE 

    --supplied EPSG code
    srid ALIAS for $1;
    
    --count of EPSG codes matching given code
    srid_exists integer := 0;
    
BEGIN

    --count of matching EPSG codes
    EXECUTE 'SELECT COUNT(*) FROM spatial_ref_sys WHERE srid = '||srid INTO srid_exists;
    
    --return true if srid exists, false otherwise
    IF srid_exists > 0 THEN
        RETURN TRUE;
    ELSE
        RETURN FALSE;
    END IF;
    
END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
ALTER FUNCTION ni_check_srid(integer) OWNER TO postgres;      

--function that runs to create the necessary network tables
--order of execution of functions IS IMPORTANT because the Edges table references the Nodes and Edge_Geometry tables
--1) Nodes
--2) Edge_Geometry
--3) Edges 
--$1 = table_prefix (this will be applied to all the nodes, edges and edge_geometry tables)
--$2 = SRID used for the nodes and edge_geometry tables
--$3 = directed network
--$4 = multigraph network
CREATE OR REPLACE FUNCTION ni_create_network_tables(varchar, integer, boolean, boolean)
RETURNS boolean AS
$BODY$
DECLARE

    --table prefix to assign to nodes, edge and edge_geometry table
    table_prefix ALIAS for $1;
	
    --srid to apply to the nodes and edge_geometry tables
    srid ALIAS for $2;

    --directed network boolean
    directed ALIAS for $3;
    
    --multigraph network boolean
    multigraph ALIAS for $4;
    
	--check srid result
	check_srid_result boolean := False;
	
    --to store the results of running the individual create network table functions
    create_network_table_nodes_result boolean := FALSE;
    create_network_table_edge_result boolean := FALSE;
    create_network_table_edge_geometry_result boolean := FALSE;
    
BEGIN
    
	--check that the srid exists
	EXECUTE 'SELECT * FROM ni_check_srid('||srid||')' INTO check_srid_result;
	
	IF check_srid_result IS FALSE THEN
		RETURN FALSE;
	END IF;
	
    --create network node table
    EXECUTE 'SELECT * FROM ni_create_network_table_nodes('||quote_literal(table_prefix)||', '||srid||')' INTO create_network_table_nodes_result;
    RAISE NOTICE 'create_network_table_nodes_result: %', create_network_table_nodes_result;
    IF create_network_table_nodes_result IS FALSE THEN
        --need to rollback things created by nodes table
        RETURN FALSE;
    END IF;
    
    --create network edge_geometry table
    EXECUTE 'SELECT * FROM ni_create_network_table_edge_geometry('||quote_literal(table_prefix)||', '||srid||')' INTO create_network_table_edge_geometry_result;   
    RAISE NOTICE 'create_network_table_edge_geometry_result: %', create_network_table_edge_geometry_result;
    IF create_network_table_edge_geometry_result IS FALSE THEN
        --need to rollback things created by edge_geometry table
        RETURN FALSE;
    END IF;
    
    --create network edges table
    EXECUTE 'SELECT * FROM ni_create_network_table_edges('||quote_literal(table_prefix)||')' INTO create_network_table_edge_result;
    RAISE NOTICE 'create_network_table_edge_result: %', create_network_table_edge_result; 
    IF create_network_table_edge_result IS FALSE THEN
        --need to rollback things created by edges table
        RETURN FALSE;
    END IF;
    
    IF create_network_table_nodes_result IS TRUE AND create_network_table_edge_geometry_result IS TRUE AND create_network_table_edge_result IS TRUE THEN
        EXECUTE 'SELECT * FROM ni_add_fr_constraints('||quote_literal(table_prefix)||')';
        EXECUTE 'SELECT * FROM ni_add_graph_record('||quote_literal(table_prefix)||', '||directed||', '||multigraph||')';
    END IF;
    
    --return true when all tables successfully created
    RETURN TRUE;
END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
ALTER FUNCTION ni_create_network_tables(varchar, integer, boolean, boolean) OWNER TO postgres;      

--function to create an empty nodes table
--$1 = table_prefix
--$2 = SRID (as geometry stored in nodes table)
CREATE OR REPLACE FUNCTION ni_create_network_table_nodes(varchar, integer)
RETURNS boolean AS
$BODY$ 
DECLARE

    --constant node table suffix
    node_table_suffix varchar := '_Nodes';
    
    --base node table to inherit from
    inherit_node_table_name varchar := 'Nodes';
    
    --new node table name to create
    new_node_table_name varchar := '';
    
    --unique table prefix e.g. Electricity
    table_prefix ALIAS for $1;
    
    --SRID (EPSG code) of data to be stored in table of name new_node_table_name
    table_srid ALIAS for $2;
    
    --boolean to store check if table of new_node_table_name already exists
    table_exists boolean := FALSE;
    
    --boolean to store check if the supplied SRID is valid i.e. exists in spatial_ref_sys
    srid_exists boolean := FALSE;
    
    --default schema name
    schema_name varchar := 'public';
    
    --default geometry column name
    node_geometry_col_name varchar := 'geom';
    
    --default coord dim
    node_geometry_coord_dim integer := 2;
    
    --node_geometry_type
    node_geometry_type varchar := 'POINT';
    
    --default catalog name
    catalog_name varchar := '';
BEGIN

    --set the new node table name
    new_node_table_name := table_prefix||node_table_suffix;

    --check to see if the new node table to be created already exists
    EXECUTE 'SELECT EXISTS (SELECT * FROM information_schema.tables WHERE table_name = '||quote_literal(new_node_table_name)||')' INTO table_exists;
    
    --check to see that the SRID supplied is valid
    EXECUTE 'SELECT * FROM ni_check_srid('||table_srid||')' INTO srid_exists;    
    
    --the supplied srid code does not exist in the spatial_ref_sys table on the current database i.e. an invalid SRID integer has been supplied
    IF srid_exists IS FALSE THEN
        RETURN FALSE;
    END IF;
    
    IF table_exists IS TRUE THEN
        --if a table of <table_prefix>_Nodes already exists in the database, return FALSE
        RETURN FALSE;
    ELSE
       
        --create the node table based on the provided table suffix (arg1) and the constant node_table_suffix, by inheriting from the base node table (inherit_node_table_name)        
        EXECUTE 'CREATE TABLE '||quote_ident(new_node_table_name)||'() INHERITS ('||quote_ident(inherit_node_table_name)||')';

        --add spatial constraints - srid check             
        EXECUTE 'ALTER TABLE '||quote_ident(new_node_table_name)||' ADD CONSTRAINT "enforce_srid_geom" CHECK (st_srid(geom) = '||table_srid||')';
        
        --to ensure that a new sequence exists for each new node table
        EXECUTE 'ALTER TABLE '||quote_ident(new_node_table_name)||' ADD COLUMN "NodeID" bigserial';
        
        --to ensure that the new sequence is used as the primary key
        EXECUTE 'ALTER TABLE '||quote_ident(new_node_table_name)||' ADD CONSTRAINT '||new_node_table_name||'_prkey PRIMARY KEY ("NodeID")';       
        
        --add this new node table to the geometry columns table
        EXECUTE 'SELECT * FROM ni_add_to_geometry_columns('||quote_literal(new_node_table_name)||', '''', '||quote_literal(schema_name)||', '||quote_literal(node_geometry_col_name)||', '||node_geometry_coord_dim||','||table_srid||','||quote_literal(node_geometry_type)||')';
        
        RETURN TRUE;
    END IF;
    
END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
ALTER FUNCTION ni_create_network_table_nodes(varchar, integer) OWNER TO postgres;  

--function to create an empty edge table
--$1 = table_prefix
CREATE OR REPLACE FUNCTION ni_create_network_table_edges(varchar)
RETURNS boolean AS
$BODY$ 
DECLARE
    --constant edge table suffix
    edge_table_suffix varchar := '_Edges';
    
    --base edge table to inherit from
    inherit_edge_table_name varchar := 'Edges';
    
    --new edge table name to create
    new_edge_table_name varchar := '';
    
    --equivalent edge geometry table name, that will be "paired" with the edge table created as a result of running this function
    equivalent_edge_geometry_table_name varchar := '';
    
    --constant edge_geometry table suffix
    equivalent_edge_geometry_table_suffix varchar := '_Edge_Geometry';
    
    --equivalent node table name, that will be referenced by the Node_F_ID and Node_T_ID attributes of the edge table created as a result of running this function
    equivalent_node_table_name varchar := '';
    
    --constant node table suffix
    equivalent_node_table_suffix varchar := '_Nodes';
    
    --supplied table prefix e.g. Electricity
    table_prefix ALIAS for $1;
    
    --these checks attempt to ensure that the equivalent edge_geometry and node tables already exist prior to creating the edge table
    --boolean to store check if edge table of supplied name already exists
    edge_table_exists boolean := FALSE;
    
    --boolean to store check if an edge_geometry table "paired" with "this" edge table already exists
    edge_geometry_table_exists boolean := FALSE;
    
    --boolean to store check if the node table "paired" with "this" edge table already exists
    node_table_exists boolean := FALSE;
BEGIN

    --generate appropriate table names for edge, edge_geometry and node tables
    new_edge_table_name := table_prefix||edge_table_suffix;
    equivalent_edge_geometry_table_name := table_prefix||equivalent_edge_geometry_table_suffix;
    equivalent_node_table_name := table_prefix||equivalent_node_table_suffix;
    
    --check if the nodes table exists
    EXECUTE 'SELECT EXISTS (SELECT * FROM information_schema.tables WHERE table_name = '||quote_literal(equivalent_node_table_name)||')' INTO node_table_exists;
    
    IF node_table_exists IS FALSE THEN
        --if the equivalent nodes table does not exist, return FALSE, because the foreign key constraints implemented on the nodes table will fail    
        RETURN FALSE;
    END IF;
    
    --check if the edge_geometry table exists
    EXECUTE 'SELECT EXISTS (SELECT * FROM information_schema.tables WHERE table_name = '||quote_literal(equivalent_edge_geometry_table_name)||')' INTO edge_geometry_table_exists;
    
    IF edge_geometry_table_exists IS FALSE THEN
        --if the equivalent edge_geometry table does not exist, return FALSE because the foreign key constraints implemented on the edge table will fail
        RETURN FALSE;
    END IF;
    
    --check if an edges table of the same name has already been created
    EXECUTE 'SELECT EXISTS (SELECT * FROM information_schema.tables WHERE table_name = '||quote_literal(new_edge_table_name)||')' INTO edge_table_exists;
    
    IF edge_table_exists IS TRUE THEN
        --if a table of <table_prefix>_Edges already exists in the database, return FALSE
        RETURN FALSE;
    ELSE
        
        --create the edge table based on the provided table suffix (arg1) and the constant edge_table_suffix, by inheriting from the base edges table (inherit_edge_table_name)      
        EXECUTE 'CREATE TABLE '||quote_ident(new_edge_table_name)||'() INHERITS ('||quote_ident(inherit_edge_table_name)||')';
        
        --to ensure that a new sequence exists for each new edge table
        EXECUTE 'ALTER TABLE '||quote_ident(new_edge_table_name)||' ADD COLUMN "EdgeID" bigserial';
        
        --to ensure that the new sequence is used as the primary key
        EXECUTE 'ALTER TABLE '||quote_ident(new_edge_table_name)||' ADD CONSTRAINT '||new_edge_table_name||'_prkey PRIMARY KEY ("EdgeID")';
        
        RETURN TRUE;
    END IF;
   
END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
ALTER FUNCTION ni_create_network_table_edges(varchar) OWNER TO postgres;  

--function to create an empty edge geometry table
--$1 = table_prefix
--$2 = SRID (as geometry stored in edge geometry table)
CREATE OR REPLACE FUNCTION ni_create_network_table_edge_geometry(varchar, integer)
RETURNS boolean AS
$BODY$ 
DECLARE
    --constant edge geometry table suffix
    edge_geometry_table_suffix varchar := '_Edge_Geometry';
    
    --base edge table to inherit from
    inherit_edge_geometry_table_name varchar := 'Edge_Geometry';
    
    --new edge table name to create
    new_edge_geometry_table_name varchar := '';
    
    --supplied table prefix e.g. Electricity
    table_prefix ALIAS for $1;    
    
    --SRID (EPSG code) of data to be stored in table of name new_edge_geometry_table_name_table_name
    table_srid ALIAS for $2;
    
    --boolean to store check if the supplied SRID is valid i.e. exists in spatial_ref_sys
    srid_exists boolean := FALSE;
    
    --boolean to store check if an edge_geometry table already exists
    edge_geometry_table_exists boolean := FALSE;    

    --constants (could be exposed as parameters)
    schema_name varchar := 'public';
    geometry_column_name varchar := 'geom';
    dims integer := 2;
    edge_geometry_type varchar := 'LINESTRING';
    
    
BEGIN

    --create the new edge geometry table name
    new_edge_geometry_table_name := table_prefix||edge_geometry_table_suffix;
    
    --check to see that the SRID supplied is valid
    EXECUTE 'SELECT * FROM ni_check_srid('||table_srid||')' INTO srid_exists;    
    
	--check if the edge geometry table exists
    EXECUTE 'SELECT EXISTS (SELECT * FROM information_schema.tables WHERE table_name = '||quote_literal(new_edge_geometry_table_name)||')' INTO edge_geometry_table_exists;
	
    --the supplied srid code does not exist in the spatial_ref_sys table on the current database i.e. an invalid SRID integer has been supplied
    IF srid_exists IS FALSE THEN
        RETURN FALSE;
    END IF;
    
    IF edge_geometry_table_exists IS TRUE THEN
        --if the equivalent edge_geometry table does exist, return FALSE
        RETURN FALSE;
    ELSE
        --create the edge_geometry table        
        EXECUTE 'CREATE TABLE '||quote_ident(new_edge_geometry_table_name)||'() INHERITS ('||quote_ident(inherit_edge_geometry_table_name)||')';

        EXECUTE 'ALTER TABLE '||quote_ident(new_edge_geometry_table_name)||' ADD CONSTRAINT "enforce_srid_geom" CHECK (st_srid(geom) = '||table_srid||')';
             
        --to ensure that a new sequence exists for each new edge table
        EXECUTE 'ALTER TABLE '||quote_ident(new_edge_geometry_table_name)||' ADD COLUMN "GeomID" bigserial';
        
        --to ensure that the new sequence is used as the primary key
        EXECUTE 'ALTER TABLE '||quote_ident(new_edge_geometry_table_name)||' ADD CONSTRAINT '||new_edge_geometry_table_name||'_prkey PRIMARY KEY ("GeomID")';
        
        --add the edge_geometry table to the geometry_columns table
        EXECUTE 'SELECT * FROM ni_add_to_geometry_columns('||quote_literal(new_edge_geometry_table_name)||', '''', '||quote_literal(schema_name)||', '||quote_literal(geometry_column_name)||', '||dims||','||table_srid||','||quote_literal(edge_geometry_type)||')';
        
        RETURN TRUE;
    END IF;
END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
ALTER FUNCTION ni_create_network_table_edge_geometry(varchar, integer) OWNER TO postgres;  

--generic function to add table to geometry columns table
--$1 = table_name
--$2 = catalog name
--$3 = schema name
--$4 = geometry column name
--$5 = coordinate dimension of input geometry
--$6 = coordinate reference system (EPSG code)
--$7 = geometry type e.g. POINT, LINESTRING, MULTILINESTRING
CREATE OR REPLACE FUNCTION ni_add_to_geometry_columns(varchar, varchar, varchar, varchar, integer, integer, varchar)
RETURNS boolean AS
$BODY$ 
DECLARE
    --table name to insert
    table_name ALIAS for $1;

    --table_catalog
    table_catalog ALIAS for $2;
    
    --table schema
    table_schema ALIAS for $3;
    
    --table geometry column name
    geometry_column_name ALIAS for $4;
    
    --coordinate dimensions of input geometry
    coord_dim ALIAS for $5;
    
    --coordinate reference system (EPSG code)
    SRID ALIAS for $6;
    
    --geometry type e.g. POINT, LINESTRING
    geometry_type ALIAS for $7;
    
    --geometry_column_table_name
    geometry_column_table_name varchar := 'geometry_columns';
    geometry_column_record_exists integer := 0;

    srid_exists boolean := FALSE;
BEGIN

    EXECUTE 'SELECT * FROM ni_check_srid('||srid||')' INTO srid_exists;
    
    IF srid_exists IS FALSE THEN
        RETURN FALSE;
    ELSE 
        
        EXECUTE 'SELECT COUNT(*) FROM '||quote_ident(geometry_column_table_name)||' WHERE f_table_catalog = '||quote_literal(table_catalog)||' AND f_table_schema = '||quote_literal(table_schema)||' AND f_table_name = '||quote_literal(table_name)||' AND f_geometry_column = '||quote_literal(geometry_column_name)||' AND coord_dimension = '||coord_dim||' AND srid = '||SRID INTO geometry_column_record_exists;
        
        IF geometry_column_record_exists < 1 THEN
            --currently defaulting to 2 coord dim
            EXECUTE 'INSERT INTO '||quote_ident(geometry_column_table_name)||' (f_table_catalog, f_table_schema, f_table_name, f_geometry_column, coord_dimension, srid, "type") VALUES ('||quote_literal(table_catalog)||', '||quote_literal(table_schema)||', '||quote_literal(table_name)||', '||quote_literal(geometry_column_name)||', '||coord_dim||', '||srid||', '||quote_literal(geometry_type)||')';
        END IF;
        RETURN TRUE;
    END IF;

RETURN FALSE;
END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
ALTER FUNCTION ni_add_to_geometry_columns(varchar, varchar, varchar, varchar, integer, integer, varchar) OWNER TO postgres;  


--function to add the appropriate foreign key relationships to the nodes, edges and edge_geometry tables
--$1 table prefix
CREATE OR REPLACE FUNCTION ni_add_fr_constraints(varchar)
RETURNS boolean AS
$BODY$ 
DECLARE
    
    --table prefix to identify particular network
    table_prefix ALIAS for $1;
    node_table_name varchar := '';
    edge_table_name varchar := '';
    edge_geometry_table_name varchar := '';
    
    --constant network interdependency table suffixes
    node_table_suffix varchar := '_Nodes';
    edge_table_suffix varchar := '_Edges';
    edge_geometry_table_suffix varchar := '_Edge_Geometry';
    
BEGIN
    
    --creates the appropriate table names based on the supplied prefix, and constant suffixes. 
    node_table_name := table_prefix||node_table_suffix;
    edge_table_name := table_prefix||edge_table_suffix;
    edge_geometry_table_name := table_prefix||edge_geometry_table_suffix;
    
    --NODES
    --add the foreign key constraint matching this new Node table to the correct record in the 'global' Graphs table    
    EXECUTE 'ALTER TABLE '||quote_ident(node_table_name)||' ADD CONSTRAINT '||node_table_name||'_Graphs_GraphID_frkey FOREIGN KEY ("GraphID") REFERENCES "Graphs" ("GraphID") MATCH SIMPLE ON UPDATE NO ACTION ON DELETE NO ACTION';
    
    --EDGES table foreign keys to nodes table
    --add foreign key Edges_Nodes_Node_F_ID_frkey    
    EXECUTE 'ALTER TABLE '||quote_ident(edge_table_name)||' ADD CONSTRAINT "'||edge_table_name||'_Edges_Nodes_Node_F_ID_frkey" FOREIGN KEY  ("Node_F_ID") REFERENCES '||quote_ident(node_table_name)||' ("NodeID") MATCH SIMPLE ON UPDATE NO ACTION ON DELETE NO ACTION';
    
    --add foreign key Edges_Nodes_Node_T_ID_frkey    
    EXECUTE 'ALTER TABLE '||quote_ident(edge_table_name)||' ADD CONSTRAINT "'||edge_table_name||'_Edges_Nodes_Node_T_ID_frkey" FOREIGN KEY ("Node_T_ID") REFERENCES '||quote_ident(node_table_name)||' ("NodeID") MATCH SIMPLE ON UPDATE NO ACTION ON DELETE NO ACTION';
    
    --edges table foreign keys to edge_geometry table
    EXECUTE 'ALTER TABLE '||quote_ident(edge_table_name)||' ADD CONSTRAINT "'||edge_table_name||'_Edges_Edge_Geometry_GeomID_frkey" FOREIGN KEY ("Edge_GeomID") REFERENCES '||quote_ident(edge_geometry_table_name)||' ("GeomID") MATCH SIMPLE ON UPDATE NO ACTION ON DELETE CASCADE';
    
    --foreign key to graphs (graphid) - Edges_Graph_GraphID_frkey - graphs table will ALWAYS exist    
    EXECUTE 'ALTER TABLE '||quote_ident(edge_table_name)||' ADD CONSTRAINT '||edge_table_name||'_Graph_GraphID_frkey FOREIGN KEY ("GraphID") REFERENCES "Graphs" ("GraphID") MATCH SIMPLE ON UPDATE NO ACTION ON DELETE NO ACTION';
    
RETURN TRUE;
END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
ALTER FUNCTION ni_add_fr_constraints(varchar) OWNER TO postgres;  

--function to add a new record to the Graphs table i.e. define a new graph
--$1 = table prefix i.e. graph name
--$2 = boolean denoting if the graph is directed
--$3 = boolean denoting if the graph is a multigraph
CREATE OR REPLACE FUNCTION ni_add_graph_record(varchar, boolean, boolean) RETURNS void AS
$BODY$ 
DECLARE
    
    --table prefix to identify a particular graph/network
    table_prefix ALIAS for $1;
    
    --denotes if the network is directed (true if directed)    
    directed ALIAS for $2;
    
    --denotes if the network is a multigraph (true if directed)d
    multigraph ALIAS for $3;
    
    --constant table suffixes 
    node_table_suffix varchar := '_Nodes';
    edge_table_suffix varchar := '_Edges';

BEGIN

    RAISE NOTICE 'multigraph: %', multigraph;
    RAISE NOTICE 'directed: %', directed;
    

    --add the new network/graph record to the Graphs table
    EXECUTE 'INSERT INTO "Graphs" ("GraphName", "Nodes", "Edges", "Directed", "MultiGraph") VALUES ('||quote_literal(table_prefix)||', '||quote_literal(table_prefix||node_table_suffix)||', '||quote_literal(table_prefix||edge_table_suffix)||', '||directed||', '||multigraph||')';
    RETURN;
    
END;
$BODY$
LANGUAGE 
plpgsql VOLATILE
COST 100;
ALTER FUNCTION ni_add_graph_record(varchar, boolean, boolean) OWNER TO postgres;  

--function to create a view that allows the node table to be read in to QGIS
--$1 = table prefix
CREATE OR REPLACE FUNCTION ni_create_node_view(varchar) RETURNS varchar AS
$BODY$
DECLARE
    --user supplied table prefix
    table_prefix ALIAS for $1;
    
    --constant node table suffix
    node_table_suffix varchar := '_Nodes';
    node_view_suffix varchar := '_View_Nodes';
    new_node_view_name varchar := '';
    node_table_name varchar := '';
	
    --to hold the information on the geometry columns of the node table
    SRID integer := 0;
    dims integer := 0;
    
    --geometry_column_record_count
    geometry_column_record_count integer := 0;
    
    --node type
    node_geometry_type varchar := '';
    
    --constant geometry column table name
    geometry_column_table_name varchar := 'geometry_columns';
    
    schema_name varchar := 'public';
    
    geometry_column_name varchar := 'geom';
BEGIN
    
    --original node table name
    node_table_name := table_prefix||node_table_suffix;
    
    --create the new node view table name
    new_node_view_name := table_prefix||node_view_suffix;

    --create node view
    EXECUTE 'CREATE OR REPLACE VIEW '||quote_ident(new_node_view_name)||' AS SELECT int4(ROW_NUMBER() over (order by node_table."NodeID")) as id, node_table.* FROM '||quote_ident(node_table_name)||' as node_table';
    
    --retrieve the SRID of the node view
    EXECUTE 'SELECT ST_SRID(geom) FROM '||quote_ident(node_table_name) INTO SRID;
    
    --retrieve the dims of the node view
    EXECUTE 'SELECT ST_Dimension(geom) FROM '||quote_ident(node_table_name) INTO dims;
    
    --retrieve the geometry type for the node view
    EXECUTE 'SELECT GeometryType(geom) FROM '||quote_ident(node_table_name) INTO node_geometry_type;
    
    EXECUTE 'SELECT COUNT(*) FROM '||quote_ident(geometry_column_table_name)||' WHERE f_table_schema = ''public'' AND f_table_name = '||quote_literal(new_node_view_name) INTO geometry_column_record_count;
    
    RAISE NOTICE 'geometry_column_record_count: %', geometry_column_record_count;
    --add the view to the geometry columsn table
    IF geometry_column_record_count < 1 THEN
        --need to add the view to the geometry columns table here
        --EXECUTE 'INSERT INTO '||quote_ident(geometry_column_table_name)||' (f_table_catalog, f_table_schema, f_table_name, f_geometry_column, coord_dimension, srid, "type") VALUES ('''', ''public'', '||quote_literal(new_node_view_name)||',''geom'', '||dims||', '||SRID||', '||quote_literal(node_geometry_type)||')';
        EXECUTE 'SELECT * FROM ni_add_to_geometry_columns('||quote_literal(new_node_view_name)||', '''', '||quote_literal(schema_name)||', '||quote_literal(geometry_column_name)||', '||dims||','||SRID||','||quote_literal(node_geometry_type)||')';
    END IF;
    
    --return the new view name to the user
    RETURN new_node_view_name;
    
END;
$BODY$
LANGUAGE 
plpgsql VOLATILE
COST 100;
ALTER FUNCTION ni_create_node_view(varchar) OWNER TO postgres;  

--function to create a view that joins the edge and edge_geometry tables, based on the supplied table prefix
--$1 = table prefix
CREATE OR REPLACE FUNCTION ni_create_edge_view(varchar) RETURNS varchar AS
$BODY$
DECLARE
    --user supplied table prefix
    table_prefix ALIAS for $1;
    
    --constant edge table suffix
    edge_table_suffix varchar := '_Edges';
    edge_table_name varchar := '';
    
    --constant edge_geometry table suffix
    edge_geometry_table_suffix varchar := '_Edge_Geometry';
    edge_geometry_table_name varchar := '';
    
    --constant value to use for creating the new edge to edge_geometry view (join)
    edge_view_suffix varchar := '_View_Edges_Edge_Geometry';
    new_edge_view_name varchar := '';
    
    --to hold the information on the geometry columns of the edge_geometry table
    SRID integer := 0;
    dims integer := 0;
    
    --geometry_column_record_count
    geometry_column_record_count integer := 0;
        
    --constant geometry column table name
    geometry_column_table_name varchar := 'geometry_columns';
    
    --edge_geometry type
    edge_geometry_type varchar := '';
    
    --schema name
    schema_name varchar := 'public';
    
    geometry_column_name varchar := 'geom';
BEGIN
    --create the new edge view table name
    new_edge_view_name := table_prefix||edge_view_suffix;
    
    --specify the edge table to join
    edge_table_name := table_prefix||edge_table_suffix;
    
    --specify the edge_geometry table to join
    edge_geometry_table_name := table_prefix||edge_geometry_table_suffix;
    
    --create the view by joining the edge and edge_geometry tables for tables with a specific prefix
    --EXECUTE 'CREATE OR REPLACE VIEW '||quote_ident(new_edge_view_name)||' AS SELECT * FROM '||quote_ident(edge_table_name)||', '||quote_ident(edge_geometry_table_name)||' WHERE "EdgeID" = "GeomID"';
    
    --this creates a view of the two edge and edge_geometry tables - this works in QGIS
    EXECUTE 'CREATE OR REPLACE VIEW '||quote_ident(new_edge_view_name)||' AS SELECT int4(ROW_NUMBER() over (order by edge_table."EdgeID")) as id, edge_table.*, edge_geometry_table.* FROM '||quote_ident(edge_table_name)||' as edge_table, '||quote_ident(edge_geometry_table_name)||' as edge_geometry_table WHERE edge_table."EdgeID" = edge_geometry_table."GeomID"';
    
    --retrieve the SRID of the edge_geometry table
    EXECUTE 'SELECT ST_SRID(geom) FROM '||quote_ident(edge_geometry_table_name) INTO SRID;
    
    --retrieve the dims of the edge_geometry table
    EXECUTE 'SELECT ST_Dimension(geom) FROM '||quote_ident(edge_geometry_table_name) INTO dims;
    
    --retrieve the geometry type for the edge geometry table
    EXECUTE 'SELECT GeometryType(geom) FROM '||quote_ident(edge_geometry_table_name) INTO edge_geometry_type;
    
    EXECUTE 'SELECT COUNT(*) FROM '||quote_ident(geometry_column_table_name)||' WHERE f_table_schema = ''public'' AND f_table_name = '||quote_literal(new_edge_view_name) INTO geometry_column_record_count;
    
    RAISE NOTICE 'geometry_column_record_count: %', geometry_column_record_count;
    --add the edge view to the geometry columns table
    IF geometry_column_record_count < 1 THEN
        --need to add the view to the geometry columns table here
        --EXECUTE 'INSERT INTO '||quote_ident(geometry_column_table_name)||' (f_table_catalog, f_table_schema, f_table_name, f_geometry_column, coord_dimension, srid, "type") VALUES ('''', ''public'', '||quote_literal(new_edge_view_name)||',''geom'', '||dims||', '||SRID||', '||quote_literal(edge_geometry_type)||')';
        EXECUTE 'SELECT * FROM ni_add_to_geometry_columns('||quote_literal(new_edge_view_name)||', '''', '||quote_literal(schema_name)||', '||quote_literal(geometry_column_name)||', '||dims||','||SRID||','||quote_literal(edge_geometry_type)||')';
    END IF;
    
    --return the new view name to the user
    RETURN new_edge_view_name;
    
END;
$BODY$
LANGUAGE 
plpgsql VOLATILE
COST 100;
ALTER FUNCTION ni_create_edge_view(varchar) OWNER TO postgres;  

--function to create a view that joins the interdependency and interdependency_edge tables, based on the supplied table prefix
--$1 = table prefix
CREATE OR REPLACE FUNCTION ni_create_interdependency_edge_view(varchar) RETURNS varchar AS
$BODY$
DECLARE
    
    --table prefix to identify a particular network
    table_prefix ALIAS for $1;
    
    --constant interdependency table suffixes
    interdependency_table_suffix varchar := '_Interdependency';
    interdependency_table_name varchar := '';
    
    --constant interdependency_edge table suffix
    interdependency_edge_table_suffix varchar := '_Interdependency_Edges';
    interdependency_edge_table_name varchar := '';
    
    --constant interdependency view suffix
    interdependency_view_suffix varchar := '_View_Interdependency_Interdependency_Edges';
    new_interdependency_view_name varchar := '';

    --to hold the information on the geometry columns of the interdependency_edges table
    SRID integer := 0;
    dims integer := 0;
    
    --interdependency_edge_geometry type
    interdependency_edge_geometry_type varchar := '';
    
    --constant geometry_columns table name
    geometry_column_table_name varchar := 'geometry_columns';
        
    --geometry_column_record_count
    geometry_column_record_count integer := 0;
    
    --default schema name
    schema_name varchar := 'public';
    
    --geometry column name
    geometry_column_name varchar := 'geom';
    
BEGIN

    --create the new edge view table name
    new_interdependency_view_name := table_prefix||interdependency_view_suffix;
    
    --specify the interdependency table to join
    interdependency_table_name := table_prefix||interdependency_table_suffix;
    
    --specify the interdependency_edge table to join
    interdependency_edge_table_name := table_prefix||interdependency_edge_table_suffix;

    --create the view by joining the interdependency and interdependency_edge tables for tables with a specific prefix
    
    EXECUTE 'CREATE OR REPLACE VIEW '||quote_ident(new_interdependency_view_name)||' AS SELECT int4(ROW_NUMBER() over (order by i."InterdependencyID")) as id, i.*, ie.geom FROM '||quote_ident(interdependency_table_name)||' AS i, '||quote_ident(interdependency_edge_table_name)||' as ie WHERE i."InterdependencyID" = ie."GeomID"';
    
    --add a new column to the view that acts as a primary key to overcome the issue of QGIS not accepting non-int4 types as primary keys
    --EXECUTE 'ALTER VIEW '||quote_ident(new_interdependency_view_name)||'';
        
    --retrieve the SRID of the edge_geometry table
    EXECUTE 'SELECT ST_SRID(geom) FROM '||quote_ident(interdependency_edge_table_name) INTO SRID;
    
    --retrieve the dims of the edge_geometry table
    EXECUTE 'SELECT ST_Dimension(geom) FROM '||quote_ident(interdependency_edge_table_name) INTO dims;    
        
    --retrieve the geometry type for the interdependency edge geometry table
    EXECUTE 'SELECT GeometryType(geom) FROM '||quote_ident(interdependency_edge_table_name) INTO interdependency_edge_geometry_type;
    
    EXECUTE 'SELECT COUNT(*) FROM '||quote_ident(geometry_column_table_name)||' WHERE f_table_schema = '||quote_literal(schema_name)||' AND f_table_name = '||quote_literal(new_interdependency_view_name) INTO geometry_column_record_count;
    
    --add the record to the geometry columns table
    IF geometry_column_record_count < 1 THEN
    
        --need to add the view to the geometry columns table here        
        EXECUTE 'SELECT * FROM ni_add_to_geometry_columns('||quote_literal(new_interdependency_view_name)||', '''', '||quote_literal(schema_name)||', '||quote_literal(geometry_column_name)||', '||dims||','||SRID||','||quote_literal(interdependency_edge_geometry_type)||')';
    
    END IF;
    
    --return the new view name to the user
    RETURN new_interdependency_view_name;    
    
END;
$BODY$
LANGUAGE 
plpgsql VOLATILE
COST 100;
ALTER FUNCTION ni_create_interdependency_edge_view(varchar) OWNER TO postgres;


-----------------------------------HANDLING CREATION OF INTERDEPENDENCIES-----------------------------
--function to create the appropriate, empty, interdependency and interdependency_edge tables based on the supplied network prefixes 
--two prefixes are required because the interdependency exists between two networks/graphs
--$1 = table prefix for first network
--$2 = table prefix for second network
CREATE OR REPLACE FUNCTION ni_create_interdependency_tables(varchar, varchar) RETURNS boolean AS
$BODY$ 
DECLARE
    --network prefixes
    network_1_table_prefix ALIAS for $1;
    network_2_table_prefix ALIAS for $2;
    
    --to store existence of relevant parts of a valid graph i.e. Nodes, Edges and Edge_Geometry table
    network_1_exists boolean := FALSE;
    network_2_exists boolean := FALSE;
    
    --default parent interdependency table names
    interdependency_table_name varchar := 'Interdependency';
    interdependency_edge_table_name varchar := 'Interdependency_Edges';
    
    --new interdependency tables to create (based on the supplied prefixes for the two networks that are 'interdependent'
    new_interdependency_table_name varchar := '';
    new_interdependency_edge_table_name varchar := '';
    
    --equivalent graph ids of respective networks
    network_1_graph_id integer := 0;
    network_2_graph_id integer := 0;
    
    --table name storing all interdependencies created
    global_interdependency_table_name varchar := 'Global_Interdependency';
    
    --network node table names
    network_1_node_table_name varchar := '';
    network_2_node_table_name varchar := '';
    
    --network edge table names
    network_1_edge_table_name varchar := '';
    network_2_edge_table_name varchar := '';
    
    --network graph ids
    network_1_graphid integer := 0;
    network_2_graphid integer := 0;
    
BEGIN
    
    --create the new table names based on the supplied table prefixes and the constant suffixes
    new_interdependency_table_name := network_1_table_prefix||'_'||network_2_table_prefix||'_'||interdependency_table_name;
    new_interdependency_edge_table_name := network_1_table_prefix||'_'||network_2_table_prefix||'_'||interdependency_edge_table_name;

    --check the network is created correctly
    EXECUTE 'SELECT * FROM ni_check_network_tables('||quote_literal(network_1_table_prefix)||')' INTO network_1_exists;
    EXECUTE 'SELECT * FROM ni_check_network_tables('||quote_literal(network_2_table_prefix)||')' INTO network_2_exists;
    
    --determine the equivalent GraphID values for the supplied networks
    EXECUTE 'SELECT "GraphID" FROM "Graphs" WHERE "GraphName" = '||quote_literal(network_1_table_prefix) INTO network_1_graph_id;
    EXECUTE 'SELECT "GraphID" FROM "Graphs" WHERE "GraphName" = '||quote_literal(network_2_table_prefix) INTO network_2_graph_id;
    
    --check that the networks have been created correctly.
    IF network_1_exists IS FALSE OR network_2_exists IS FALSE THEN
        RETURN FALSE;
    ELSE
    
        --retrieve the equivalent node table name for network 1
        EXECUTE 'SELECT "Nodes" FROM "Graphs" WHERE "GraphName" = '||quote_literal(network_1_table_prefix) INTO network_1_node_table_name;
        --retrieve the equivalent node table name for network 2
        EXECUTE 'SELECT "Nodes" FROM "Graphs" WHERE "GraphName" = '||quote_literal(network_2_table_prefix) INTO network_2_node_table_name;
        
        --retrieve the equivalent edge table name for network 1
        EXECUTE 'SELECT "Edges" FROM "Graphs" WHERE "GraphName" = '||quote_literal(network_1_table_prefix) INTO network_1_edge_table_name;
        --retrieve the equivalent edge table name for network 2
        EXECUTE 'SELECT "Edges" FROM "Graphs" WHERE "GraphName" = '||quote_literal(network_2_table_prefix) INTO network_2_edge_table_name;
        
        --retrieve the equivalent graph id for network 1
        EXECUTE 'SELECT "GraphID" FROM "Graphs" WHERE "GraphName" = '||quote_literal(network_1_table_prefix) INTO network_1_graphid;
        --retrieve the equivalent graph id for network 2
        EXECUTE 'SELECT "GraphID" FROM "Graphs" WHERE "GraphName" = '||quote_literal(network_2_table_prefix) INTO network_2_graphid;
        
        --Interdependency Table
        --create a child 'interdependency' table by inheriting from "Interdependency"
        EXECUTE 'CREATE TABLE '||quote_ident(new_interdependency_table_name)||'() INHERITS ('||quote_ident(interdependency_table_name)||')';
        
        --add the InterdependencyID column as a bigserial to the interdependency table
        EXECUTE 'ALTER TABLE '||quote_ident(new_interdependency_table_name)||' ADD COLUMN "InterdependencyID" bigserial ';
        --set the InterdependencyID column as the primary key for the interdependency table
        EXECUTE 'ALTER TABLE '||quote_ident(new_interdependency_table_name)||' ADD CONSTRAINT '||new_interdependency_table_name||'_prkey PRIMARY KEY ("InterdependencyID")';
        
        --Interdependency_Edge Table        
        --create a child 'interdependency_edge' table by inheriting from "Interdependency_Edge"
        EXECUTE 'CREATE TABLE '||quote_ident(new_interdependency_edge_table_name)||'() INHERITS ('||quote_ident(interdependency_edge_table_name)||')';
        
        --add the GeomID column as bigserial to the interdependency_edge table
        EXECUTE 'ALTER TABLE '||quote_ident(new_interdependency_edge_table_name)||' ADD COLUMN "GeomID" bigserial ';
        --set the GeomID column of the interdependency_edge table to be a primary key
        EXECUTE 'ALTER TABLE '||quote_ident(new_interdependency_edge_table_name)||' ADD CONSTRAINT '||new_interdependency_edge_table_name||'_prkey PRIMARY KEY ("GeomID")';       
        
        --FOREIGN KEYS
        --add a foreign key relationship to GraphID on Graph table for FROM
        EXECUTE 'ALTER TABLE '||quote_ident(new_interdependency_table_name)||' ADD CONSTRAINT "'||new_interdependency_table_name||'_Interdependency_Graphs_F_GraphID_frkey" FOREIGN KEY ("Interdependency_Graphs_F_GraphID") REFERENCES "Graphs" ("GraphID") MATCH SIMPLE ON UPDATE NO ACTION ON DELETE NO ACTION';
        
        --add a foreign key relationship to GraphID on Graph table for TO
        EXECUTE 'ALTER TABLE '||quote_ident(new_interdependency_table_name)||' ADD CONSTRAINT "'||new_interdependency_table_name||'_Interdependency_Graphs_T_GraphID_frkey" FOREIGN KEY ("Interdependency_Graphs_T_GraphID") REFERENCES "Graphs" ("GraphID") MATCH SIMPLE ON UPDATE NO ACTION ON DELETE NO ACTION';
        
        --add a foreign key relationship to equivalent node tables (network 1 = from, network 2 = to)
        --network 1 from 
        EXECUTE 'ALTER TABLE '||quote_ident(new_interdependency_table_name)||' ADD CONSTRAINT "'||new_interdependency_table_name||'_Interdependency_Nodes_F_NodeID_frkey" FOREIGN KEY ("Interdependency_Nodes_F_NodeID") REFERENCES '||quote_ident(network_1_node_table_name)||' ("NodeID") MATCH SIMPLE
      ON UPDATE NO ACTION ON DELETE NO ACTION';
        
        --network 2 to
        EXECUTE 'ALTER TABLE '||quote_ident(new_interdependency_table_name)||' ADD CONSTRAINT "'||new_interdependency_table_name||'_Interdependency_Nodes_T_NodeID_frkey" FOREIGN KEY ("Interdependency_Nodes_T_NodeID") REFERENCES '||quote_ident(network_2_node_table_name)||' ("NodeID") MATCH SIMPLE
      ON UPDATE NO ACTION ON DELETE NO ACTION';
        
        --add a foreign key relationship to GeomID of equivalent Interdependency_Edge table
        EXECUTE 'ALTER TABLE '||quote_ident(new_interdependency_table_name)||' ADD CONSTRAINT "'||new_interdependency_table_name||'_Interdependency_Interdependency_Edges_GeomID_frkey" FOREIGN KEY ("GeomID") REFERENCES '||quote_ident(new_interdependency_edge_table_name)||' MATCH SIMPLE
      ON UPDATE NO ACTION ON DELETE CASCADE';
        
        --Global Interdependency Table
        --insert a new record in to the Global_Interdependency table
        EXECUTE 'INSERT INTO '||quote_ident(global_interdependency_table_name)||' ("InterdependencyFromGraphID", "InterdependencyToGraphID", "InterdependencyTableName", "InterdependencyEdgeTableName") VALUES ('||network_1_graph_id||', '||network_2_graph_id||', '||quote_literal(new_interdependency_table_name)||', '||quote_literal(new_interdependency_edge_table_name)||')';
        RETURN TRUE;
    END IF;
    RETURN FALSE;
END;
$BODY$
LANGUAGE 
plpgsql VOLATILE
COST 100;
ALTER FUNCTION ni_create_interdependency_tables(varchar, varchar) OWNER TO postgres; 



