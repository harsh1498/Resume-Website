from flask import Flask, render_template, request, make_response,redirect,url_for, send_file
import requests
import json
import sqlite3
import uuid
import html
import re
import os
from validate_email import validate_email
import phonenumbers
from phonenumbers import geocoder, carrier
import markdown

md = markdown.Markdown()

DATABASE_FILE_NAME = "app.db"

app = Flask(__name__)

app.config['RESUME_PATH'] = "~/"
app.config['RESUME_NAME'] = "resume.pdf"
app.config['ARTICLE_PATH'] = "./articles"
CONTEXT = {}
BLOGS = []


@app.route('/pdfresume/',methods=["GET"])
def download_file():
    #return "hello"
    return send_file('resume.pdf')

def get_visits(user_id):
    conn = sqlite3.connect(DATABASE_FILE_NAME)
    c = conn.cursor()
    c.execute('SELECT value FROM counts where key="visits" and user_cookie="{}"'.format(user_id))
    visits = c.fetchone()
    conn.commit()
    conn.close()
    if visits != None:
        visits = int(visits[0])
    return visits

def update_user(name,email,phone,user_id,message):
    conn = sqlite3.connect(DATABASE_FILE_NAME)
    c = conn.cursor()
    c.execute('UPDATE user set name="{}",email="{}",phone="{}" where cookie="{}"'.format(name,email,phone,user_id))
    c.execute('INSERT INTO message (user_cookie,message) VALUES("{}","{}")'.format(user_id,message))
    conn.commit()
    conn.close()

def new_user(name,email,phone,user_id):
    conn = sqlite3.connect(DATABASE_FILE_NAME)
    c = conn.cursor()
    c.execute('INSERT INTO user (name,email,phone,cookie) VALUES("{}","{}",{},"{}") '.format(name,email,phone,user_id))
    c.execute('INSERT INTO counts (key,value,user_cookie) values("{}",{},"{}")'.format("visits",1,user_id))
    conn.commit()
    conn.close()

def new_anon_user(user_id):
    conn = sqlite3.connect(DATABASE_FILE_NAME)
    c = conn.cursor()
    c.execute('INSERT INTO user (name,email,phone,cookie) VALUES("{}","{}",{},"{}") '.format('ANON','ANON',0,user_id))
    c.execute('INSERT INTO counts (key,value,user_cookie) values("{}",{},"{}")'.format("visits",1,user_id))
    conn.commit()
    conn.close()


def store_metadata(remote_addr,user_agent,user_id):
    conn = sqlite3.connect(DATABASE_FILE_NAME)
    c = conn.cursor()
    c.execute('SELECT user_cookie from metadata where key="visits_from_{}" and value="{}" and user_cookie="{}"'.format(user_agent,user_agent,user_id))
    results = c.fetchall()
    if not results:
        c.execute('INSERT INTO metadata (key,value,user_cookie) values("visits_from_{}","{}","{}")'.format(user_agent,user_agent,user_id))
    else:
        c.execute('SELECT value from counts where key="visits_from_{}" and user_cookie="{}"'.format(user_agent,user_id))
        visits = c.fetchone()
        if not visits:
            c.execute('INSERT INTO counts (key,value,user_cookie) VALUES("visits_from_{}","{}","{}")'.format(user_agent,1,user_id))
        else:
            c.execute('UPDATE counts set value={} where user_cookie="{}" and key="visits_from_{}"'.format(int(visits[0])+1,user_id,user_agent))

    conn.commit()
    conn.close()

def collect_metadata():
    remote_addr = html.escape(str(request.remote_addr))
    user_agent = html.escape(str(request.user_agent))
    return remote_addr, user_agent

def update_counts(user_id, value, key):
    conn = sqlite3.connect(DATABASE_FILE_NAME)
    c = conn.cursor()
    c.execute('UPDATE counts set value={} where key="{}" and user_cookie="{}"'.format(value,key,user_id)) 
    conn.commit()
    conn.close()

def get_user_info(user_id):
    conn = sqlite3.connect(DATABASE_FILE_NAME)
    c = conn.cursor()
    c.execute('SELECT name,email,phone from user where cookie="{}"'.format(user_id))
    visitor = c.fetchone()
    c.execute('SELECT message from message where user_cookie="{}"'.format(user_id))
    visitors_message = c.fetchone()
    if visitor == None or visitors_message == None:
        return [None,None,None,None]
    return visitor+visitors_message

