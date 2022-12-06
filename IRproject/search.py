from flask import Flask, url_for
from flask import request
from flask import render_template
import ssl
import base64
from elasticsearch import Elasticsearch
from elasticsearch.connection import create_ssl_context


# Create the web app with a `static` directory for static files
app = Flask(__name__, static_url_path='/static')

# Add the following
context = create_ssl_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

es = Elasticsearch(
    ['localhost'],
    scheme="http", 
    port=9200,
     
    ssl_context=context
)

# home page
# the `/` is the root of your web app
@app.route('/')
def home():
    return render_template('home.html')


# search result page
@app.route('/search', methods=['get'])
def search():
    keywords = request.args.get('keywords')
    system = request.args.get('system')
    if system == "system1":
    # Include the keywords in a query object ()
        query = {
            "from": 0, "size": 200, 
            "query": {
                "multi_match": {
                    "query": keywords, 
                    "fields": ["author", "title","description","genres"]
                }
            }
        }
    elif system == "system2":
        query = {
        "from": 0, "size":200,
        "query":{
            "script_score": {
            "script": {"source":"_score*(doc['rating_average'].value)"},
            "query": {
                "multi_match":{
            "query": keywords,
            "fields":["author","title","description","genres"]
            }
            }
        }
        }
        }
    elif system == "system3":
        query = { 
            "from": 0,"size":200,
            "query":{
                "script_score": {
                "script": {"source":"_score*(doc['pages'].value/100+doc['rating_count'].value/100000)"},
                "query": {
                    "multi_match":{
                "query": keywords,
                "fields":["author","title","description","genres"]
                }
                }
            }
            }
            }
    # Send a search request with the query to server
    res = es.search(index=system, body=query)
    hits = res["hits"]["total"]["value"]
    return render_template('results.html', keywords=keywords, hits=hits, docs=res["hits"]["hits"])