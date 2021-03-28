import os
if os.path.isfile('project/db.sqlite'):
    os.remove('project/db.sqlite')

from project import db, create_app
db.create_all(app=create_app())