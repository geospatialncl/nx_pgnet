-----------------------RESET THE DATABASE--------------------------
SELECT * FROM ni_reset_database('public');

--delete old network
SELECT * FROM ni_delete_network('test1');
SELECT * FROM ni_delete_network('test2');