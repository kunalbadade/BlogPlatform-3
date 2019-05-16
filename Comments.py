from flask import Flask, request, url_for, jsonify, json, g, make_response
import sqlite3
from functools import wraps
import sys
from datetime import datetime
from cassandra.cluster import Cluster
from cassandra.util import OrderedMapSerializedKey

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
    cur.execute('SELECT * FROM Comments;')
    results = cur.fetchall()
    return '''<h1>{}<h1>'''.format(results)

#curl --include --verbose --request POST --header 'Content-Type: application/json' --data '{"article_id":"2","comment_content":"Comment1"}' http://localhost:5000/new_comment
@app.route('/new_comment', methods = ['POST'])
def api_new_comment():
    statusCode = 0
    articleExists = 1
    data = None
    CommentId = None
    lastCommentId = 1
    date = datetime.now()
    if request.method == 'POST':
        data = request.get_json()
        article_id = data['article_id']
        comment_content = data['comment_content']
        session = get_db()
        now = datetime.now()
        if not request.authorization:
            user_name = "Anonymous Coward"
        else:
            user_name = request.authorization["username"]
        try:
            article_exists_stmt = session.prepare('SELECT COUNT(*) FROM articles where article_id=?').bind((int(article_id),))
            row = session.execute(article_exists_stmt)
            user_count = row[0]
            print(user_count.count)
            if user_count.count >= 1:
                year, createstamp = get_year_and_timestamp(session, article_id)
                commentsList = [{createstamp:{user_name:comment_content}}]
                insert_comment_stmt = session.prepare('UPDATE articles SET comments = ? + comments where article_id=? and year = ? and createstamp = ?').bind((commentsList, int(article_id), year, createstamp))
                session.execute(insert_comment_stmt)
                statusCode = 1
            else:
                articleExists = 0
                #insert_comment_stmt = session.prepare('INSERT INTO articles (article_id, comments, createstamp, updatestamp, user_name) VALUES (?,?,?,?,?)').bind((int(article_id),[comment_content],now,now,user_name))

        except Exception as e:
            print(e)
            statusCode = 0
        finally:
            if statusCode == 1:
                #url = 'http://127.0.0.1/new_comment/' + str(lastCommentId)
                resp = jsonify(data)
                resp.status_code = 201
                #resp.headers['Link'] = url
                return resp
            else:
                if articleExists == 0:
                    return jsonify(message="Article does not exists"), 409
                else:
                    return jsonify(message = "Failed"),409

#curl --include --verbose --request DELETE --header 'Content-Type: application/json' --data '{"article_id":"3"}' http://localhost:5000/comments/0
@app.route('/comments/<comment_id>', methods = ['DELETE'])
def api_delete_comment(comment_id):
    if request.method == 'DELETE':
        #statusCode:bool = False
        statusCode = 0
        data = request.get_json()
        article_id = int(data['article_id'])
        if request.authorization:
            user_name = request.authorization["username"]
        session = get_db()
        try:
            year, createstamp = get_year_and_timestamp(session, article_id)
            delete_comment_stmt = session.prepare('DELETE comments[?] FROM articles WHERE article_id = ? AND year=? AND createstamp=?').bind(((int(comment_id),article_id, year, createstamp)))
            session.execute(delete_comment_stmt)
            statusCode = 1
        except Exception as e:
            print(e)
            statusCode = 0
        finally:
            if statusCode == 1:
                return jsonify(message = "Comment deleted successfully"),200
            else:
                return jsonify(message = "Failed"),409

#curl --include --verbose --request GET --header 'Content-Type: application/json' http://localhost:5000/comments/getcommentcount/2
@app.route('/comments/getcommentcount/<article_id>', methods = ['GET'])
def api_count_comment(article_id):
    statusCode = 0
    session = get_db()
    count = 0
    try:
        article_id = int(article_id)
        get_comment_count_stmt = session.prepare('SELECT comments FROM articles WHERE article_id = ?').bind((article_id,))
        rows = session.execute(get_comment_count_stmt)
        commentsdata = rows[0]

        for idx_row, i_row in enumerate(commentsdata):
            for idx_value, i_value in enumerate(i_row):
                if type(i_value) is OrderedMapSerializedKey:
                    commentsdata[idx_row][idx_value] = dict(commentsdata[idx_row][idx_value])

        data = commentsdata.comments
        count = len(data)
        statusCode = 1
    except Exception as e:
        print(e)
        statusCode = 0
    finally:
       if statusCode == 1:
          resp = jsonify(count)
          resp.status_code = 200
          return resp
       else:
          return jsonify(message = "Failed"),409

#curl --include --verbose --request GET --data '{"n":"2"}' --header 'Content-Type: application/json' http://localhost:5300/comments/getncomments/1
@app.route('/comments/getncomments/<article_id>', methods = ['GET'])
def api_n_comment(article_id):
    statusCode = 0
    data = request.get_json()
    n = data['n']
    session = get_db()
    try:
        article_id_int = int(article_id)
        #get_year_stmt = session.prepare('SELECT year, updatestamp FROM articles WHERE article_id=? ALLOW FILTERING;').bind((article_id_int,))
        #yeardata = session.execute(get_year_stmt)
        #year = yeardata[0].year
        #updatestamp = yeardata[0].updatestamp
        year,createstamp = get_year_and_timestamp(session, article_id)
        get_n_comments_stmt = session.prepare('SELECT comments FROM articles WHERE year=? and article_id=? and createstamp=?').bind((int(year),int(article_id),createstamp))
        data = session.execute(get_n_comments_stmt)
        commentsdata = data[0]

        for idx_row, i_row in enumerate(commentsdata):
            for idx_value, i_value in enumerate(i_row):
                if type(i_value) is OrderedMapSerializedKey:
                    commentsdata[idx_row][idx_value] = dict(commentsdata[idx_row][idx_value])

        data = commentsdata.comments

        dic1List = []
        ResultDict=[]
        for key, value in enumerate(data):
            dic1 = {}
            for key_time, value_commentContent in value.items():
                key_time_str = str(key_time)
                dic1[key_time_str] = value_commentContent
                dic1List.append(dic1)
                for k1, v1 in dic1.items():
                    dic2 = {}
                    for k2,v2 in v1.items():
                        dic2['Author'] = k2
                        dic2['CommentContent'] = v2
                        dic2['updatestamp'] = k1
                        ResultDict.append(dic2)

        statusCode = 1
    except Exception as e:
        print(e)
        statusCode = 0
    finally:
        if statusCode == 1:
           resp = jsonify(ResultDict)
           resp.status_code = 200
           return resp
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
#class Article(Resource):
#    def get(self, name):
#        conn = db_conneect .connnect()
#        for article in articles:
#            if(name == user["name"]):
#                return article, 200
#        return "Article not found, 404
