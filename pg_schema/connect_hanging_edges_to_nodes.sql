--TODO - auto-determine the SRID for geometry in the nodes and edge_geometry tables

--connects the geometry of an edge from edge_geometry within the specified search distance of the nodes from the input node table (edge end)
--$1 - prefix of edge table 
--$2 - edge geometry column name e.g. "geom"
--$3 - edge table join key
--$4 - prefix of node table
--$5 - node geometry column name e.g. "geom"
--$6 - node table primary key
--$7 - output table name (will be suffixed with _join when joined back to the original edge data
--$8 - add output to geometry columns (adds default geom column, additional_geom, and additional_combined_geom to geometry columns table)
--$9 - search distance (m)

CREATE OR REPLACE FUNCTION ni_connect_hanging_edges_to_nodes(varchar, varchar, varchar, varchar, varchar, varchar, varchar, boolean, numeric)
RETURNS SETOF RECORD AS 
$BODY$
DECLARE
	
	--name of input edge table
	edge_table_prefix ALIAS for $1;
	
	--edge_geometry column name
	edge_geometry_column_name ALIAS for $2;
	
	--edge table join key
	edge_join_key_column_name ALIAS for $3;
	
	--name of input node table
	node_table_prefix ALIAS for $4;
	
	--node geometry column name
	node_geometry_column_name ALIAS for $5;
	
	--node table join key
	node_join_key_column_name ALIAS for $6;
	
	--name of output table
	output_table_name ALIAS for $7;	
	--boolean to add output table to geometry columns
	add_to_geometry_columns ALIAS for $8;
	--search distance between node and nearest edge
	search_distance ALIAS for $9;
	
	--constants (could be exposed as parameters)
	schema_name varchar := 'public';
	dims integer := 2;			
	edge_geometry_table_srid integer := 27700;	
	node_table_srid integer := 27700;
	edge_geometry_type varchar := 'MULTILINESTRING';
	node_geometry_type varchar := 'POINT';
	
	--table suffixes
	node_table_suffix varchar := '_Nodes';
	edge_table_suffix varchar := '_Edges';
	edge_geometry_table_suffix varchar := '_Edge_Geometry';
	
	--derived from input prefixes and table suffixes (see above)
	edge_table_name varchar := '';
	edge_geometry_table_name varchar := '';
	node_table_name varchar := '';
	
	--used to store outputs of node and edge_geometry tables (without needing to know the column structure)
	node_record RECORD;	
	edge_geometry_record RECORD;
	
	edge_table_exists integer := 0;
	edge_geometry_table_exists integer := 0;
	node_table_exists integer := 0;
	
	--distance to start point of edge from node
	distance_between_node_edge_start_point numeric := 0;
	--distance to end point of edge from node
	distance_between_node_edge_end_point numeric := 0;
	
	--end point of edge
	edge_end_point text := '';
	--start point of edge
	edge_start_point text := '';
		
	--the newly derived edge geometry
	new_edge_geometry text := '';
	--the newly combined edge geometry (new_edge_geometry + original geometry)
	new_combined_edge_geometry text := '';
	
	--derived from output_table_name + join_table_suffix
	join_table_name varchar := '';
	join_table_suffix varchar := '_join';
	
BEGIN

	--create node and edge, edge_geometry table names
	edge_table_name := edge_table_prefix||edge_table_suffix;	
	edge_geometry_table_name := edge_table_prefix||edge_geometry_table_suffix;
	node_table_name := node_table_prefix||node_table_suffix;
	
	--check the edge table exists
	EXECUTE 'SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '||quote_literal(edge_table_name) INTO edge_table_exists;
	--check the edge_geometry table exists
	EXECUTE 'SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '||quote_literal(edge_geometry_table_name)  INTO edge_geometry_table_exists;
	--check the node table exists
	EXECUTE 'SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '||quote_literal(node_table_name)  INTO node_table_exists;
	
	--raise exception if the tables do not exist or there are multiple tables of same name
	IF edge_table_exists <> 1 OR edge_geometry_table_exists <> 1 OR node_table_exists <> 1 THEN
		--there are either duplicates of the same name or the table does not exist
		RAISE EXCEPTION 'Either the edge table, corresponding edge_geometry table or the node table specified do not exist in the current database.';
	END IF;
	
	
	
	--drop the previous temporary output table
	EXECUTE 'DROP TABLE IF EXISTS '||quote_ident(output_table_name);	
	
	--create a temporary table to store the new derived and combined geometry
	EXECUTE 'CREATE TEMP TABLE '||quote_ident(output_table_name)||' (gid_copy integer, connection_point_geom geometry, additional_geom geometry, additional_combined_geom geometry)';		

	--add geometry checks for the connection point geometry to the temporary table (connection_point_geom)
	EXECUTE 'ALTER TABLE '||quote_ident(output_table_name)||' ADD CONSTRAINT "enforce_srid_connection_point_geom" CHECK (st_srid(connection_point_geom) = '||edge_geometry_table_srid||')';
	EXECUTE 'ALTER TABLE '||quote_ident(output_table_name)||' ADD CONSTRAINT "enforce_geotype_connection_point_geom" CHECK (geometrytype(connection_point_geom) = ''POINT''::text OR connection_point_geom IS NULL)';
	
	--add geometry checks for the newly derived geometry to the temporary table (additional_geom)
	EXECUTE 'ALTER TABLE '||quote_ident(output_table_name)||' ADD CONSTRAINT "enforce_srid_additional_geom" CHECK (st_srid(additional_geom) = '||edge_geometry_table_srid||')';
	EXECUTE 'ALTER TABLE '||quote_ident(output_table_name)||' ADD CONSTRAINT "enforce_geotype_additional_geom" CHECK (geometrytype(additional_geom) = ''MULTILINESTRING''::text OR geometrytype(additional_geom) = ''LINESTRING''::text OR additional_geom IS NULL)';
	
	--add a geometry checks for the newly derived geometry + original geometry to the temporary table (additional_combined_geom)
	EXECUTE 'ALTER TABLE '||quote_ident(output_table_name)||' ADD CONSTRAINT "enforce_srid_additional_combined_geom" CHECK (st_srid(additional_geom) = '||edge_geometry_table_srid||')';
	EXECUTE 'ALTER TABLE '||quote_ident(output_table_name)||' ADD CONSTRAINT "enforce_geotype_additional_combined_geom" CHECK (geometrytype(additional_combined_geom) = ''MULTILINESTRING''::text OR geometrytype(additional_combined_geom) = ''LINESTRING''::text OR additional_combined_geom IS NULL)';
	
	--add a column for the distance to the start point of the line
	EXECUTE 'ALTER TABLE '||quote_ident(output_table_name)||' ADD COLUMN start_point_distance numeric(10,0)';
	
	--add a column for the distance to the end point of the line
	EXECUTE 'ALTER TABLE '||quote_ident(output_table_name)||' ADD COLUMN end_point_distance numeric(10,0)';
	
	--loop around every node in the node table
	FOR node_record IN EXECUTE 'SELECT ST_AsText('||quote_ident(node_geometry_column_name)||') AS geom, node_table.* FROM '||quote_ident(node_table_name)||' AS node_table ORDER BY '||quote_ident(node_join_key_column_name)||' ASC' LOOP
		--loop around every edge in the edge table			
		FOR edge_geometry_record IN EXECUTE 'SELECT ST_AsText('||quote_ident(edge_geometry_column_name)||') AS geom, edge_geometry_table.'||quote_ident(edge_join_key_column_name)||' as gid, edge_geometry_table.* FROM '||quote_ident(edge_geometry_table_name)||' AS edge_geometry_table ORDER BY '||quote_ident(edge_join_key_column_name)||' ASC' LOOP
		
			--find the closest edge
			--get the start point of the edge
			EXECUTE 'SELECT ST_AsText(ST_StartPoint(ST_GeomFromText('||quote_literal(edge_geometry_record.geom)||', '||edge_geometry_table_srid||')))' INTO edge_start_point;
			
			--get the end point of the edge
			EXECUTE 'SELECT ST_AsText(ST_EndPoint(ST_GeomFromText('||quote_literal(edge_geometry_record.geom)||', '||edge_geometry_table_srid||')))' INTO edge_end_point;
			
			--calculate distance between node and the start point of the chosen edge
			EXECUTE 'SELECT ST_Distance(ST_GeomFromText('||quote_literal(edge_start_point)||', '||edge_geometry_table_srid||'), ST_GeomFromText('||quote_literal(node_record.geom)||', '||node_table_srid||'))' INTO distance_between_node_edge_start_point;
			
			--calculate distance between node and the end point of the chosen edge
			EXECUTE 'SELECT ST_Distance(ST_GeomFromText('||quote_literal(edge_end_point)||', '||edge_geometry_table_srid||'), ST_GeomFromText('||quote_literal(node_record.geom)||', '||node_table_srid||'))' INTO distance_between_node_edge_end_point;
			
			--determine if the distance to start or end point of edge is within the search distance specified
			IF distance_between_node_edge_start_point <= search_distance OR distance_between_node_edge_end_point <= search_distance THEN
							
				IF distance_between_node_edge_start_point < distance_between_node_edge_end_point AND (distance_between_node_edge_start_point <= search_distance) THEN
				
					--make a new line between the start point and node
					EXECUTE 'SELECT ST_AsText(ST_MakeLine(ST_GeomFromText('||quote_literal(node_record.geom)||', '||node_table_srid||'), ST_GeomFromText('||quote_literal(edge_start_point)||', '||edge_geometry_table_srid||')))' INTO new_edge_geometry;
					--make a new geometry of the old geometry + new line created above
					EXECUTE 'SELECT ST_AsText(ST_Union(ST_GeomFromText('||quote_literal(edge_geometry_record.geom)||', '||edge_geometry_table_srid||'), ST_GeomFromText('||quote_literal(new_edge_geometry)||', '||edge_geometry_table_srid||')))' INTO new_combined_edge_geometry;
				
					--insert the record in to the temporary output table
					EXECUTE 'INSERT INTO '||quote_ident(output_table_name)|| '(gid_copy, start_point_distance, end_point_distance, connection_point_geom, additional_geom, additional_combined_geom) VALUES ('||edge_geometry_record.gid||', '||distance_between_node_edge_start_point||', '||distance_between_node_edge_end_point||', ST_GeomFromText('||quote_literal(edge_start_point)||', '||node_table_srid||'), ST_GeomFromText('||quote_literal(new_edge_geometry)||', '||edge_geometry_table_srid||'),ST_GeomFromText('||quote_literal(new_combined_edge_geometry)||', '||edge_geometry_table_srid||'))';
					
				ELSIF distance_between_node_edge_start_point > distance_between_node_edge_end_point AND (distance_between_node_edge_end_point <= search_distance) THEN
					
					--make a new line between the end point and node
					EXECUTE 'SELECT ST_AsText(ST_MakeLine(ST_GeomFromText('||quote_literal(node_record.geom)||', '||node_table_srid||'), ST_GeomFromText('||quote_literal(edge_end_point)||', '||edge_geometry_table_srid||')))' INTO new_edge_geometry;	
					--make a new geometry of the old geometry + new line created above
					EXECUTE 'SELECT ST_AsText(ST_Union(ST_GeomFromText('||quote_literal(edge_geometry_record.geom)||', '||edge_geometry_table_srid||'), ST_GeomFromText('||quote_literal(new_edge_geometry)||', '||edge_geometry_table_srid||')))' INTO new_combined_edge_geometry;
				
					--insert the record in to the temporary output table
					EXECUTE 'INSERT INTO '||quote_ident(output_table_name)|| '(gid_copy, start_point_distance, end_point_distance, connection_point_geom, additional_geom, additional_combined_geom) VALUES ('||edge_geometry_record.gid||', '||distance_between_node_edge_start_point||', '||distance_between_node_edge_end_point||', ST_GeomFromText('||quote_literal(edge_end_point)||', '||node_table_srid||'), ST_GeomFromText('||quote_literal(new_edge_geometry)||', '||edge_geometry_table_srid||'),ST_GeomFromText('||quote_literal(new_combined_edge_geometry)||', '||edge_geometry_table_srid||'))';
				END IF;							
			END IF;
		END LOOP;
	END LOOP;
	
	--create the new join table name as a combination of the join suffix and supplied output table name
	join_table_name := output_table_name||join_table_suffix;
	
	--drop the join table
	EXECUTE 'DROP TABLE IF EXISTS '||quote_ident(join_table_name);
	
	--create the new join table
	EXECUTE 'CREATE TABLE '||quote_ident(join_table_name)||' AS SELECT * FROM '||quote_ident(edge_table_name)||' LEFT OUTER JOIN '||quote_ident(output_table_name)||' ON ('||quote_ident(edge_table_name)||'.'||quote_ident(edge_join_key_column_name)||' = '||quote_ident(output_table_name)||'.gid_copy)';
	
	--add a comment stating what function was used to create the output table
	EXECUTE 'COMMENT ON TABLE '||quote_ident(join_table_name)|| ' IS ''This table was created using the ni_connect_hanging_edges_to_nodes function. Please see the network_interdependency schema for more details of the parameters required for this function, and what it does''';
	
	--add geometry checks for the connection point geometry to the join table (connection_point_geom)
	EXECUTE 'ALTER TABLE '||quote_ident(join_table_name)||' ADD CONSTRAINT "enforce_srid_connection_point_geom" CHECK (st_srid(connection_point_geom) = '||node_table_srid||')';
	EXECUTE 'ALTER TABLE '||quote_ident(join_table_name)||' ADD CONSTRAINT "enforce_geotype_connection_point_geom" CHECK (geometrytype(connection_point_geom) = ''POINT''::text OR connection_point_geom IS NULL)';
	
	--add geometry checks for geom column to the joined table
	EXECUTE 'ALTER TABLE '||quote_ident(join_table_name)||' ADD CONSTRAINT "enforce_srid_geom" CHECK (st_srid(geom) = '||edge_geometry_table_srid||')';
	EXECUTE 'ALTER TABLE '||quote_ident(join_table_name)||' ADD CONSTRAINT "enforce_geotype_geom" CHECK (geometrytype(geom) = ''MULTILINESTRING''::text OR geometrytype(geom) = ''LINESTRING''::text OR geom IS NULL)';
	
	--add geometry checks for the newly derived geometry to the joined table
	EXECUTE 'ALTER TABLE '||quote_ident(join_table_name)||' ADD CONSTRAINT "enforce_srid_additional_geom" CHECK (st_srid(additional_geom) = '||edge_geometry_table_srid||')';
	EXECUTE 'ALTER TABLE '||quote_ident(join_table_name)||' ADD CONSTRAINT "enforce_geotype_additional_geom" CHECK (geometrytype(additional_geom) = ''MULTILINESTRING''::text OR geometrytype(additional_geom) = ''LINESTRING''::text OR additional_geom IS NULL)';
	
	--add a geometry checks for the newly derived geometry + original geometry to the joined table
	EXECUTE 'ALTER TABLE '||quote_ident(join_table_name)||' ADD CONSTRAINT "enforce_srid_additional_combined_geom" CHECK (st_srid(additional_geom) = '||edge_geometry_table_srid||')';
	EXECUTE 'ALTER TABLE '||quote_ident(join_table_name)||' ADD CONSTRAINT "enforce_geotype_additional_combined_geom" CHECK (geometrytype(additional_combined_geom) = ''MULTILINESTRING''::text OR geometrytype(additional_combined_geom) = ''LINESTRING''::text OR additional_combined_geom IS NULL)';	
	
	--remove the gid_copy column from the join table
	EXECUTE 'ALTER TABLE '||quote_ident(join_table_name)||' DROP COLUMN gid_copy';
	
	--remove the temporary table
	EXECUTE 'DROP TABLE IF EXISTS '||quote_ident(output_table_name);
	
	--add the new output join table geometry columns to the geomtry columns table (this has been joined back to the original data)
	IF add_to_geometry_columns IS TRUE THEN
		RAISE NOTICE 'Adding to geometry columns - geom';
		EXECUTE 'SELECT * FROM ni_add_to_geometry_columns('||quote_literal(join_table_name)||', '''', '||quote_literal(schema_name)||','||quote_literal(edge_geometry_table_geometry_column_name)||','||dims||','||edge_geometry_table_srid||', '||quote_literal(edge_geometry_type)||')';
		
		RAISE NOTICE 'Adding to geometry columns - connection_point_geom';
		EXECUTE 'SELECT * FROM ni_add_to_geometry_columns('||quote_literal(join_table_name)||', '''', '||quote_literal(schema_name)||',''connection_point_geom'','||dims||','||node_table_srid||', '||quote_literal(node_geometry_type)||')';
		
		RAISE NOTICE 'Adding to geometry columns - additional_geom';
		EXECUTE 'SELECT * FROM ni_add_to_geometry_columns('||quote_literal(join_table_name)||', '''', '||quote_literal(schema_name)||',''additional_geom'','||dims||','||edge_geometry_table_srid||', '||quote_literal(edge_geometry_type)||')';
		
		RAISE NOTICE 'Adding to geometry columns - additional_combined_geom';
		EXECUTE 'SELECT * FROM ni_add_to_geometry_columns('||quote_literal(join_table_name)||', '''', '||quote_literal(schema_name)||',''additional_combined_geom'','||dims||','||edge_geometry_table_srid||', '||quote_literal(edge_geometry_type)||')';
		
	END IF;
	RAISE NOTICE 'Returning records';
	RETURN QUERY EXECUTE 'SELECT * FROM '||quote_ident(join_table_name);
	
END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
ALTER FUNCTION ni_connect_hanging_edges_to_nodes(varchar, varchar, varchar, varchar, varchar, varchar, varchar, boolean, numeric) OWNER TO postgres; 