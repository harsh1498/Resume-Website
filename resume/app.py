from flask import Flask, render_template, request, make_response,redirect
import requests
import json
import sqlite3
import uuid
import html

app = Flask(__name__)


@app.route('/',methods=['GET','POST'])
def home():
    harsh = open('harsh.json','r')
    context = json.loads(harsh.read())
    harsh.close()

    remote_addr = html.escape(str(request.remote_addr))
    user_agent = html.escape(str(request.user_agent))
    
    if request.method == 'GET':
        if not request.cookies.get('user_id'):
            user_id = html.escape(str(uuid.uuid4().hex))
            conn = sqlite3.connect('app.db')
            c = conn.cursor()
            c.execute('INSERT INTO user (name,email,phone,cookie) VALUES("{}","{}",{},"{}") '.format('ANON','ANON',0,user_id))
            c.execute('INSERT INTO counts (key,value,user_cookie) values("{}",{},"{}")'.format("visits",1,user_id))
            c.execute('INSERT INTO metadata (key,value,user_cookie) values("{}","{}","{}")'.format("remote_addr",remote_addr,user_id))
            c.execute('INSERT INTO metadata (key,value,user_cookie) values("{}","{}","{}")'.format("user_agent",user_agent,user_id))
            conn.commit()
            conn.close()
            resp = make_response(render_template('index.html',context=context[0]))
            resp.set_cookie('user_id',user_id)

        else:
            conn = sqlite3.connect('app.db')
            c = conn.cursor()
            user_id = html.escape(str(request.cookies.get('user_id')))
            c.execute('SELECT value FROM counts where key="visits" and user_cookie="{}"'.format(user_id))
            visits = c.fetchone()
            if visits != None:
                visits = int(visits[0])
            else:
                user_id = html.escape(str(uuid.uuid4().hex))
                conn = sqlite3.connect('app.db')
                c = conn.cursor()
                c.execute('INSERT INTO user (name,email,phone,cookie) VALUES("{}","{}",{},"{}") '.format('ANON','ANON',0,user_id))
                c.execute('INSERT INTO counts (key,value,user_cookie) values("{}",{},"{}")'.format("visits",1,user_id))
                c.execute('INSERT INTO metadata (key,value,user_cookie) values("{}","{}","{}")'.format("remote_addr",remote_addr,user_id))
                c.execute('INSERT INTO metadata (key,value,user_cookie) values("{}","{}","{}")'.format("user_agent",user_agent,user_id))
                conn.commit()
                conn.close()
                resp = make_response(render_template('index.html',context=context[0]))
                resp.set_cookie('user_id',user_id)
                return resp

            c.execute('UPDATE counts set value={} where key="visits" and user_cookie="{}"'.format(visits+1,user_id))
            c.execute('INSERT INTO metadata (key,value,user_cookie) values("{}","{}","{}")'.format("remote_addr",remote_addr,user_id))
            c.execute('INSERT INTO metadata (key,value,user_cookie) values("{}","{}","{}")'.format("user_agent",user_agent,user_id))
            conn.commit()
            conn.close()
            resp = make_response(render_template('index.html',context=context[0]))

        return resp

    elif request.method == 'POST':
        name = html.escape(str(request.form.get('name')))
        phone = html.escape(str(request.form.get('phone')))
        email = html.escape(str(request.form.get('e-mail')))
        message = html.escape(str(request.form.get('message')))
 
        body = "Name: {} ; Phone Number: {} ; E-mail: {} ; Message: {}".format(name,phone,email,message)

        requests.post("https://hooks.slack.com/services/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",json={"text":body})


        user_id = html.escape(str(request.cookies.get('user_id')))

        if user_id:
            conn = sqlite3.connect('app.db')
            c = conn.cursor()
            c.execute('UPDATE user set name="{}",email="{}",phone="{}" where cookie="{}"'.format(name,email,phone,user_id))
            c.execute('INSERT INTO message (user_cookie,message) VALUES("{}","{}")'.format(user_id,message))
            conn.commit()
            conn.close()
            resp = make_response(redirect('/'))

        else:
            user_id = html.escape(str(uuid.uuid4().hex))
            conn = sqlite3.connect('app.db')
            c = conn.cursor()
            c.execute('INSERT INTO user (name,email,phone,cookie) VALUES("{}","{}",{},"{}") '.format(name,email,phone,user_id))
            c.execute('INSERT INTO counts (key,value,user_cookie) values("{}",{},"{}")'.format("visits",1,user_id))
            conn.commit()
            conn.close()
            resp = make_response(redirect('/'))
            resp.set_cookie('user_id',user_id)

        return resp

if __name__ == '__main__':
    app.run(debug=True, port=5001)
