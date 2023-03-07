from flask import Blueprint, request, render_template, make_response, jsonify
# from flask import current_app as app
from datetime import datetime as dt
from application.DBModels import db, User


BPuser = Blueprint('user', __name__)


@BPuser.route('/users/index', methods=['GET'])
def index():
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])


@BPuser.route('/user/add', methods=['GET'])
def add():
    """Create a user."""
    email = request.args.get('email')
    if email:
        new_user = User(email=email,
                        created=dt.now(),
                        password="Password1234")
        db.session.add(new_user)  # Adds new User record to database
        db.session.commit()  # Commits all changes
    return make_response(f"{new_user} successfully created!")
