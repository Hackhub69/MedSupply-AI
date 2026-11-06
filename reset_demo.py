import os
from app import DB_PATH, init_demo
if os.getenv('DB2_CONNECTION_STRING'):
    raise SystemExit('Unset DB2_CONNECTION_STRING before resetting the local demo.')
if os.path.exists(DB_PATH): os.remove(DB_PATH)
init_demo()
print('Sample data reset.')
