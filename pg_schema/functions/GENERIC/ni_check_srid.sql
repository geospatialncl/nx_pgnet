-- Function: ni_check_srid(integer)

-- DROP FUNCTION ni_check_srid(integer);

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
