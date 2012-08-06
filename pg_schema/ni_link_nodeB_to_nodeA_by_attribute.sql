--SELECT * FROM ni_link_nodeB_to_nodeA_by_attribute('UWWTW_T_UWWTPS_UK_ONLY_OSGB', 'uwwid', 'geom', 'uwwid', 'nodeset_A_', 'UWWTW_T_DischargePoints_UK_ONLY_OSGB36', 'dcpid', 'geom', 'uwwid', 'nodeset_B_', 'uwwtw_t_uwwtps_link_uwwtw_discharge_points_Feb2011', False) f(nodeset_A_gid integer, nodeset_A_uwwid double precision, nodeset_A_uwwstate double precision, nodeset_A_rptmstatek character varying(254), nodeset_A_aggid double precision, nodeset_A_uwwcode character varying(254), nodeset_A_uwwname character varying(254), nodeset_A_uwwcollect double precision, nodeset_A_uwwdateclo character varying(254), nodeset_A_uwwhistori character varying(254), nodeset_A_uwwlatitud double precision, nodeset_A_uwwlongitu double precision, nodeset_A_uwwnuts double precision, nodeset_A_uwwloadent double precision, nodeset_A_uwwcapacit double precision, nodeset_A_uwwprimary smallint, nodeset_A_uwwseconda smallint, nodeset_A_uwwothertr smallint, nodeset_A_uwwnremova smallint, nodeset_A_uwwpremova smallint, nodeset_A_uwwuv smallint, nodeset_A_uwwchlorin smallint, nodeset_A_uwwozonati smallint, nodeset_A_uwwsandfil smallint, nodeset_A_uwwmicrofi smallint, nodeset_A_uwwother smallint, nodeset_A_uwwspecifi character varying(254), nodeset_A_uwwbod5per double precision, nodeset_A_uwwcodperf double precision, nodeset_A_uwwtssperf double precision, nodeset_A_uwwntotper double precision, nodeset_A_uwwptotper double precision, nodeset_A_geom geometry, nodeset_B_gid integer, nodeset_B_dcpid double precision, nodeset_B_dcpstate double precision, nodeset_B_rptmstatek character varying(254), nodeset_B_uwwid double precision, nodeset_B_dcpcode character varying(254), nodeset_B_dcpname character varying(254), nodeset_B_dcpnuts double precision, nodeset_B_dcplatitud double precision, nodeset_B_dcplongitu double precision, nodeset_B_dcpwaterbo double precision, nodeset_B_dcpirrigat double precision, nodeset_B_dcptypeofr double precision, nodeset_B_rcaid double precision, nodeset_B_dcpsurface double precision, nodeset_B_dcpwater_1 character varying(254), nodeset_B_dcpnotaffe character varying(254), nodeset_B_dcpmsprovi character varying(254), nodeset_B_dcpcomacce character varying(254), nodeset_B_dcpgroundw character varying(254), nodeset_B_dcpreceivi character varying(254), nodeset_B_dcpwfdsubu character varying(254), nodeset_B_dcpwfdrbd character varying(254), nodeset_B_dcpremarks character varying(254), nodeset_B_dcpwfdrbdr date, nodeset_B_dcpwater_2 date, nodeset_B_dcpgroun_1 character varying(254), nodeset_B_dcprecei_1 date, nodeset_B_dcpwfdsu_1 character varying(254), nodeset_B_geom geometry, node_A_id double precision, node_A_attr double precision, node_A_geom geometry, node_B_id double precision, node_B_attr double precision, node_B_geom geometry, node_AB_line geometry, node_AB_distance numeric);
--function to find the closest node of nodeset B to each node of nodeset A
--returns all the original nodes, and attributes of nodeset A, along with the geometry of the nearest node of nodeset B, a distance to the nearest node of nodeset B, and a straight line that joins node of nodeset A to nodes of nodeset B.

--$1 - nodeset_A_table_name - table name of containing nodes
--$2 - nodeset_A_prkey - primary key of nodeset_A_table_name
--$3 - nodeset_A_geometry_column_name - name of geometry column of nodeset_A_table_name - this will be used to create the new link with the second nodeset_B table
--$4 - nodeset_A_attribute_name - name of attribute that joins with nodeset_B
--$5 - nodeset_A_prefix - prefix for all columns of nodeset_A_table_name e.g. "nodeset_A_"
--$6 - nodeset_B_table_name - table name of containing nodes
--$7 - nodeset_B_prkey - primary key of nodeset_B_table_name
--$8 - nodeset_B_geometry_column_name - name of geometry column of nodeset_B_table_name - this will be used to create the new link with the first nodeset_A table
--$9 - nodeset_B_attribute_name - name of attribute that joins with nodeset_A
--$10 - nodeset_B_prefix - prefix for all columns of nodeset_A_table_name e.g. "nodeset_B_"
--$11 - output_table_name - table name for output
--$12 - add_to_geometry_columns - boolean denoting whether to add the resultant join table to the geometry columns table of the current database (adds node_A_geom, node_B_geom, and node_AB_line)

