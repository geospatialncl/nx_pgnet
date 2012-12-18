@echo off
REM - combine all processing functions into a single .sql file
REM - results in a file at \FUNCTIONS\PROCESSING\ni_processing_functions.sql being created - ready to execute on chosen database
call %~dp0FUNCTIONS\PROCESSING\ni_combine_processing_sql_functions.bat

REM - combine all trigger functions into a single .sql file
REM - results in a file at \FUNCTIONS\TRIGGER\ni_trigger_functions.sql being created - ready to execute on chosen database
call %~dp0FUNCTIONS\TRIGGER\ni_combine_trigger_sql_functions.bat

REM - combine all sql table definitions into a single .sql file
REM - results in a file at \TABLES\ni_tables.sql being created - ready to execute on chosen database
call %~dp0TABLES\ni_combine_tables_sql.bat

REM - combine all generic (admin) functions into a single .sql file
REM - results in a file at \FUNCTIONS\GENERIC\ni_generic_functions.sql being created - ready to execute on chosen database
call %~dp0FUNCTIONS\GENERIC\ni_combine_generic_sql_functions.bat

