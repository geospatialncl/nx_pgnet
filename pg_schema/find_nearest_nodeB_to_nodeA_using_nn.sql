--function to find the closest node of nodeset B to each node of nodeset A
--returns all the original nodes, and attributes of nodeset A, along with the geometry of the nearest node of nodeset B, a distance to the nearest node of nodeset B, and a straight line that joins node of nodeset A to nodes of nodeset B.

CREATE OR REPLACE FUNCTION ni_find_nearest_nodeB_to_nodeA_using_nn(varchar, varchar, varchar, varchar, varchar, varchar, varchar, boolean)
RETURNS SETOF RECORD AS
$BODY$
DECLARE

	--nodeset A table_name
	nodeset_A_table_name ALIAS for $1;
	
	--nodeset A prkey
	nodeset_A_prkey ALIAS for $2;
	
	--geometry column name of nodeset A table (could be exposed as a parameter)
	nodeset_A_geometry_column_name ALIAS for $3;
	
	--nodeset B table_name
	nodeset_B_table_name ALIAS for $4;
	
	--nodeset B prkey
	nodeset_B_prkey ALIAS for $5;
	
	--geometry column name of nodeset B table (could be exposed as a parameter)
	nodeset_B_geometry_column_name ALIAS for $6;
	
	--output table name 
	output_table_name ALIAS for $7;
	
	--indicates whether or not to add the resulting output table to the geometry columns table
	add_to_geometry_columns ALIAS for $8;
	
	--dimensions 
	dims integer := 2;
	
	--schema_name 
	schema_name varchar := 'public';
	
	--could be exposed as a parameter?
	nodeset_A_srid integer := 27700;
	
	--could be exposed as a parameter?
	nodeset_B_srid integer := 27700;
	
	--srid of resultant line between nodeA and closest node of nodeset B
	node_AB_line_srid integer := 27700;
	
	--search distance result of iterations
	search_distance numeric := 0.0;
	
	--nodeset A prkey datatype
	nodeset_A_prkey_datatype varchar := '';
	
	--nodeset B prkey datatype
	nodeset_B_prkey_datatype varchar := '';
	
	--temporary table name
	temp_table_name varchar := '';
		
BEGIN
	
	--create a temporary table to store the final results, then need to join the original table back to this table
	temp_table_name := output_table_name||'_temp';
	
	--determine the datatype of nodeset A prkey
	EXECUTE 'SELECT data_type FROM information_schema.columns WHERE table_name = '||quote_literal(nodeset_A_table_name)||' AND column_name = '||quote_literal(nodeset_A_prkey) INTO nodeset_A_prkey_datatype;
	
	--determine the datatype of nodeset B prkey
	EXECUTE 'SELECT data_type FROM information_schema.columns WHERE table_name = '||quote_literal(nodeset_B_table_name)||' AND column_name = '||quote_literal(nodeset_B_prkey) INTO nodeset_B_prkey_datatype;
	
	--drop the previous temporary table
	EXECUTE 'DROP TABLE IF EXISTS '||quote_ident(temp_table_name);
	
	--create a new temporary table to store the outputs generated as a result of the function. We will then join to this table the original data
	--node A geometry (POINT)
	--node A id (unknown data type)
	--node B geometry (POINT) - closest point to node A
	--node B id (unknown data type)
	--node_AB_line - derived geometry between node A and node B (closest)
	--distance of node_AB_line
	EXECUTE 'CREATE TEMPORARY TABLE '||quote_ident(temp_table_name)||' ("node_A_id" '||nodeset_A_prkey_datatype||', "node_A_geom" geometry, "node_B_id" '||nodeset_B_prkey_datatype||', "node_B_geom" geometry, "node_AB_line" geometry, "node_AB_distance" numeric)';
	
	--find the closest node from set B to each node in set A
	EXECUTE 'INSERT INTO '||quote_ident(temp_table_name)||' ("node_A_id", "node_A_geom", "node_B_id", "node_B_geom", "node_AB_line", "node_AB_distance") SELECT DISTINCT ON("node_A_set".'||quote_ident(nodeset_A_prkey)||') "node_A_set".'||quote_ident(nodeset_A_prkey)||', "node_A_set".'||quote_ident(nodeset_A_geometry_column_name)||', "node_B_set".'||quote_ident(nodeset_B_prkey)||', "node_B_set".'||quote_ident(nodeset_B_geometry_column_name)||', ST_MakeLine("node_A_set".'||quote_ident(nodeset_A_geometry_column_name)||', "node_B_set".'||quote_ident(nodeset_B_geometry_column_name)||'), ST_Distance("node_A_set".'||quote_ident(nodeset_A_geometry_column_name)||', "node_B_set".'||quote_ident(nodeset_B_geometry_column_name)||') FROM '||quote_ident(nodeset_A_table_name)||' AS "node_A_set", '||quote_ident(nodeset_B_table_name)||' AS "node_B_set" WHERE "node_A_set".'||quote_ident(nodeset_A_prkey)||' < 10 ORDER BY "node_A_set".'||quote_ident(nodeset_A_prkey)||', "node_A_set".'||quote_ident(nodeset_A_geometry_column_name)||' <-> "node_B_set".'||quote_ident(nodeset_B_geometry_column_name);
	
	--drop the previous table
	EXECUTE 'DROP TABLE IF EXISTS '||quote_ident(output_table_name);
	
	--create the output table joined back to the original input node set A table
	EXECUTE 'CREATE TABLE '||quote_ident(output_table_name)||' AS SELECT * FROM '||quote_ident(temp_table_name)||' LEFT OUTER JOIN '||quote_ident(nodeset_A_table_name)||' ON ('||quote_ident(temp_table_name)||'."node_A_id" = '||quote_ident(nodeset_A_table_name)||'.'||quote_ident(nodeset_A_prkey)||')';
	
	--add the output to the geometry columns table
	IF add_to_geometry_columns IS TRUE THEN

		RAISE NOTICE 'Adding to geometry columns (node_A_geom)';
		EXECUTE 'SELECT * FROM ni_add_to_geometry_columns('||quote_literal(output_table_name)||', '''', '||quote_literal(schema_name)||','||quote_literal(nodeset_A_geometry_column_name)||','||dims||','||nodeset_A_srid||', ''POINT'')';
		
		RAISE NOTICE 'Adding to geometry columns (node_B_geom)';
		EXECUTE 'SELECT * FROM ni_add_to_geometry_columns('||quote_literal(output_table_name)||', '''', '||quote_literal(schema_name)||','||quote_literal(nodeset_B_geometry_column_name)||','||dims||','||nodeset_B_srid||', ''POINT'')';
		
		RAISE NOTICE 'Adding to geometry columns (node_AB_line)';
		EXECUTE 'SELECT * FROM ni_add_to_geometry_columns('||quote_literal(output_table_name)||', '''', '||quote_literal(schema_name)||',''node_AB_line'','||dims||','||node_AB_line_srid||', ''POINT'')';
		
	END IF;
	
	RAISE NOTICE 'Returning records';
	RETURN QUERY EXECUTE 'SELECT * FROM '||quote_ident(output_table_name);
	
END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
ALTER FUNCTION ni_find_nearest_nodeB_to_nodeA_using_nn(varchar, varchar, varchar, varchar, varchar, varchar, varchar, boolean) OWNER TO postgres;