from flask import Flask,redirect,url_for,render_template,request,flash,abort\
,session
from flask_session import Session
from key import secret_key,salt1,salt2,salt3
from s_token import token
from cmail import sendmail
import flask_excel as excel
from itsdangerous import URLSafeTimedSerializer
import mysql.connector
app=Flask(__name__)
app.secret_key=secret_key
app.config['SESSION_TYPE']='filesystem'
Session(app)
excel.init_excel(app)
mydb=mysql.connector.connect(host='localhost',user='root',password='CHsrinu@506',db='prm')
@app.route('/')
def index():
    return render_template('title.html')
@app.route('/login',methods=['GET','POST'])
def login():
    if session.get('user'):
        return redirect(url_for('home'))
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from users where username=%s',[username])
        count=cursor.fetchone()[0]
        if count==1:
            cursor.execute('select count(*) from users where username=%s and password=%s',[username,password])
            p_count=cursor.fetchone()[0]
            if p_count==1:
                session['user']=username
                cursor.execute('select email_status from users where username=%s',[username])
                status=cursor.fetchone()[0]
                cursor.close()
                if status!='confirmed':
                    return redirect(url_for('inactive'))
                else:
                    return redirect(url_for('home'))
            else:
                cursor.close()
                flash('invalid password')
                return render_template('login.html')
        else:
            cursor.close()
            flash('invalid username')
            return render_template('login.html')
    return render_template('login.html')
@app.route('/inactive')
def inactive():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from users where username=%s',[username])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            return redirect(url_for('home'))
        else:
            return render_template('inactive.html')
    else:
        return redirect(url_for('login'))    
@app.route('/home')
def home():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from users where username=%s',[username])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            return render_template('homepage.html')
        else:
            return redirect(url_for('inactive'))
    else:
        return redirect(url_for('login'))
@app.route('/resend')
def resend():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from users where username=%s',[username])
        status=cursor.fetchone()[0]
        cursor.execute('select email from users where username=%s',[username])
        email=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            flash('Email already confirmed')
            return redirect(url_for('home'))
        else:
            subject='Email Confirmation'
            confirm_link=url_for('confirm',token=token(email,salt1),_external=True)
            body=f"Please confirm your mail-\n\n{confirm_link}"
            sendmail(to=email,body=body,subject=subject)
            flash('confirmation link sent check your email')
            return redirect(url_for('inactive'))
    else:
        return redirect(url_for('login'))
@app.route('/registration',methods=['GET','POST'])
def registration():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        try:
            cursor.execute('insert into users (username,password,email) values(%s,%s,%s)',(username,password,email))
        except mysql.connector.IntegrityError:
            flash('username or email is already in use')
            render_template('registration.html')
        else:
            mydb.commit()
            cursor.close()
            subject='Email Confirmation'
            confirm_link=url_for('confirm',token=token(email,salt1),_external=True)
            body=f"Thanks for signing up.Follow this link-\n\n{confirm_link}"
            sendmail(to=email,body=body,subject=subject)
            flash('confirmation link sent check your email')
            return render_template('registration.html') 
    return render_template('registration.html')
@app.route('/confirm/<token>')
def confirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        email=serializer.loads(token,salt=salt1,max_age=180)
    except Exception as e:
        print(e)
        abort(404,'Link expired')
    else:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from users where email=%s',[email])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            flash('Email already confirmed')
            return redirect(url_for('login'))
        else:
            cursor=mydb.cursor(buffered=True)
            cursor.execute("update users set email_status='confirmed' where email=%s",[email])
            mydb.commit()
            flash('Email confirmation success')
            return redirect(url_for('login'))
@app.route('/forgot',methods=['GET','POST'])
def forgot():
    if request.method=='POST':
        email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from users where email=%s',[email])
        count=cursor.fetchone()[0]
        cursor.close()
        if count==1:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select email_status from users where email=%s',[email])
            status=cursor.fetchone()[0]
            cursor.close()
            if status!='confirmed':
                flash('Please confirm your email first')
                return render_template('forgot.html')
            else:
                subject='Forgot password'
                confirm_link=url_for('reset',token=token(email,salt=salt2),_external=True)
                body=f"use this link to reset your password-\n\n{confirm_link}"
                sendmail(to=email,body=body,subject=subject)
                flash('reset link sent check your email')
                return redirect(url_for('login'))
        else:
            flash('Invalid email id')
            return render_template('forgot.html')
    return render_template('forgot.html')    
@app.route('/reset/<token>',methods=['GET','POST'])
def reset(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        email=serializer.loads(token,salt=salt2,max_age=180)
    except Exception as e:
        print(e)
        abort(404,'Link expired')
    else:
        if request.method=='POST':
            newpassword=request.form['npassword']
            confirmpassword=request.form['cpassword']
            if newpassword==confirmpassword:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update users set password=%s where email=%s',[newpassword,email])
                mydb.commit()
                flash('reset successful') 
                return redirect(url_for('login'))
            else:
                flash('password mismatched')   
                return render_template('newpassword.html') 
        return render_template('newpassword.html')      
@app.route('/logout')
def logout():
    if session.get('user'):
        session.pop('user')
        return redirect(url_for('login'))
    else:
        return redirect(url_for('login'))        

'''@app.route('/fdform',methods=['GET','POST'])
def fdform():
    if session.get('user'):
        return render_template('fdform.html') 
    else:
        return redirect(url_for('login'))'''  
@app.route('/submit')
def submit():
    if session.get('user'):
        return 'Feedback Form Submitted Successfully'  
    else:
        return redirect(url_for('login'))  
 
import random,string
def rand_pass(size):
	generate_pass = ''.join([random.choice( string.ascii_uppercase +
											string.ascii_lowercase +
											string.digits)
											for n in range(size)])
							
	return generate_pass
 
@app.route('/create',methods=['GET','POST'])
def create():
    if session.get('user'):
        if request.method=='POST':
            sid=rand_pass(10)
            sur_link=url_for('fdlink',token=(sid,salt3),_external=True)
            cursor=mydb.cursor(buffered=True)
            cursor.execute('insert into survey (sid,sur_link) values(%s,%s)',[sid,sur_link])
            mydb.commit()
            cursor.close()
            return redirect(url_for('home'))
        return render_template('fdform.html')
    else:
        return redirect(url_for('login')) 
    
@app.route('/fdlink/<token>')
def fdlink(token):
    sid=request.form['sid']
    try:
        serializer=URLSafeTimedSerializer(sid,salt3)
        link=serializer.loads(token,salt=salt3,max_age=180)
    except Exception as e:
        print(e)
        abort(404,'Link expired')
    else:    
        flash('the feedback form send to your mail')  
        print(link) 
        return render_template('fdform.html')
@app.route('/report',methods=['GET','POST'])
def report():
    if session.get('user'):   
        return render_template('fdtable.html')
    else:
        return redirect(url_for('login'))  
'''@app.route('/download/<sid>')
def download():
    cursor=mydb.cursor(buffered=True)
    lst=['Name','Roll Number','Email','Python','Operating System','Data structures','Mysql','Flask Frame Work','Feedback']
    cursor.execute('select *from sur_data where sid=%s',[sid])
    user_data=[list(i)[1:] for i in cursor.fetchall()]
    print(user_data)
    return excel.make_response_from_array(user_data,'xlsx',file_name='student_data')'''
app.run(debug=True,use_reloader=True)

            