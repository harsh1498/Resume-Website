from flask import Flask, render_template, request, make_response
from flask_mail import Mail, Message
import json
import sqlite3
import uuid

app = Flask(__name__)

app.config['MAIL_SERVER'] = "smtp.gmail.com"
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = "ctfadvert@gmail.com"
app.config['MAIL_PASSWORD'] = "wpduynivetwacocf"
app.config['MAIL_DEFAULT_SENDER'] = "ctfadvert@gmail.com"
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)


@app.route('/',methods=['GET','POST'])
def home():
    harsh = open('harsh.json','r')
    context = json.loads(harsh.read())
    harsh.close()
    if request.method == 'GET':
        if not request.cookies.get('user_id'):
            user_id = uuid.uuid4().hex
            conn = sqlite3.connect('app.db')
            c = conn.cursor()
            c.execute('INSERT INTO user (email,phone,cookie) VALUES("{}",{},"{}") '.format('ANON',0,user_id))
            c.execute('INSERT INTO counts (key,value,user_cookie) values("{}",{},"{}")'.format("visits",1,user_id))
            conn.commit()
            conn.close()
            resp = make_response(render_template('index.html',context=context[0]))
            resp.set_cookie('user_id',user_id)

        else:
            conn = sqlite3.connect('app.db')
            c = conn.cursor()
            c.execute('SELECT value FROM counts where key="visits" and user_cookie="{}"'.format(request.cookies.get('user_id')))
            visits = int(c.fetchone()[0])
            c.execute('UPDATE counts set value={} where key="visits" and user_cookie="{}"'.format(visits+1,request.cookies.get('user_id')))
            conn.commit()
            conn.close()
            resp = make_response(render_template('index.html',context=context[0]))


        return resp

    elif request.method == 'POST':
        body = "Phone Number: {} ; E-mail: {} ; Message: {}".format(request.form.get('phone'),request.form.get('e-mail'),request.form.get('message'))
        msg = Message("Someone is trying to reach you through your website!!!",recipients=["harsh3@umbc.edu"])
        msg.body = body
        mail.send(msg)

       
        user_id = request.cookies.get('user_id')

        if user_id:
            conn = sqlite3.connect('app.db')
            c = conn.cursor()
            c.execute('UPDATE user set email="{}",phone="{}" where cookie="{}"'.format(request.form.get('e-mail'),request.form.get('phone'),user_id))
            c.execute('INSERT INTO message (user_cookie,message) VALUES("{}","{}")'.format(user_id,request.form.get('message')))
            conn.commit()
            conn.close()
            resp = make_response(render_template('index.html',context=context[0]))

        else:
            user_id = uuid.uuid4().hex
            conn = sqlite3.connect('app.db')
            c = conn.cursor()
            c.execute('INSERT INTO user (email,phone,cookie) VALUES("{}",{},"{}") '.format(request.form.get('e-mail'),request.form.get('phone'),user_id))
            c.execute('INSERT INTO counts (key,value,user_cookie) values("{}",{},"{}")'.format("visits",1,user_id))
            conn.commit()
            conn.close()
            resp = make_response(render_template('index.html',context=context[0]))
            resp.set_cookie('user_id',user_id)

        return resp

if __name__ == '__main__':
    app.run(debug=True, port=5001)
