-- Table: "Global_Interdependency"

DROP TABLE IF EXISTS "Global_Interdependency" CASCADE;

CREATE TABLE "Global_Interdependency"
(
  "InterdependencyID" bigserial NOT NULL,
  "InterdependencyFromGraphID" integer NOT NULL,
  "InterdependencyToGraphID" integer NOT NULL,
  "InterdependencyTableName" character varying NOT NULL,
  "InterdependencyEdgeTableName" character varying NOT NULL,
  CONSTRAINT "Global_Interdependency_prkey" PRIMARY KEY ("InterdependencyID"),
  CONSTRAINT "InterdependencyFromGraphID_frkey" FOREIGN KEY ("InterdependencyFromGraphID")
      REFERENCES "Graphs" ("GraphID") MATCH SIMPLE
      ON UPDATE NO ACTION ON DELETE NO ACTION,
  CONSTRAINT "InterdependencyToGraphID_frkey" FOREIGN KEY ("InterdependencyToGraphID")
      REFERENCES "Graphs" ("GraphID") MATCH SIMPLE
      ON UPDATE NO ACTION ON DELETE NO ACTION,
  CONSTRAINT "InterdependencyEdgeGraphTableName" UNIQUE ("InterdependencyEdgeTableName"),
  CONSTRAINT "InterdependencyTableName_uinque" UNIQUE ("InterdependencyTableName")
)
WITH (
  OIDS=FALSE
);
ALTER TABLE "Global_Interdependency" OWNER TO postgres;

-- Trigger: ni_delete_int_edge_table_post_int_record_delete on "Global_Interdependency"

-- DROP TRIGGER ni_delete_int_edge_table_post_int_record_delete ON "Global_Interdependency";

CREATE TRIGGER ni_delete_int_edge_table_post_int_record_delete
  AFTER DELETE
  ON "Global_Interdependency"
  FOR EACH ROW
  EXECUTE PROCEDURE ni_delete_int_edge_table_post_int_record_delete();

-- Trigger: ni_delete_int_table_post_int_record_delete on "Global_Interdependency"

-- DROP TRIGGER ni_delete_int_table_post_int_record_delete ON "Global_Interdependency";

CREATE TRIGGER ni_delete_int_table_post_int_record_delete
  AFTER DELETE
  ON "Global_Interdependency"
  FOR EACH ROW
  EXECUTE PROCEDURE ni_delete_int_table_post_int_record_delete();