CREATE OR REPLACE FUNCTION ni_link_nodeb_to_nodea_by_attribute(varchar, varchar, varchar, varchar, varchar(10), varchar, varchar, varchar, varchar, varchar(10), varchar, boolean)
RETURNS SETOF RECORD AS 
$BODY$
DECLARE

	--nodeset A table_name
	nodeset_A_table_name ALIAS for $1;
	
	--nodeset A prkey
	nodeset_A_prkey ALIAS for $2;
	
	--geometry column name of nodeset A table (could be exposed as a parameter)
	nodeset_A_geometry_column_name ALIAS for $3;
	
	--attribute of nodeset A table to relate to attribute of nodeset B table
	nodeset_A_attribute_name ALIAS for $4;
	
	--prefix for output columns from nodeset A
	nodeset_A_prefix ALIAS for $5;
	
	--nodeset B table_name
	nodeset_B_table_name ALIAS for $6;
	
	--nodeset B prkey
	nodeset_B_prkey ALIAS for $7;
	
	--geometry column name of nodeset B table (could be exposed as a parameter)
	nodeset_B_geometry_column_name ALIAS for $8;
	
	--attribute of nodeset B table to relate to attribute of nodeset A table
	nodeset_B_attribute_name ALIAS for $9;
	
	--prefix for output columns from nodeset A
	nodeset_B_prefix ALIAS for $10;
	
	--output table name 
	output_table_name ALIAS for $11;
	
	--indicates whether or not to add the resulting output table to the geometry columns table
	add_to_geometry_columns ALIAS for $12;
	
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

	--to store records retrieve from the information_schema table
	information_schema_table_record RECORD;
	
	--to store column names of original node A table
	join_sql_table_A text := '';
	--to store column names of original node B table
	join_sql_table_B text := '';
	
	--column counter for creating sql string
	current_column_counter integer := 0;
	
	--column count of node A table
	column_count_nodeset_A integer := 0;
	--column count of node B table
	column_count_nodeset_B integer := 0;
	
	--string to store new column name for columns in node A table
	new_column_name_nodeset_A text := '';
	--string to store new column name for columns in node B table
	new_column_name_nodeset_B text := '';
	
	--to store table name of join between attribute tables of node A and node B tables
	temp_table_name_join text := '';
	
	--to store the column name of the new key for node A table i.e. nodeset_A_prefix||nodeset_A_attribute_name
	new_join_key_name text := '';
	
