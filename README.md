# hera_mc
Monitor and Control code for HERA

# adding a new table
To add a new table into the hera_mc database:
    1 - create a new module under hera_mc, basing on e.g. host_status.py
    2 - add import line in __init__.py
    3 - after enabling the production database for a schema change, run mc_initialize_db.py
    4 - disable production database schema edit
If you then run psql and connect to hera_mc, you should see the new table
