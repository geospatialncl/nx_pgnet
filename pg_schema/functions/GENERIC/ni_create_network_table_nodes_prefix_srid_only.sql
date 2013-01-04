
CREATE OR REPLACE FUNCTION ni_create_network_table_nodes(character varying, integer)
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
ALTER FUNCTION ni_create_network_table_nodes(character varying, integer) OWNER TO postgres;
