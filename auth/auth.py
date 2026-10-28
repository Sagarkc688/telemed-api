from flask import Blueprint, make_response, jsonify, request
import datetime
import jwt
import bcrypt
import globals
from decorators import jwt_required

users = globals.db.users
blacklist = globals.db.blacklist      # tokens of users who have logged out

auth_bp = Blueprint("auth_bp", __name__)


# LOGIN - checks username and password (sent with Basic Auth) and returns a token
@auth_bp.route("/api/v1.0/login", methods=["GET"])
def login():
    auth = request.authorization
    if not auth or not auth.username or not auth.password:
        return make_response(jsonify({"message": "Username and password required"}), 401,
                             {'WWW-Authenticate': 'Basic realm="Login required"'})

    user = users.find_one({"username": auth.username})

    # same message whether the username or the password is wrong - doesn't tell an attacker which one
    if user is None or not bcrypt.checkpw(auth.password.encode("utf-8"), user["password"].encode("utf-8")):
        return make_response(jsonify({"message": "Wrong username or password"}), 401)

    token = jwt.encode({
        "user": user["username"],
        "role": user["role"],                       # used later to check what this user is allowed to do
        "email": user["email"],                     # used to find a patient's own consultations
        "doctor_id": user.get("doctor_id"),         # only doctors have this - None for everyone else
        "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=30)
    }, globals.secret_key, algorithm="HS256")

    return make_response(jsonify({"token": token}), 200)


# LOGOUT - saves the token in the blacklist so it can't be used again
@auth_bp.route("/api/v1.0/logout", methods=["GET"])
@jwt_required
def logout():
    token = request.headers.get('x-access-token')
    blacklist.insert_one({"token": token})
    return make_response(jsonify({"message": "Logged out"}), 200)