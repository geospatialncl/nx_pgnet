
CREATE OR REPLACE FUNCTION ni_create_node_view(character varying, character varying, character varying, integer, integer)
  RETURNS character varying AS
$BODY$
DECLARE

    --user supplied table prefix
    table_prefix ALIAS for $1;
	
	--schema name
	schema_name ALIAS for $2;
    
	--geometry column name for Node table
    geometry_column_name ALIAS for $3;
	
    --to store SRID of geometry in Node table
    SRID ALIAS for $4;
	
	--to store coordinate dimension of coordinates in geometry of Node table
    coordinate_dimension ALIAS for $5;
	
    --constant node table suffix
    node_table_suffix varchar := '_Nodes';
    node_view_suffix varchar := '_View_Nodes';
    new_node_view_name varchar := '';
    node_table_name varchar := '';
	    
    --geometry_column_record_count
    geometry_column_record_count integer := 0;
    
    --node type
    node_geometry_type varchar := '';
    
    --constant geometry column table name
    geometry_column_table_name varchar := 'geometry_columns';
    
BEGIN
    
    --original node table name
    node_table_name := table_prefix||node_table_suffix;
    
    --create the new node view table name
    new_node_view_name := table_prefix||node_view_suffix;

	--drop the view	
	EXECUTE 'DROP VIEW IF EXISTS'||quote_ident(new_node_view_name)||' CASCADE';
	
    --create node view
    EXECUTE 'CREATE OR REPLACE VIEW '||quote_ident(new_node_view_name)||' AS SELECT int4(ROW_NUMBER() over (order by node_table."NodeID")) as view_id, node_table.* FROM '||quote_ident(node_table_name)||' as node_table';
    
    --retrieve the SRID of the node view
    EXECUTE 'SELECT ST_SRID(geom) FROM '||quote_ident(node_table_name) INTO SRID;
    
    --retrieve the coordinate_dimension of the node view
    EXECUTE 'SELECT ST_Dimension(geom) FROM '||quote_ident(node_table_name) INTO coordinate_dimension;
    
    --retrieve the geometry type for the node view
    EXECUTE 'SELECT GeometryType(geom) FROM '||quote_ident(node_table_name) INTO node_geometry_type;
    
	--add the node view to the geometry columns table
	EXECUTE 'SELECT * FROM ni_add_to_geometry_columns('||quote_literal(new_node_view_name)||', '''', '||quote_literal(schema_name)||', '||quote_literal(geometry_column_name)||', '||coordinate_dimension||','||SRID||','||quote_literal(node_geometry_type)||')';
	--return the new view name to the user
    RETURN new_node_view_name;
    
END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;
ALTER FUNCTION ni_create_node_view(character varying, character varying, character varying, integer, integer) OWNER TO postgres;