def cookie_management(template,article_index=None):
    remote_addr,user_agent = collect_metadata()
    # Try to get the user's cookie
    user_id = request.cookies.get('user_id')

    # And the user does not have a cookie defined
    if not user_id:
        # Define a new user cookie
        user_id = html.escape(str(uuid.uuid4().hex))
        # Insert a new ANON user into the database
        new_anon_user(user_id)
        # Updates store ANON user's metadata
        store_metadata(remote_addr,user_agent,user_id)
        # Generate a response object 
        if article_index:
            resp = make_response(render_template(template,context=CONTEXT[0],article=BLOGS[article_index-1]))
        else:
            resp = make_response(render_template(template,context=CONTEXT[0],blogs=BLOGS))
        resp.set_cookie('user_id',user_id)
    else:
        # Get user's cookie
        user_id = html.escape(str(user_id))
        # Get visits
        visits = get_visits(user_id)
        # Update visits key
        update_counts(user_id,visits+1,"visits")
        visitors_name, visitors_email, visitors_phone, visitors_message = get_user_info(user_id)
        # Updates store ANON user's metadata
        store_metadata(remote_addr,user_agent,user_id)
        # Create the response object
        if article_index:
            resp = make_response(render_template(template,context=CONTEXT[0],article=BLOGS[article_index-1],visitors_name=visitors_name,visitors_message=visitors_message,visitors_email=visitors_email,visitors_phone=visitors_phone))
        else:
            resp = make_response(render_template(template,context=CONTEXT[0],blogs=BLOGS,visitors_name=visitors_name,visitors_message=visitors_message,visitors_email=visitors_email,visitors_phone=visitors_phone))

    return resp

@app.route('/',methods=['GET','POST'])
def index():
    # Get User's Metadata
    remote_addr,user_agent = collect_metadata()

    # If the user makes a get request
    if request.method == 'GET':
        resp = cookie_management("index.html")
        return resp

    elif request.method == 'POST':
        # Get data from form
        name = html.escape(str(request.form.get('name')))
        phone = html.escape(str(request.form.get('phone')))
        email = html.escape(str(request.form.get('e-mail')))
        message = html.escape(str(request.form.get('message')))

        if not (validate_email(email) and phonenumbers.is_possible_number(phonenumbers.parse(phone,"US")) and phonenumbers.is_valid_number(phonenumbers.parse(phone,"US"))):  
            url = '/'
            resp = make_response(redirect(url))
            return resp
        else:
            phone_number = phone
            phone = phonenumbers.parse(phone,"US")
            phone_desc = geocoder.description_for_number(phone,"en")
            phone_carrier = carrier.name_for_number(phone,"en")

        # Get their user cookie
        user_id = html.escape(str(request.cookies.get('user_id')))

        # Get visits for user
        visits = get_visits(user_id)

        # Construct a body for the message
        body = "Name: {} ; Visits:{} ; Phone Number: {} ; Phone Description: {} ; Phone Carrier: {} ; E-mail: {} ; Message: {}".format(name,visits,phone_number,phone_desc,phone_carrier,email,message)
        # Post the message to slack
        requests.post("https://hooks.slack.com/services/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",json={"text":body})

        if user_id:
            # Update existign user
            update_user(name,email,phone,user_id,message)
            
            url = '/'

            # Redirect to index, as a get request
            resp = make_response(redirect(url))

        else:
            # Generate user_id
            user_id = html.escape(str(uuid.uuid4().hex))

            # Generate new user
            new_user(name,email,phone,user_id)

            url = '/'

            # Make a response object, set cookie
            resp = make_response(redirect(url))
            resp.set_cookie('user_id',user_id)
        
        # Return response
        return resp

@app.route('/blog',methods=['GET'])
def blog():
    resp = cookie_management("blog.html")
    return resp

@app.route('/article',methods=['GET'])
def article():
    try:
        article_index = int(request.args.get('article', None))
    except ValueError:
        return redirect(url_for('blog'))
    if article_index == None or article_index > len(BLOGS):
        return redirect(url_for('blog'))
    resp = cookie_management("article.html",article_index=article_index)
    return resp



if __name__ == '__main__':
    with open('harsh.json','r') as harsh:
        CONTEXT = json.loads(harsh.read())
    for filename in os.listdir(app.config['ARTICLE_PATH']): 
        with open(os.path.join(app.config['ARTICLE_PATH'],filename),'r') as f:
            BLOGS.append(json.loads(f.read()))

    app.run(debug=False,host="0.0.0.0", port=5000)
