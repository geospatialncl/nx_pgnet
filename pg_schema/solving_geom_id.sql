--Tom would this work?
--Example insert statement
INSERT INTO "LightRail_Baseline_Wards_Edges" ("Node_F_ID", "Node_T_ID", "GraphID", "Edge_GeomID") VALUES (SELECT d."NodeID", b."NodeID", g."GraphID", SELECT * FROM return_edge_geometry_geom_id_on_edge_insert("Light_RailBaseline_Wards", SELECT ST_AsText(ST_MakeLine(d.geom, a.geom))) FROM "LightRail_Baseline_Stations" as a, "LightRail_Baseline_Wards_Nodes" as b, "General_Data_CAS_Wards_2001" as c, "LightRail_Baseline_Wards_Nodes" as d, "Graphs" as g) WHERE ST_Equals(a.geom , b.geom)
AND ST_within(b.geom, c.geom)
AND d.ons_label = c.ons_label
AND g."GraphName" = 'LightRail_Baseline_Wards';

--$1 - edge_geometry table prefix
--$2 - geometry (as wkt) to insert in to the edge_geometry table
CREATE OR REPLACE FUNCTION return_edge_geometry_geom_id_on_edge_geometry_insert(varchar, varchar)
RETURNS integer AS 
$BODY$
DECLARE
    --edge_geometry table prefix
    edge_geometry_table_prefix ALIAS for $1;
    
    --wkt geometry string
    geometry ALIAS for $2;
    
    --constant edge_geometry table suffix
    edge_geometry_table_suffix varchar := '_Edge_Geometry';
    
    --stores the table_name based on the prefix provided and suffix above
    edge_geometry_table_name varchar := '';
    
    --this will be the latest geometry id to return for use when inserting in to the edges table
    geom_id integer := 0;
BEGIN
    --create the apprporate edge_geometry table name
    edge_geometry_table_name := edge_geometry_table_prefix||edge_geometry_table_suffix;
    
    --insert the supplied geometry into the appropriate edge_geometry table (based on the supplied table prefix)
    EXECUTE 'INSERT INTO '||quote_ident(edge_geometry_table_name)||' (geom) VALUES (SELECT ST_GeomFromText('||geometry||')) RETURNING "GeomID"' INTO geom_id;
    
    --return the geometry id
    RETURN geom_id;
END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
ALTER FUNCTION return_edge_geometry_geom_id_on_edge_geometry_insert(varchar, varchar) OWNER TO postgres; 