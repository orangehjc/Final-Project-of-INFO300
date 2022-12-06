# Web Search with Flask and ElasticSearch

October 14， 2022

## Purpose

This tutorial is to outline the process to create web search engine interface based on: 

+ `Flask` web framework (in Python)
+ Python's `elasticsearch` module
+ An index on an `ElasticSearch` server

## Setup 

Make sure you have Flask and ElasticSearch modules installed in Python: 

```shell
pip3 install elasticsearch
pip3 install Flask
```

## Directories and Files

Create a new folder such as `search` in VS Code to host all project-related directories and files. 

Ultimately, these will be sub-folders (directories) and files for the project: 

```shell
search.py               # the main python file for flask
templates/              # sub-folder for templates (HTML pages)
         home.html      # home page with search box
         results.html   # search results page
static/                 # other files such as .css for page styles
```

## Test `hello` page

Create a file named `hello.py` in the project folder with the following code: 

```python
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello, World!'
```

Go to terminal (e.g. as part of VS Code): 

```shell
cd search   # go into the project folder if not yet there
set FLASK_ENV=development     # <- on Windows; otherwise: export FLASK_ENV=development
set FLASK_APP=hello.py        # <- on Windows; otherwise: export FLASK_APP=hello.py
flask run
```

After the Flask server is ready, visit the following on your browser: 

`http://127.0.0.1:5000/`

which should `Hello, World!` on the web page. 

## Home Page Template

In the `templates` sub-folder, create a `home.html` with the following content: 

```html
<!DOCTYPE html>
<html>
  <head>
    <title>Best Search Engine</title>
  </head>
  <body>
    <h1>Best Search Engine</h1>
    <form action="/search" method="get">
      <input type="text" id="keywords" name="keywords">
      <input type="submit" value="Search">
    </form>
  </body>
</html>
```

## Flask App to Load the Home Page

In the project folder, create a python file named `search.py` with the following: 

```python
from flask import Flask, url_for
from flask import request
from flask import render_template
import ssl
import base64
from elasticsearch import Elasticsearch
from elasticsearch.connection import create_ssl_context

# Create the web app with a `static` directory for static files
app = Flask(__name__, static_url_path='/static')

# home page
# the `/` is the root of your web app
@app.route('/')
def home():
    return render_template('home.html')
```

On the terminal, use `Ctrl+C` to end previously running Flask, if it is still running. 

Restart Flask with the following: 

```shell
set FLASK_ENV=development
set FLASK_APP=search.py        
flask run
```

Refresh (reload) your page in browser at: 

`http://127.0.0.1:5000/`

and it should show a page with a **input box** and a **search button**. 

If not, follow error messages to fix problems in the code. 

## Adding Code to Conduct Search

In this section, you may reuse code from your Python ElasticSearch exercise. 

### A. Connect to ElasticSearch

Add code to `search.py` to connect to the ElasticSearch server: 

```python
# Exsiting code
...
app = Flask(__name__, static_url_path='/static')

# Add the following
context = create_ssl_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

es = Elasticsearch(
    ['121.43.234.160'],
    scheme="http", 
    port=9201,
    http_auth=('your_username', base64.b64decode("MTIzNDU2c2hp").decode("utf-8")), 
    ssl_context=context
)
```

### B. New Route for `/search`

Then, create another `route` at the END fo your `search.py`: 

```python
# search result page
@app.route('/search', methods=['get'])
def search():
    keywords = request.args.get('keywords')
    # Include the keywords in a query object (JSON)
    query = {
        "from": 0, "size": 10, 
        "query": {
            "multi_match": {
                "query": keywords, 
                "fields": ["author", "title"]
            }
        }
    }

    # Send a search request with the query to server
    res = es.search(index="suwei_books", body=query)
    hits = res["hits"]["total"]["value"]
    return render_template('results.html', keywords=keywords, hits=hits, docs=res["hits"]["hits"])
```

What this function does is to: 

1. Search the ElasticSearch server index using the `keywords`. 
2. Retrieve the results in `res`. 
3. Load a template page named `results.html` with data in `keywords`, `hits`, and `docs` (based on `res`).

### C. Template for Results

Now, let's create a new template page named `results.html` under the `templates/` sub-folder. 

You can reuse the HTML code from `home.html` and change code in the `body` section so that it appears: 

```html
<body>
    <h1>Found {{hits}} for query {{keywords}}: </h1>
    {% for doc in docs %}
        <p>{{doc["_source"]['title']}} by {{doc["_source"]['author']}}</p>
    {% endfor %}
</body>
```

## Test the App

1. Go to: `http://127.0.0.1:5000/`
2. Enter some `keywords` that can match documents in your index. 
3. Hit the `search` button. 
4. It should get to `http://127.0.0.1:5000/search` page and show results. 
   
If there are issues, follow error messages to fix them. 

## Add link to each result
Enter code to add link to each retrieved result.
```html

```
## Style

We are going to use the following CSS framework to make the site look better: 
https://bulma.io/

We will go through steps in class if time allows. 
