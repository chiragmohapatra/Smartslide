from flask_login import UserMixin
from . import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    is_instructor = db.Column(db.Boolean)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True)
    name = db.Column(db.String(1000))
    instructor_id = db.Column(db.Integer)
    reg_code = db.Column(db.String(1000))
    is_active = db.Column(db.Boolean)

class User_Course(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer)
    course_id = db.Column(db.Integer)

class Lecture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer)
    lecture_no = db.Column(db.Integer)
    name = db.Column(db.String(1000))

class Slide(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lecture_id = db.Column(db.Integer)
    slide_no = db.Column(db.Integer)
    subtitles = db.Column(db.Text)
    image_path = db.Column(db.Text)
    audio_path = db.Column(db.Text)
