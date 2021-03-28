from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from . import db
from .models import Course, User, User_Course, Lecture
import os

main = Blueprint('main', __name__)

@main.route('/')
def index():
    if not current_user.is_authenticated:
        return render_template('index.html')
    else:
        courses = None
        if current_user.is_instructor:
            courses = Course.query.filter_by(instructor_id = current_user.id)
        else:
            user_courses = User_Course.query.filter_by(user_id = current_user.id)
            courses = [Course.query.filter_by(id=course.course_id).first() for course in user_courses]
        return render_template('dashboard.html', name=current_user.name, courses=courses)

@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@main.route('/newcourse')
@login_required
def newcourse():
    if not current_user.is_instructor:
        return 'Invalid access'
    return render_template('new_course.html')

@main.route('/newcourse', methods=['POST'])
@login_required
def newcourse_post():
    if not current_user.is_instructor:
        return 'Invalid access'

    code = request.form.get('code')
    name = request.form.get('name')
    reg_code = request.form.get('reg_code')
    
    course = Course.query.filter_by(code=code).first()

    if course:
        flash('Course code already exists')
        return redirect(url_for('main.newcourse'))

    new_course = Course(code=code, name=name, instructor_id=current_user.id, reg_code=reg_code, is_active=True)

    db.session.add(new_course)
    db.session.commit()
    
    return redirect(url_for('main.index'))

@main.route('/enrollcourse')
@login_required
def enrollcourse():
    if current_user.is_instructor:
        return 'Invalid access'
    return render_template('enroll_course.html')

@main.route('/enrollcourse', methods=['POST'])
@login_required
def enrollcourse_post():
    if current_user.is_instructor:
        return 'Invalid access'

    code = request.form.get('code')
    reg_code = request.form.get('reg_code')
    
    course = Course.query.filter_by(code=code).first()

    if not course:
        flash('Invalid Course code')
        return redirect(url_for('main.enrollcourse'))
    if course.reg_code != reg_code:
        flash('Incorrect registration code')
        return redirect(url_for('main.enrollcourse'))
    
    user_course = User_Course.query.filter_by(user_id = current_user.id, course_id = course.id).first()
    if user_course:
        flash('Already registered!')
        return redirect(url_for('main.enrollcourse'))

    user_course = User_Course(user_id = current_user.id, course_id = course.id)

    db.session.add(user_course)
    db.session.commit()
    
    return redirect(url_for('main.index'))

@main.route('/course/<code>')
@login_required
def course(code):
    course = Course.query.filter_by(code=code).first()

    if not course:
        return render_template('404.html')

    if current_user.is_instructor:
        if course.instructor_id != current_user.id:
            return 'Invalid access'
    else:
        user_course = User_Course.query.filter_by(course_id=course.id,user_id=current_user.id).first()
        if not user_course:
            return 'Invalid access'

    instructor = User.query.filter_by(id=course.instructor_id).first().name

    lectures=Lecture.query.filter_by(course_id=course.id)

    return render_template('course_page.html', course=course, instructor=instructor, admin_access=current_user.is_instructor, lectures=lectures)

@main.route('/course/<code>/newlecture')
@login_required
def newlecture(code):
    course = Course.query.filter_by(code=code).first()
    
    if not course:
        return render_template('404.html')
    if course.instructor_id != current_user.id:
        return 'Invalid access'

    course_lectures = Lecture.query.filter_by(course_id=course.id)
    num_lectures = 0
    for lecture in course_lectures:
        num_lectures += 1

    return render_template('new_lecture.html', code=code, default_name='Lecture '+str(num_lectures+1))

@main.route('/course/<code>/newlecture', methods=['POST'])
@login_required
def newlecture_post(code):
    course = Course.query.filter_by(code=code).first()
    
    if not course:
        return render_template('404.html')
    if course.instructor_id != current_user.id:
        return 'Invalid access'

    name = request.form.get('name')
    ppt = request.files['ppt']
    video = request.files['video']

    course_lectures = Lecture.query.filter_by(course_id=course.id)
    num_lectures = 0
    for lecture in course_lectures:
        num_lectures += 1
    lecture_no = num_lectures+1

    ppt.save(os.path.join('files', f'course-{course.id}-lecture-{lecture_no}.pdf'))
    video.save(os.path.join('files', f'course-{course.id}-lecture-{lecture_no}.mp4'))

    lecture = Lecture(name=name, lecture_no=lecture_no, course_id=course.id)
    db.session.add(lecture)
    db.session.commit()

    # Processing here for slides
    
    return redirect(url_for('main.course', code=code))
