-- Function: ni_create_edge_view(character varying, character varying, character varying, integer, integer)

-- DROP FUNCTION ni_create_edge_view(character varying, character varying, character varying, integer, integer);

CREATE OR REPLACE FUNCTION ni_create_edge_view(character varying, character varying, character varying, integer, integer)
  RETURNS character varying AS
$BODY$
DECLARE
    --user supplied table prefix
    table_prefix ALIAS for $1;
    
	--schema name
    schema_name ALIAS for $2;
    
	--geometry column name for Edge_Geometry table
    geometry_column_name ALIAS for $3;
	
    --to store SRID of geometry in Edge_Geometry table
    SRID ALIAS for $4;
	
	--to store coordinate dimension of coordinates in geometry of Edge_Geometry table
    coordinate_dimension ALIAS for $5;
	
    --constant edge table suffix
    edge_table_suffix varchar := '_Edges';
    edge_table_name varchar := '';
    
    --constant edge_geometry table suffix
    edge_geometry_table_suffix varchar := '_Edge_Geometry';
    edge_geometry_table_name varchar := '';
    
    --constant value to use for creating the new edge to edge_geometry view (join)
    edge_view_suffix varchar := '_View_Edges_Edge_Geometry';
    new_edge_view_name varchar := '';
    
    --geometry_column_record_count
    geometry_column_record_count integer := 0;
        
    --constant geometry column table name
    geometry_column_table_name varchar := 'geometry_columns';
    
    --edge_geometry type
    edge_geometry_type varchar := '';
    
    
BEGIN
    --create the new edge view table name
    new_edge_view_name := table_prefix||edge_view_suffix;
    
    --specify the edge table to join
    edge_table_name := table_prefix||edge_table_suffix;
    
    --specify the edge_geometry table to join
    edge_geometry_table_name := table_prefix||edge_geometry_table_suffix;
        
	--drop view 	
	EXECUTE 'DROP VIEW IF EXISTS'||quote_ident(new_edge_view_name)||' CASCADE';
	
    --this creates a view of the two edge and edge_geometry tables - this works in QGIS
    EXECUTE 'CREATE OR REPLACE VIEW '||quote_ident(new_edge_view_name)||' AS SELECT int4(ROW_NUMBER() over (order by edge_table."EdgeID")) as view_id, edge_table.*, edge_geometry_table.* FROM '||quote_ident(edge_table_name)||' as edge_table, '||quote_ident(edge_geometry_table_name)||' as edge_geometry_table WHERE edge_table."Edge_GeomID" = edge_geometry_table."GeomID"';
    
    --retrieve the SRID of the edge_geometry table
    EXECUTE 'SELECT ST_SRID(geom) FROM '||quote_ident(edge_geometry_table_name) INTO SRID;
    
    --retrieve the coordinate_dimension of the edge_geometry table
    EXECUTE 'SELECT ST_Dimension(geom) FROM '||quote_ident(edge_geometry_table_name) INTO coordinate_dimension;
    
    --retrieve the geometry type for the edge geometry table
    EXECUTE 'SELECT GeometryType(geom) FROM '||quote_ident(edge_geometry_table_name) INTO edge_geometry_type;
    
	--add the edge view to the geometry columns table
	EXECUTE 'SELECT * FROM ni_add_to_geometry_columns('||quote_literal(new_edge_view_name)||', '''', '||quote_literal(schema_name)||', '||quote_literal(geometry_column_name)||', '||coordinate_dimension||','||SRID||','||quote_literal(edge_geometry_type)||')';
	
    --return the new view name to the user
    RETURN new_edge_view_name;
    
END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;
ALTER FUNCTION ni_create_edge_view(character varying, character varying, character varying, integer, integer) OWNER TO postgres;
