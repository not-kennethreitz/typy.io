#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import hashlib

import bucketstore
import mistune
from decouple import config
from flask import Flask, request, render_template, jsonify, redirect, url_for, Response
from flask_caster import FlaskCaster
from flask_uuid import FlaskUUID
from raven.contrib.flask import Sentry

from saferproxyfix import SaferProxyFix


# Support for gomix's 'front-end' and 'back-end' UI.
app = Flask(__name__, static_folder='public', template_folder='views')
app.debug = config('DEBUG', default=True, cast=bool)
# app.wsgi_app = SaferProxyFix(app.wsgi_app)

# Set the app secret key from the secret environment variables.
app.secret = config('SECRET')


# Flask plugins

caster = FlaskCaster(app)
FlaskUUID(app)
sentry = Sentry(app, dsn=config('SENTRY_DSN'))

# The S3 Key/Value store.
store = bucketstore.get('typy', create=True)
store_total = len(store.list())

@app.after_request
def apply_kr_hello(response):
  """Adds some headers to all responses."""
  
  # Made by Kenneth Reitz. 
  if 'MADE_BY' in os.environ:
    response.headers["X-Was-Here"] = os.environ.get('MADE_BY')
    
  # Powered by Flask. 
  response.headers["X-Powered-By"] = os.environ.get('POWERED_BY')
  return response


@app.route('/')
def type_away(fork=None):
  if fork:
    doc = store[fork]
  else:
    doc = None
    
  return render_template('write.html', total=store_total, seed=doc)

@app.route('/raw')
def document_list():
  return jsonify({'documents': store.list()})


@app.route('/', methods=['POST'])
def put_type():
  doc = request.form['document']

  # Sha256 of document.
  sha = hashlib.sha256(doc).hexdigest()

  # Store the document.
  store[sha] = doc
  
  return redirect(url_for('get_type', hash=sha))


@app.route('/<hash>')
def get_type(hash):
  doc = mistune.markdown(store[hash])
  return render_template('doc.html', doc=doc, hash=hash, total=store_total)


@app.route('/<hash>/raw')
def get_raw_type(hash):
  return Response(store[hash], mimetype='text/plain')

@app.route('/<hash>/fork')
def fork_type(hash):
  return type_away(fork=hash)



if __name__ == '__main__':
  app.run()