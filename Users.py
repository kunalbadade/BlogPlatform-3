from flask import Flask, request, url_for, jsonify, json, g, make_response
from functools import wraps
from passlib.hash import pbkdf2_sha256
import sqlite3
from cassandra.cluster import Cluster

app = Flask(__name__)

def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if(request.authorization != None and request.authorization["username"] != None and request.authorization["password"] != None):
            username = request.authorization["username"]
            password = request.authorization["password"]
        else:
            return make_response('User does not exists.\n' 'Please provide user credentials', 401,
                    {'WWW-Authenticate': 'Basic realm="Login Required"'})
        if check_auth(username, password):
            return f(*args, **kwargs)
        else:
            return  make_response('Could not verify the credentials.\n' 'Please use correct credentials', 401,
                    {'WWW-Authenticate': 'Basic realm="Login Required"'})
    return decorated

def check_auth(username, password):
    row = get_db().execute("SELECT user_name, password, active_status FROM users WHERE user_name=%s", (username,))
    user_credentials = row[0]
    if row and user_credentials.user_name == username and pbkdf2_sha256.verify(password, user_credentials.password) and user_credentials.active_status == 1:
        return True
    else:
        return False

def get_db():
    cluster = Cluster(['172.17.0.2'])
    session = cluster.connect('blogplatform')
    return session

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def api_root():
    return "Welcome"

@app.route('/auth-server', methods = ['POST'])
@auth_required
def api_authenticat_user():
    if request.method == 'POST':
        return jsonify({"status":"OK"})

#curl --include --verbose --request POST --header 'Content-Type: application/json' --data '{"user_name" : "parag", "password" : "parag"}' http://localhost:5200/create_user
@app.route('/create_user', methods = ['POST'])
def api_create_user():
    if request.method == 'POST':
        status_code:bool = False
        session = get_db()
        userdata = request.get_json()
        user_id = None
        number_of_rows = None
        try:
            get_count_stmt = session.prepare("SELECT COUNT(*) FROM users WHERE user_name = ? ALLOW FILTERING").bind((userdata['user_name'],))
            user_exixts = session.execute(get_count_stmt)
            number_of_rows = user_exixts[0]
            if number_of_rows.count <= 0:
                 get_count_stmt = session.prepare("SELECT MAX(user_id) FROM users;")
                 row = session.execute(get_count_stmt)
                 user_id=row[0].system_max_user_id
                 if not user_id == 0 and not user_id is None:
                     user_id += 1
                 else:
                     user_id = 1
                 hashed_password = pbkdf2_sha256.hash(userdata['password'])
                 insert_user_stmt = session.prepare("INSERT INTO users (user_id, user_name, password, active_status) VALUES (?, ?, ?, ?)").bind((user_id, userdata['user_name'], hashed_password, 1))
                 session.execute(insert_user_stmt)
                 status_code = True
        except Exception as e:
            status_code = False
        finally:
            if status_code:
                return jsonify(message="User Created successfully"), 201
            else:
                return jsonify(message="User Already Exists"), 409

#curl -u parag:parag --include --verbose --request DELETE --header 'Content-Type: application/json' http://localhost:5200/delete_user
@app.route('/delete_user', methods=['DELETE'])
def api_delete_user():
        if request.method == 'DELETE':
            status_code:bool = False
        session = get_db()
        username = request.authorization["username"]
        try:
            delete_user_stmt = session.prepare("DELETE FROM users WHERE user_name=?").bind([username])
            session.execute(delete_user_stmt)
            status_code = True
        except Exception as e:
            status_code = False
        finally:
            if status_code:
                return jsonify(message="User deleted successfully"), 201
            else:
                return jsonify(message="Failed to delete the user"), 409

#curl -u shekhar:palit -i --request PATCH --header 'Content-Type: application/json' --data '{"user_name" : "shekhar","old_password" : "palit", "password" : "palit1234"}' http://localhost:5200/change_password
@app.route('/change_password', methods=['PATCH'])
def api_change_password():
    if request.method == 'PATCH':
        status_code:bool = False
    session = get_db()
    try:
        userdata = request.get_json()
        user_name = userdata['user_name']
        get_password_stmt = session.prepare("select password from users where user_name = ? ALLOW FILTERING").bind([user_name])
        row = session.execute(get_password_stmt)
        if pbkdf2_sha256.verify(userdata['old_password'], row[0].password):
            new_hashed_password = pbkdf2_sha256.hash(userdata['password'])
            select_stmt = session.prepare("SELECT user_name FROM users WHERE active_status=1 ALLOW FILTERING")
            resultSet = session.execute(select_stmt)
            for row in resultSet:
                update_user_stmt = session.prepare("UPDATE users SET password=? WHERE user_name=?").bind((new_hashed_password, row.user_name))
                session.execute(update_user_stmt)
            status_code = True
    except Exception as e:
        status_code = False
    finally:
        if status_code:
            return jsonify(message="Password Updated SucessFully"), 200
        else:
            return jsonify(message="Failed to Update the Password"), 409

if __name__ == '__main__':
    app.run(debug=True)
