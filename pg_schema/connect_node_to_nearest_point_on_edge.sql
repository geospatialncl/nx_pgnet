--TO DO
--return all edge_geometry attributes in output table - currently just those derived
--return all edge_geometry edges, regardless of needing to be joined or not

--joins the geometry of an edge from edge_geometry within the specified search distance of the nodes from the input node table to the closest point on the edge (not necessarily the edge end)
--$1 - prefix of edge table 
--$2 - edge geometry column name e.g. "geom"
--$3 - edge table join key
--$4 - prefix of node table
--$5 - node geometry column name e.g. "geom"
--$6 - node table primary key
--$7 - output table name (will be suffixed with _join when joined back to the original edge data
--$8 - add output to geometry columns (adds default geom column, additional_geom, and additional_combined_geom to geometry columns table)
--$9 - search distance (m)
CREATE OR REPLACE FUNCTION ni_connect_nodes_to_nearest_point_on_nearest_edge_in_search(varchar, varchar, varchar, varchar, varchar, varchar, varchar, boolean, numeric)
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
	
	edge_table_suffix varchar := '_Edges';
	edge_table_name varchar := '';
	node_table_suffix varchar := '_Nodes';
	node_table_name varchar := '';
	edge_geometry_table_suffix varchar := '_Edge_Geometry';
	edge_geometry_table_name varchar := '';
		
	node_record RECORD;		
	edge_geometry_record RECORD;
	
	edge_table_exists integer := 0;
	edge_geometry_table_exists integer := 0;
	node_table_exists integer := 0;
	
	edge_geometry_linestring_record RECORD;
	
	edge_geom text;
	st_line_locate_point_result numeric := 0;
	st_line_interpolate_point_result text := '';

	--the newly derived edge geometry
	new_edge_geometry text := '';
	--the newly combined edge geometry (new_edge_geometry + original geometry)
	new_combined_edge_geometry text := '';
	--to determine if the edge table has a geometry column (which it should not)
	
	line_string_geom_counter integer := 0;
	--for determining the closest point following shortest distance < search_distance ranking
	closest_point_on_edge_ranking_record RECORD;
	--for storing the distance between the current node and the interpolated point on the edge
	point_to_node_distance numeric := 0;
	
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
	
	--remove the output table if it already exists
	EXECUTE 'DROP TABLE IF EXISTS '||quote_ident(output_table_name);	
	--create the output table of given name based on the attributes and columns found in the edge_geometry table
	--create a temporary table to store the new derived and combined geometry
	EXECUTE 'CREATE TEMP TABLE '||quote_ident(output_table_name)||' (gid_copy integer, node_to_point_distance numeric, additional_geom geometry, additional_combined_geom geometry)';
	
	--add geometry checks for the newly derived geometry to the temporary table (additional_geom)
	EXECUTE 'ALTER TABLE '||quote_ident(output_table_name)||' ADD CONSTRAINT "enforce_srid_additional_geom" CHECK (st_srid(additional_geom) = '||edge_geometry_table_srid||')';
	EXECUTE 'ALTER TABLE '||quote_ident(output_table_name)||' ADD CONSTRAINT "enforce_geotype_additional_geom" CHECK (geometrytype(additional_geom) = ''MULTILINESTRING''::text OR geometrytype(additional_geom) = ''LINESTRING''::text OR additional_geom IS NULL)';
	
	--add a geometry checks for the newly derived geometry + original geometry to the temporary table (additional_combined_geom)
	EXECUTE 'ALTER TABLE '||quote_ident(output_table_name)||' ADD CONSTRAINT "enforce_srid_additional_combined_geom" CHECK (st_srid(additional_geom) = '||edge_geometry_table_srid||')';
	EXECUTE 'ALTER TABLE '||quote_ident(output_table_name)||' ADD CONSTRAINT "enforce_geotype_additional_combined_geom" CHECK (geometrytype(additional_combined_geom) = ''MULTILINESTRING''::text OR geometrytype(additional_combined_geom) = ''LINESTRING''::text OR additional_combined_geom IS NULL)';

	--loop around all the nodes
	FOR node_record IN EXECUTE 'SELECT ST_AsText('||quote_ident(node_geometry_column_name)||') AS geom, node_table.* FROM '||quote_ident(node_table_name)||' AS node_table' LOOP		
		--loop around all the edges (geometries)
		--FOR edge_geometry_record IN EXECUTE 'SELECT ST_AsText('||quote_ident(edge_geometry_column_name)||') AS geom, ST_NumGeometries('||quote_ident(edge_geometry_column_name)||') as edge_geom_count, edge_geometry_table.* FROM '||quote_ident(edge_geometry_table_name)||' AS edge_geometry_table WHERE ST_Intersects(ST_GeomFromText(ST_AsText(edge_geometry_table.'||quote_ident(edge_geometry_column_name)||'), '||edge_geometry_table_srid||'), expand(ST_GeomFromText('||quote_literal(node_record.geom)||', '||node_table_srid||'), '||search_distance||')) ORDER BY gid ' LOOP
		FOR edge_geometry_record IN EXECUTE 'SELECT ST_AsText('||quote_ident(edge_geometry_column_name)||') AS geom, ST_NumGeometries('||quote_ident(edge_geometry_column_name)||') as edge_geom_count, edge_geometry_table.'||quote_ident(edge_join_key_column_name)||' as gid, edge_geometry_table.* FROM '||quote_ident(edge_geometry_table_name)||' AS edge_geometry_table ORDER BY '||quote_ident(edge_join_key_column_name)||' ASC' LOOP
			
			--RAISE NOTICE 'edge_geometry_record.edge_geom_count: %', edge_geometry_record.edge_geom_count;
			--single geometry stored e.g. linestring or multilinestring with only one linestring
			IF edge_geometry_record.edge_geom_count = 1 THEN
				
				--get the first geometry (as there is only one geometry within the multilinestring)
				EXECUTE 'SELECT ST_AsText(ST_GeometryN(ST_GeomFromText('||quote_literal(edge_geometry_record.geom)||', '||edge_geometry_table_srid||'), 1))' INTO edge_geom;				
				--RAISE NOTICE 'edge_geom: %', edge_geom;
				
				--reset the locate point result to 0
				st_line_locate_point_result := 0;
				
				--interpolate along the current edge, at what fraction of the total length does the node lie at
				EXECUTE 'SELECT ST_Line_Locate_Point(ST_GeomFromText('||quote_literal(edge_geom)||', '||edge_geometry_table_srid||'), ST_GeomFromText('||quote_literal(node_record.geom)||', '||node_table_srid||'))' INTO st_line_locate_point_result;				
				
				--RAISE NOTICE 'SINGLE GEOM: st_line_locate_point_result: %, ', st_line_locate_point_result;
					
				--create a point on the edge, based on the fraction calculated in st_line_locate_point_result
				EXECUTE 'SELECT AsText(ST_Line_Interpolate_Point(ST_GeomFromText('||quote_literal(edge_geom)||', '||edge_geometry_table_srid||'), '||st_line_locate_point_result||'))' INTO st_line_interpolate_point_result;
				--RAISE NOTICE 'st_line_interpolate_point_result: %, ', st_line_interpolate_point_result;
				
				EXECUTE 'SELECT ST_Distance(ST_GeomFromText('||quote_literal(st_line_interpolate_point_result)||', '||edge_geometry_table_srid||'), ST_GeomFromText('||quote_literal(node_record.geom)||', '||node_table_srid||'))' INTO point_to_node_distance;
				--RAISE NOTICE 'point_to_node_distance: %', point_to_node_distance;
				
				IF point_to_node_distance <= search_distance THEN
				
					--create a line that links the node with the interpolated point on the line (additional_geom in output table)
					EXECUTE 'SELECT ST_AsText(ST_MakeLine(ST_GeomFromText('||quote_literal(node_record.geom)||', '||node_table_srid||'), ST_GeomFromText('||quote_literal(st_line_interpolate_point_result)||', '||edge_geometry_table_srid||')))' INTO new_edge_geometry;
					
					--create a line that combines the original edge geometry with the newly derived geometry (additional_combined_geom in the output table)
					EXECUTE 'SELECT ST_AsText(ST_Union(ST_GeomFromText('||quote_literal(edge_geom)||', '||edge_geometry_table_srid||'), ST_GeomFromText('||quote_literal(new_edge_geometry)||', '||edge_geometry_table_srid||')))' INTO new_combined_edge_geometry;
					
					--insert a record in to the output table 
					EXECUTE 'INSERT INTO '||quote_ident(output_table_name)|| '(gid_copy, node_to_point_distance, additional_geom, additional_combined_geom) VALUES ('||edge_geometry_record.gid||', '||point_to_node_distance||', ST_GeomFromText('||quote_literal(new_edge_geometry)||', '||edge_geometry_table_srid||'), ST_GeomFromText('||quote_literal(new_combined_edge_geometry)||', '||edge_geometry_table_srid||'))';
				END IF;
				
			ELSIF edge_geometry_record.edge_geom_count > 1 THEN
				RAISE NOTICE 'multiple geometries in multilinestring';
				
				EXECUTE 'DROP TABLE IF EXISTS closest_point_on_edge_ranking ';
				--create a temp table to store the ranked values on linestring
				EXECUTE 'CREATE TEMP TABLE closest_point_on_edge_ranking (gid_copy integer, node_to_point_distance numeric, additional_geom geometry, additional_combined_geom geometry)';			
				
				--1-based index for ST_GeometryN
				line_string_geom_counter := 1;
				
				--loop around every geometry because we cannot use the line_locate_point function on multilinestring								
				FOR i IN 1..edge_geometry_record.edge_geom_count LOOP
				
					--get the current geometry whilst looping all linestrings of multilinestring
					EXECUTE 'SELECT ST_AsText(ST_GeometryN(ST_GeomFromText('||quote_literal(edge_geometry_record.geom)||', '||edge_geometry_table_srid||'), '||line_string_geom_counter||')) as edge_linestring_geom' INTO edge_geometry_linestring_record;
					
					--find a point on the line based on the linestring geometry and the chosen node					
					st_line_locate_point_result := 0;
					--find the fraction of total line length that closest point to node is (0-1)
					EXECUTE 'SELECT ST_Line_Locate_Point(ST_GeomFromText('||quote_literal(edge_geometry_linestring_record.edge_linestring_geom)||', '||edge_geometry_table_srid||'), ST_GeomFromText('||quote_literal(node_record.geom)||', '||node_table_srid||'))' INTO st_line_locate_point_result;
					
					--create a point based on the fraction returned by ST_Line_Locate_Point
					EXECUTE 'SELECT AsText(ST_Line_Interpolate_Point(ST_GeomFromText('||quote_literal(edge_geom)||', '||edge_geometry_table_srid||'), '||st_line_locate_point_result||'))' INTO st_line_interpolate_point_result;
					--RAISE NOTICE 'st_line_interpolate_point_result: %, ', st_line_interpolate_point_result;
					
					--calculate the distance between this newly created point and the chosen node
					EXECUTE 'SELECT ST_Distance(ST_GeomFromText('||quote_literal(st_line_interpolate_point_result)||', '||edge_geometry_table_srid||'), ST_GeomFromText('||quote_literal(node_record.geom)||', '||node_table_srid||'))' INTO point_to_node_distance;
					
					--create a new line
					EXECUTE 'SELECT ST_AsText(ST_MakeLine(ST_GeomFromText('||quote_literal(node_record.geom)||', '||node_table_srid||'), ST_GeomFromText('||quote_literal(st_line_interpolate_point_result)||', '||edge_geometry_table_srid||')))' INTO new_edge_geometry;
					
					--create a line that combines the original edge geometry with the newly derived geometry (additional_combined_geom in the output table)
					EXECUTE 'SELECT ST_AsText(ST_Union(ST_GeomFromText('||quote_literal(edge_geometry_record.geom)||', '||edge_geometry_table_srid||'), ST_GeomFromText('||quote_literal(new_edge_geometry)||', '||edge_geometry_table_srid||')))' INTO new_combined_edge_geometry;
					
					--add the newly created values 
					RAISE NOTICE 'add link to closest_point_on_edge_ranking';
					EXECUTE 'INSERT INTO closest_point_on_edge_ranking (gid_copy, node_to_point_distance, additional_geom, additional_combined_geom) VALUES ('||edge_geometry_record.gid||', '||point_to_node_distance||', ST_GeomFromText('||quote_literal(new_edge_geometry)||', 27700), ST_GeomFromText('||quote_literal(new_combined_edge_geometry)||', 27700))';	
					
					line_string_geom_counter := line_string_geom_counter + 1;
				END LOOP;
				
				FOR closest_point_on_edge_ranking_record IN EXECUTE 'SELECT gid_copy as gid_copy, ST_AsText(additional_geom) as additional_geom, ST_AsText(additional_combined_geom) as additional_combined_geom, node_to_point_distance as node_to_point_distance FROM closest_point_on_edge_ranking WHERE node_to_point_distance <= '||search_distance||' ORDER BY node_to_point_distance ASC' LOOP
					
					EXECUTE 'INSERT INTO '||quote_ident(output_table_name)|| ' (gid_copy, node_to_point_distance, additional_geom, additional_combined_geom) VALUES ('||edge_geometry_record.gid||','||closest_point_on_edge_ranking_record.node_to_point_distance||', ST_GeomFromText('||quote_literal(closest_point_on_edge_ranking_record.additional_geom)||', 27700), ST_GeomFromText('||quote_literal(closest_point_on_edge_ranking_record.additional_combined_geom)||', 27700))';
					
				END LOOP;
				
				
			END IF;		
		END LOOP;
	
	END LOOP;
		
	--create the new join table name as a combination of the join suffix and supplied output table name
	join_table_name := output_table_name||join_table_suffix;
	
	--create the new join table
	EXECUTE 'CREATE TABLE '||quote_ident(join_table_name)||' AS SELECT * FROM '||quote_ident(edge_table_name)||' LEFT OUTER JOIN '||quote_ident(output_table_name)||' ON ('||quote_ident(edge_table_name)||'.'||quote_ident(edge_join_key_column_name)||' = '||quote_ident(output_table_name)||'.gid_copy)';
	
	--add a comment stating what function was used to create the output table
	EXECUTE 'COMMENT ON TABLE '||quote_ident(join_table_name)|| ' IS ''This table was created using the ni_connect_nodes_to_nearest_point_on_nearest_edge_in_search function. Please see the network_interdependency schema for more details of the parameters required for this function, and what it does''';
	
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
	
	--delete the table of rankings for multilinestring
	EXECUTE 'DROP TABLE IF EXISTS closest_point_on_edge_ranking';
	
		--remove the temporary table
	--EXECUTE 'DROP TABLE IF EXISTS '||quote_ident(output_table_name);
	
	--add the resultant output table to the geometry columns table(adds references to the original data (geom), additional geometry created linking the edge with the node (additional_geom), additional_combined_geom created as a union of geom and additional_geom
	IF add_to_geometry_columns IS TRUE THEN
		RAISE NOTICE 'Adding to geometry columns - geom';
		EXECUTE 'SELECT * FROM ni_add_to_geometry_columns('||quote_literal(join_table_name)||', '''', '||quote_literal(schema_name)||','||quote_literal(edge_geometry_column_name)||','||dims||','||edge_geometry_table_srid||', '||quote_literal(edge_geometry_type)||')';
		
		RAISE NOTICE 'Adding to geometry columns - additional_geom';
		EXECUTE 'SELECT * FROM ni_add_to_geometry_columns('||quote_literal(join_table_name)||', '''', '||quote_literal(schema_name)||',''additional_geom'','||dims||','||edge_geometry_table_srid||', '||quote_literal(edge_geometry_type)||')';
		
		RAISE NOTICE 'Adding to geometry columns - additional_combined_geom';
		EXECUTE 'SELECT * FROM ni_add_to_geometry_columns('||quote_literal(join_table_name)||', '''', '||quote_literal(schema_name)||',''additional_combined_geom'','||dims||','||edge_geometry_table_srid||', '||quote_literal(edge_geometry_type)||')';		
	END IF;	
	RAISE NOTICE 'execute select all from output table';
	RETURN QUERY EXECUTE 'SELECT * FROM '||quote_ident(output_table_name);
END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
ALTER FUNCTION ni_connect_nodes_to_nearest_point_on_nearest_edge_in_search(varchar, varchar, varchar, varchar, varchar, varchar, varchar, boolean, numeric) OWNER TO postgres; 