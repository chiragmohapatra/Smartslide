import os
os.remove('project/db.sqlite')

from project import db, create_app
db.create_all(app=create_app())