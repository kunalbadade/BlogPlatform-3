from flask import Flask, request, url_for, jsonify, json, g, make_response
import sqlite3
import sys
from datetime import datetime
from functools import wraps
from passlib.hash import pbkdf2_sha256
from cassandra.cluster import Cluster

app = Flask(__name__)
isAuthenticated = True
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
    session = get_db()
    rows = session.execute('SELECT article_title,article_content FROM articles;')
    for row in rows:
        print ("Article Title "+row.article_title+" Article Content "+row.article_content)
    return '''<h1>{}<h1>'''.format(rows)

def api_root():
    return "Welcome"

#curl -u kunal:kunal --include --verbose --request POST --header 'Content-Type: application/json' --data '{"article_content":"Here is new content","article_title":"New Title"}' http://localhost:5000/new_article
@app.route('/new_article', methods = ['POST','GET'])
def api_new_article():
    data = None
    articleId = None
    url = None
    lastRowArticleId = 1
    username = request.authorization['username']
    if request.method == 'POST':
        statusCode:bool = False
        session = get_db()
        try:
            data = request.get_json()
            article_content = data['article_content']
            article_title = data['article_title']
            rows = session.execute('SELECT MAX(article_id) FROM articles;')
            article = rows[0]
            if article.system_max_article_id != None:
                lastRowArticleId = article.system_max_article_id
                lastRowArticleId += 1
            url = 'http://127.0.0.1/articles/' + str(lastRowArticleId)
            now = datetime.now()
            year = now.year

            session.execute(
                """
                INSERT INTO articles (year, article_id, article_content, article_title, createstamp, updatestamp, url, user_name)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s);
                """,
                (year,lastRowArticleId, article_content, article_title, now, now, url, username)
            )
            statusCode = True
        except Exception as e:
            print(e)
            statusCode = False
        finally:
            if statusCode:
                resp = jsonify(data)
                resp.status_code = 201
                resp.headers['Link'] = url
                return resp
            else:
                return jsonify(message="Failed to insert article"),409

#curl -u kunal:kunal --include --verbose --request GET --header 'Content-Type: application/json' http://localhost:5000/articles
@app.route('/articles/<article_id>', methods = ['GET'])
def api_get_article(article_id):
    if request.method == 'GET':
        statusCode:bool = False
        notFound:bool = False
        session = get_db()
        stmt = None
        try:
            stmt = session.prepare("SELECT \
            article_id,article_title, article_content,user_name,url, createstamp, updatestamp \
            FROM articles WHERE article_id = ?").bind([int(article_id)])

            rows = session.execute(stmt)
            articleRecord = rows[0]
            if articleRecord != None:
                statusCode = True
            else:
                notFound = True
        except Exception as e:
            print(e)
            statusCode = False
        finally:
            if statusCode:
                resp = jsonify(articleRecord)
                resp.status_code = 200
                return resp
            else:
                if notFound:
                    return jsonify(message="Article record not found for the given id"),404
                else:
                    return jsonify(message="Failed to retrieve record for given id"),409

#curl -u kunal:kunal --include --verbose --request GET --header 'Content-Type: application/json' --data '{"n":"3"}' http://localhost:5000/articles
@app.route('/articles', methods = ['GET'])
def api_get_n_article():
    if request.method == 'GET':
        statusCode:bool = False
        notFound:bool = False
        session = get_db()
        try:
            data = request.get_json()
            n = data['n']
            print("sdfsdfsdfdsfsdfsdfsdf  ",n)
            get_articles_stmt = session.prepare("SELECT \
            article_id,article_title, article_content,user_name,url, createstamp, updatestamp \
            FROM articles limit ?").bind([int(n)])
            articleRecord = session.execute(get_articles_stmt)
            print(articleRecord[0])
            if articleRecord != None:
                statusCode = True
            else:
                notFound = True
        except Exception as e:
            print(e)
            statusCode = False
        finally:
            if statusCode:
                resp = jsonify(articleRecord[0])
                resp.status_code = 200
                return resp
            else:
                if notFound:
                    return jsonify(message="Article records not found"),404
                else:
                    return jsonify(message="Failed"),409
#curl -u kunal:kunal --include --verbose --request GET --header 'Content-Type: application/json' --data '{"n":"3"}' http://localhost:5000/articles
@app.route('/articles_metadata', methods = ['GET'])
def api_get_article_metadata():
    if request.method == 'GET':
        statusCode:bool = False
        notFound:bool = False
        session = get_db()
        try:
            data = request.get_json()
            n = data['n']
            get_metadata_stmt = session.prepare("SELECT \
            article_id, article_title, user_name, createstamp, updatestamp, url \
            FROM articles LIMIT ? ").bind([int(n)])
            articleRecord = session.execute(get_metadata_stmt)
            if articleRecord != None:
                statusCode = True
            else:
                notFound = True
        except:
            statusCode = False
        finally:
            if statusCode:
                resp = jsonify(articleRecord[0])
                resp.status_code = 200
                return resp
            else:
                if notFound:
                    return jsonify(message="Article records not found"),404
                else:
                    return jsonify(message="Failed"),409

#curl -u kunal:kunal --include --verbose --request PUT --header 'Content-Type: application/json' --data '{"article_title":"UpdatedTitle","article_content":"UpdatedContent"}' http://localhost:5000/articles/5
@app.route('/articles/<article_id>', methods = ['PUT'])
def api_update_article(article_id):
    if request.method == 'PUT':
        statusCode:bool = False
        session = get_db()
        try:
            data = request.get_json()
            article_content = data['article_content']
            article_title = data['article_title']
            now = datetime.now()

            year, createstamp = get_year_and_timestamp(session, article_id)

            update_article_stmt = session.prepare("""
                UPDATE articles SET article_title = ?, article_content = ?, updatestamp = ? \
                WHERE article_id = ? and year = ? and createstamp = ?
            """).bind((article_title, article_content, now, int(article_id), year, createstamp))
            session.execute(update_article_stmt)
            statusCode = True
        except Exception as e:
            print(e)
            statusCode = False
        finally:
            if statusCode:
                url = 'http://127.0.0.1/articles/' + str(article_id)
                resp = jsonify(data)
                resp.status_code = 200
                resp.headers['Link'] = url
                return resp
            else:
                return jsonify(message="Failed"),409

#curl -u kunal:kunal --include --verbose --request DELETE --header 'Content-Type: application/json' --data '{"article_title":"UpdatedTitle","article_content":"UpdatedContent"}' http://localhost:5000/articles/6
@app.route('/articles/<article_id>', methods = ['DELETE'])
def api_delete_article(article_id):
    if request.method == 'DELETE':
        statusCode:bool = False
        session = get_db()
        try:
            year, createstamp = get_year_and_timestamp(session, article_id)
            delete_article_stmt = session.prepare(
            """
            DELETE FROM articles WHERE article_id = ? and year = ? and createstamp = ?
            """
            ).bind((int(article_id), year, createstamp))

            session.execute(delete_article_stmt)
            statusCode = True
        except Exception as e:
            print(e)
            statusCode = False
        finally:
            if statusCode:
                return jsonify(message = "Record Deleted Successfully"),200
            else:
                return jsonify(message = "Failed"),409

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
    app.run(debug=True)