BEGIN
	
	--create a temporary table to store the final results, then need to join the original table back to this table
	temp_table_name := output_table_name||'_temp';
	
	--determine the datatype of nodeset A prkey
	EXECUTE 'SELECT data_type FROM information_schema.columns WHERE table_name = '||quote_literal(nodeset_A_table_name)||' AND column_name = '||quote_literal(nodeset_A_prkey) INTO nodeset_A_prkey_datatype;
	
	--determine the datatype of nodeset B prkey
	EXECUTE 'SELECT data_type FROM information_schema.columns WHERE table_name = '||quote_literal(nodeset_B_table_name)||' AND column_name = '||quote_literal(nodeset_B_prkey) INTO nodeset_B_prkey_datatype;
	
	--drop the previous temporary table
	EXECUTE 'DROP TABLE IF EXISTS '||quote_ident(temp_table_name);
		
	--perform a join 
	--creates a temporary table from the left outer join performed between nodesetA and nodesetB
	EXECUTE 'CREATE TEMPORARY TABLE '||quote_ident(temp_table_name)||' AS SELECT '||quote_ident(nodeset_A_table_name)||'.'||quote_ident(nodeset_A_prkey)||' AS "node_A_id", '||quote_ident(nodeset_A_table_name)||'.'||quote_ident(nodeset_A_geometry_column_name)||' AS "node_A_geom", '||quote_ident(nodeset_A_table_name)||'.'||quote_ident(nodeset_A_attribute_name)||' AS "node_A_attr", '||quote_ident(nodeset_B_table_name)||'.'||quote_ident(nodeset_B_prkey)||' AS "node_B_id", '||quote_ident(nodeset_B_table_name)||'.'||quote_ident(nodeset_B_geometry_column_name)||' AS "node_B_geom", '||quote_ident(nodeset_B_table_name)||'.'||quote_ident(nodeset_B_attribute_name)||' AS "node_B_attr" FROM '||quote_ident(nodeset_A_table_name)||' LEFT OUTER JOIN '||quote_ident(nodeset_B_table_name)||' ON ('||quote_ident(nodeset_A_table_name)||'.'||quote_ident(nodeset_A_attribute_name)||' = '||quote_ident(nodeset_B_table_name)||'.'||quote_ident(nodeset_B_attribute_name)||');';
	
	EXECUTE 'ALTER TABLE '||quote_ident(temp_table_name)||' ADD COLUMN "node_AB_line" geometry;';
	EXECUTE 'ALTER TABLE '||quote_ident(temp_table_name)||' ADD COLUMN "node_AB_distance" numeric;';
	
	EXECUTE 'UPDATE '||quote_ident(temp_table_name)||' SET "node_AB_line" = ST_MakeLine("node_A_geom", "node_B_geom");';
	
	--NEED TO UPDATE THE VALUES FOR "node_AB_distance" - this uses the distance between the two input geometries
	--EXECUTE 'UPDATE '||quote_ident(temp_table_name)||' SET "node_AB_distance" = ST_Distance('||quote_ident(nodeset_A_geometry_column_name)||','||quote_ident(nodeset_B_geometry_column_name)||')';
	
	--NEED TO UPDATE THE VALUES FOR "node_AB_distance" - this uses the length of the result geometry?
	EXECUTE 'UPDATE '||quote_ident(temp_table_name)||' SET "node_AB_distance" = ST_Length("node_AB_line");';
	
	--create the custom column names from nodeset_A
	EXECUTE 'SELECT * FROM ni_create_new_column_names_for_join('||quote_literal(nodeset_A_prefix)||','||quote_literal(nodeset_A_table_name)||')' INTO join_sql_table_A;
	
	--create the custom column names for nodeset_B
	EXECUTE 'SELECT * FROM ni_create_new_column_names_for_join('||quote_literal(nodeset_B_prefix)||','||quote_literal(nodeset_B_table_name)||')' INTO join_sql_table_B;
	
	--create a temporary table name for joining the two attribute tables of nodeset_A and nodeset_B
	temp_table_name_join := 'nodeset_A_join_nodeset_B';
	
	--drop the temporary table if it exists
	EXECUTE 'DROP TABLE IF EXISTS '||quote_ident(temp_table_name_join);
	
	--create the temporary table as a join between nodeset_A table and nodeset_B table, based upon common attributes supplied
	EXECUTE 'CREATE TEMPORARY TABLE '||quote_ident(temp_table_name_join)||' AS SELECT '||join_sql_table_A||', '||join_sql_table_B||' FROM '||quote_ident(nodeset_A_table_name)||' LEFT OUTER JOIN '||quote_ident(nodeset_B_table_name)||' ON ('||quote_ident(nodeset_A_table_name)||'.'||quote_ident(nodeset_A_attribute_name)||' = '||quote_ident(nodeset_B_table_name)||'.'||quote_ident(nodeset_B_attribute_name)||');';
	
	--create the final join key based on the prefix supplied and the attribute of nodeset_A
	new_join_key_name := nodeset_A_prefix||nodeset_A_attribute_name;
	
	--drop the output table (name given as parameter)
	EXECUTE 'DROP TABLE IF EXISTS '||quote_ident(output_table_name);
	
	--create the output table as a join between the newly joined two tables (nodeset_A, nodeset_B), and the new table containing the link geometry and distance
	EXECUTE 'CREATE TABLE '||quote_ident(output_table_name)||' AS SELECT '||quote_ident(temp_table_name_join)||'.*, "node_A_id", "node_A_attr", "node_A_geom", "node_B_id", "node_B_attr", "node_B_geom", "node_AB_line", "node_AB_distance" FROM '||quote_ident(temp_table_name_join)||' LEFT OUTER JOIN '||quote_ident(temp_table_name)||' ON ('||quote_ident(new_join_key_name)||' = "node_A_attr");';
	
	--delete old temp table (of nodeset_A, nodeset_B)
	EXECUTE 'DROP TABLE IF EXISTS '||quote_ident(temp_table_name_join);
	--delete old temp table (of join table containing new geometry and distance of link between node sets)
	EXECUTE 'DROP TABLE IF EXISTS '||quote_ident(temp_table_name);
	
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
ALTER FUNCTION ni_link_nodeb_to_nodea_by_attribute(varchar, varchar, varchar, varchar, varchar(10), varchar, varchar, varchar, varchar, varchar(10), varchar, boolean) OWNER TO postgres;