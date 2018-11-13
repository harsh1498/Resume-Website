from flask import Flask, render_template, request, make_response,redirect,url_for, send_file
import requests
import json
import sqlite3
import uuid
import html


DATABASE_FILE_NAME = "app.db"

app = Flask(__name__)

app.config['RESUME_PATH'] = "~/"
app.config['RESUME_NAME'] = "resume.pdf"
CONTEXT = {}

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

@app.route('/',methods=['GET','POST'])
def index():


    # Get User's Metadata
    remote_addr,user_agent = collect_metadata()

    # If the user makes a get request
    if request.method == 'GET':
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
            resp = make_response(render_template('index.html',context=CONTEXT[0]))
            resp.set_cookie('user_id',user_id)

        else:
            # Get user's cookie
            user_id = html.escape(str(request.cookies.get('user_id')))

            # Get visits
            visits = get_visits(user_id)
            
            if visits == None:
                # Define a new user cookie
                user_id = html.escape(str(uuid.uuid4().hex))

                # Insert a new ANON user into the database
                new_anon_user(user_id)

                # Updates store ANON user's metadata
                store_metadata(remote_addr,user_agent,user_id)

                # Make a response object, set cookie, and redirect
                resp = make_response(render_template('index.html',context=CONTEXT[0]))
                resp.set_cookie('user_id',user_id)

            else:
                # Update visits key
                conn = sqlite3.connect(DATABASE_FILE_NAME)
                c = conn.cursor()
                c.execute('UPDATE counts set value={} where key="visits" and user_cookie="{}"'.format(visits+1,user_id)) 
                c.execute('SELECT name,email,phone from user where cookie="{}"'.format(user_id))
                visitors_name = c.fetchone()
                c.execute('SELECT message from message where user_cookie="{}"'.format(user_id))
                visitors_message = c.fetchone()

                if visitors_name != None and visitors_message != None:
                    print(visitors_name)
                    visitors_name,visitors_email,visitors_phone = visitors_name
                    visitors_message = visitors_message[0]
                else:
                    visitors_name = None
                    visitors_email = None
                    visitors_phone = None
                    visitors_message = None
                
                conn.commit()
                conn.close()
                
                # Updates store ANON user's metadata
                store_metadata(remote_addr,user_agent,user_id)
                


                # Create the response object
                resp = make_response(render_template('index.html',context=CONTEXT[0],visitors_name=visitors_name,visitors_message=visitors_message,visitors_email=visitors_email,visitors_phone=visitors_phone))

        return resp

    elif request.method == 'POST':
        # Get data from form
        name = html.escape(str(request.form.get('name')))
        phone = html.escape(str(request.form.get('phone')))
        email = html.escape(str(request.form.get('e-mail')))
        message = html.escape(str(request.form.get('message')))
 
        # Get their user cookie
        user_id = html.escape(str(request.cookies.get('user_id')))

        # Get visits for user
        visits = get_visits(user_id)

        # Construct a body for the message
        body = "Name: {} ; Visits:{} ; Phone Number: {} ; E-mail: {} ; Message: {}".format(name,visits,phone,email,message)

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

if __name__ == '__main__':
    harsh = open('harsh.json','r')
    CONTEXT = json.loads(harsh.read())
    harsh.close()
    app.run(debug=True,host="0.0.0.0", port=80)
