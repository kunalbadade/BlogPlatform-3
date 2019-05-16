from flask import Flask, request, url_for, jsonify, json, g
import sqlite3
import sys
from datetime import datetime
from functools import wraps
from passlib.hash import pbkdf2_sha256
from cassandra.cluster import Cluster

app = Flask(__name__)

def get_db():
    cluster = Cluster(['172.17.0.2'])
    session = cluster.connect('blogplatform')
    return session

def get_year_and_timestamp(session, article_id):
    now = datetime.now()
    year = now.year

    select_year_stmt = session.prepare('SELECT year, createstamp FROM articles WHERE article_id=?').bind((int(article_id),))
    rows = session.execute(select_year_stmt)
    year = rows[0].year
    createstamp = rows[0].createstamp
    return year, createstamp

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route("/")
def index():
    cur = get_db().cursor()
    cur.execute('SELECT * FROM tags;')
    results = cur.fetchall()
    return '''<h1>{}<h1>'''.format(results)

#curl --include --request POST --header 'Content-Type: application/json' --data '{"tags":["tag3","tag4"]}' http://localhost:5000/new_tag/5
@app.route('/new_tag/<article_id>', methods = ['POST'])
def api_new_tag(article_id):
    data = None
    articleId = None
    article_url = None
    tagData = None
    lastRowId = None
    newTagId = None
    statusCode = None
    if request.method == 'POST':
        statusCode:bool = False
        session = get_db()
        try:
            tags = request.get_json()['tags']
            now = datetime.now()
            get_existing_tags_stmt = session.prepare('SELECT * from articles where article_id=?').bind((int(article_id),))
            rows = session.execute(get_existing_tags_stmt)
            existingTags = rows[0].tags

            if not existingTags == None:
                for tag in tags:
                    existingTags.add(tag)
            else:
                existingTags = tags

            newTags = existingTags

            insert_tag_stmt = session.prepare('insert into articles(article_id,article_title,article_content,year,createstamp,updatestamp,url,user_name,comments,tags)  values(?,?,?,?,?,?,?,?,?,?)')
            insert_tag_bind = insert_tag_stmt.bind((int(article_id), rows[0].article_title, rows[0].article_content, rows[0].year, rows[0].createstamp, now, rows[0].url, rows[0].user_name, rows[0].comments, newTags))
            session.execute(insert_tag_bind)
            statusCode = True
        except Exception as e:
            print(e)
            statusCode = False
        finally:
            if statusCode:
                resp = jsonify(tags)
                resp.status_code = 201
                return resp
            else:
                return jsonify(message="Failed"),409

#curl --request DELETE --header 'Content-Type: application/json' --data '{"tags":["tag5","tag6"]}' http://localhost:5000/remove_tags/<article_id>
@app.route('/remove_tags/<article_id>', methods = ['DELETE'])
def api_remove_tags(article_id):
    session = get_db()
    status_code :bool= False
    tags= None
    try:
        tags = request.get_json()['tags']
        now = datetime.now()

        get_existing_tags_stmt = session.prepare('SELECT * from articles where article_id=?').bind((int(article_id),))
        rows = session.execute(get_existing_tags_stmt)
        existingTags = rows[0].tags

        for tag in tags:
            existingTags.remove(tag)

        newTags = existingTags

        insert_tag_stmt = session.prepare('insert into articles(article_id,article_title,article_content,year,createstamp,updatestamp,url,user_name,comments,tags)  values(?,?,?,?,?,?,?,?,?,?)')
        insert_tag_bind = insert_tag_stmt.bind((int(article_id), rows[0].article_title, rows[0].article_content, rows[0].year, rows[0].createstamp, now, rows[0].url, rows[0].user_name, rows[0].comments, newTags))
        session.execute(insert_tag_bind)
        status_code = True
    except Exception as e:
        print(e)
        status_code = False
    finally:
        if status_code:
            return jsonify(message="Tags Deleted successfully"), 200
        else:
            return jsonify(message="Tags Deletion Failed"), 409

#curl --request GET --header 'Content-Type: application/json' http://localhost:5000/get_articles_for_tag/<tag_id>
@app.route('/get_articles_for_tag/<tag_name>', methods = ['GET'])
def api_get_articles_for_tag(tag_name):
    session = get_db()
    no_tags_found:bool = False
    status_code:bool = False
    try:
        print("here")
        get_url_stmt = session.prepare('SELECT url FROM articles WHERE tags CONTAINS ? ALLOW FILTERING;').bind((tag_name,))
        rows = session.execute(get_url_stmt)
        #print(rows[4])
        articles = []

        for i in rows:
            articles.append(i)

        status_code = True
    except Exception as e:
        print(e)
        status_code = False
    finally:
        if status_code:
            resp = jsonify(articles)
            resp.status_code = 200
            return resp
        else:
            if no_tags_found == True:
                return jsonify(message="No Articles Found"), 404
            else:
                return jsonify(message="Failed"), 409

#curl --request GET --header 'Content-Type: application/json' http://localhost:5100/get_tags/<article_id>
@app.route('/get_tags/<article_id>', methods = ['GET'])
def api_get_tags(article_id):
    session = get_db()
    no_tags_found = False
    status_code = False
    try:
        get_tags_stmt = session.prepare('SELECT tags FROM articles WHERE article_id = ?').bind((int(article_id),))
        rows = session.execute(get_tags_stmt)
        print(rows[0].tags)
        tagsSet = rows[0].tags

        tags = []

        for i in tagsSet:
            tags.append(i)
        status_code = True
    except Exception as e:
        print(e)
        status_code = False
    finally:
        if status_code:
            resp = jsonify(tags)
            resp.status_code = 200
            return resp
        else:
            if no_tags_found == True:
                return jsonify(message="No Tags Found"), 404
            else:
                return jsonify(message="Failed"), 404

@app.errorhandler(404)
def not_found(error=None):
    message = {
    'status' : 404,
    'message': 'Not found : '+ request.url,
    }
    resp = jsonify(message)
    resp.status_code = 404

    return 404

if __name__ == '__main__':
    app.run(debug = True)
#class Article(Resource):
#    def get(self, name):
#        conn = db_conneect .connnect()
#        for article in articles:
#            if(name == user["name"]):
#                return article, 200
#        return "Article not found, 404
