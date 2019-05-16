#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
from flask import Flask, request, url_for, jsonify, json, g, make_response
import sqlite3
import sys
from datetime import datetime
from functools import wraps
from passlib.hash import pbkdf2_sha256
import datetime
from rfeed import *


app = Flask(__name__)


class Slash(Extension):
    def get_namespace(self):
        return {"xmlns:slash" : "http://purl.org/rss/1.0/modules/slash/"}

class SlashItem(Serializable):
    def __init__(self, content):
        Serializable.__init__(self)
        self.comments = content

    def publish(self, handler):
        Serializable.publish(self, handler)
        self._write_element("slash:comments", self.comments)

@app.route("/comment_feed/<article_id>", methods = ['GET'])
def comment_feed(article_id):
    req = requests.get('http://localhost/articles/'+ article_id)
    article = req.json()
    items = []
    r = requests.get('http://localhost/comments/getncomments/'+ article_id, json = {"n" : "10"})
    arr = r.json()
    for i in range(0, len(r.json())):
        date_time_str = str(arr[i][1])
        date_time_obj = datetime.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S.%f')

        item1 = Item(
            title = arr[i][0],
            comments = arr[i][1],
            pubDate = date_time_obj)
        items.append(item1)

    feed = Feed(
        title = "Top comments for article",
        link = ("http://127.0.0.1/"+article_id),
        description = "Top comments for article",
        language = "en-US",
        lastBuildDate = datetime.datetime.now(),
        items = items)

    return (feed.rss())

@app.route("/summary_feed", methods = ['GET'])
def summary_feed():
    r = requests.get('http://localhost/articles', json = {"n" : "10"})
    arr = r.json()
    items = []
    for i in range(0, len(arr)):
        date_time_str = str(arr[i][3])
        date_time_obj = datetime.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S.%f')
        item1 = Item(
            title = arr[i][1],
            link = arr[i][5],
            author = arr[i][6],
            pubDate = date_time_obj)
        items.append(item1)

    feed = Feed(
        title = "Articles RSS Feed",
        link = "http://www.articles.com/rss",
        description = "Generate RSS Feeds for Articles",
        language = "en-US",
        lastBuildDate = datetime.datetime.now(),
        items = items)

    return (feed.rss())

@app.route("/full_feed/<article_id>", methods = ['GET'])
def full_feed(article_id):
    req_article = requests.get('http://localhost/articles/'+ article_id)
    article = req_article.json()
    req_tags = requests.get('http://localhost/get_tags/'+ article_id)
    tags = req_tags.json();
    req_comment_count = requests.get('http://localhost/comments/getcommentcount/'+ article_id)
    comment_count = req_comment_count.json()
    items = []
    tags_arr = []
    for i in range (0, len(tags)):
        tags_arr.append(''.join(tags[i]))
    date_time_str = str(article[3])
    date_time_obj = datetime.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S.%f')
    item1 = Item(
        title = article[1],
        description = article[2],
        link = article[5],
        author = article[6],
        categories = tags_arr,
        pubDate = date_time_obj,
        extensions = [SlashItem(comment_count)])
    items.append(item1)
    feed = Feed(
        title = "Artciles RSS Feed",
        link = "http://www.articles.com/rss",
        description = "Generate RSS Feeds for Articles",
        language = "en-US",
        lastBuildDate = datetime.datetime.now(),
        extensions = [Slash()],
        items = items)

    return (feed.rss())
