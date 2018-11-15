#!/usr/bin/env python2.7

"""
Columbia W4111 Intro to databases
Project 1 Part 3
Chenling Yang
Go to http://localhost:8111 in your browser
"""
import pdb
import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, session, flash, url_for
from flask_table import Table, Col, LinkCol

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

DB_USER = "cy2472"
DB_PASSWORD = "g7cu7643"

DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/w4111"

##################################################################################
# This line creates a database engine that knows how to connect to the URI above
##################################################################################
engine = create_engine(DATABASEURI)

@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request

  The variable g is globally accessible
  """
  try:
    g.conn = engine.connect()
  except:
    print "uh oh, problem connecting to database"
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass

##################################################################################
# index page
##################################################################################
@app.route('/')
def index():
    if 'uid' in session:
        uid = session['uid']
        cursor = g.conn.execute("SELECT name FROM Users "
                                "WHERE uid = %s", (uid,))
        name = cursor.next()[0]
        cursor.close()
        return render_template('dashboard.html', name=name)
    else:
        return render_template('login.html')



##################################################################################
# login page
###################################################################################
@app.route('/login', methods=['POST'])
def login():
    POST_USERNAME = str(request.form['username'])
    POST_PASSWORD = str(request.form['password'])

    # check if there is matched user record in the db
    if 'uid' not in session:
        try:
            cursor = g.conn.execute("SELECT uid FROM Users "
                                    "WHERE username = %s AND "
                                    "password = %s;", (POST_USERNAME, POST_PASSWORD))
            session['uid'] = cursor.next()[0]
            cursor.close()
        except:
            flash('username/password not matched!')
    return index()



##################################################################################
# logout page
##################################################################################
@app.route('/logout')
def logout():
    # remove the username from the session if it's there
    session.pop('uid', None)
    return redirect(url_for('index'))



##################################################################################
# create a new user
##################################################################################
@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')

    # fetch sign-up info, all fields cannot be null.
    POST_USERNAME = str(request.form['username'])
    POST_NAME = str(request.form['name'])
    POST_PASSWORD = str(request.form['password'])
    if not (POST_USERNAME and POST_PASSWORD and POST_NAME ):
        flash('All fields cannot be null.')
        return redirect(url_for('signup'))

    # create new record in db
    cursor = g.conn.execute("SELECT MAX(uid) FROM Users;")
    curuid = cursor.next()[0] + 1
    cursor.close()
    try:
        # usernames are set to be unique, if violate ICs, redirect to another sign-up page
        g.conn.execute("INSERT INTO Users(uid, username, name, password) VALUES"
                        "(%s, %s, %s, %s);", (curuid, POST_USERNAME, POST_NAME, POST_PASSWORD))
    except:
        flash('User cannot be created.')
        return redirect(url_for('signup'))
    flash('User created.')
    return redirect(url_for('index'))


##################################################################################
# Use Flask_table module to generate html table for Payment/Deposit Options
# (third-party library)
##################################################################################
class PayDepositResults(Table):
    oid = Col('Id', show=False)
    oname = Col('Name')
    olabel = Col('Label')
    odescription = Col('Description')
    # Called edit_paydeposit() when the link is clicked.
    edit = LinkCol('Edit', 'edit_paydeposit', url_kwargs=dict(oid='oid'))
    # Called delete_paydeposit() when the link is clicked.
    delete = LinkCol('Delete', 'delete_paydeposit', url_kwargs=dict(oid='oid'))

##################################################################################
# view payment/deposit options
##################################################################################
@app.route('/paydeposit', methods=['POST', 'GET'])
def paydeposit():
    cursor = g.conn.execute("SELECT * FROM Payment_Deposit_Options WHERE uid = %s ORDER BY oid", (session['uid'],))
    results = []
    for result in cursor:
        results.append({'oid': result['oid'],
                        'oname': result['oname'],
                        'olabel': result['olabel'],
                        'odescription': result['odescription']})
    cursor.close()
    table = PayDepositResults(results)
    table.border = True
    return render_template('paydeposit.html', table=table)

##################################################################################
# add new payment/deposit option
##################################################################################
@app.route('/add_paydeposit', methods=['POST', 'GET'])
def add_paydeposit():
    if request.method == 'GET':
        return render_template("add_paydeposit.html")
    
    POST_ONAME = request.form['oname']
    POST_OLABEL = request.form['olabel']
    POST_ODESCRIPTION = request.form['odescription']
    if not POST_ONAME:
        flash('name should not be null.')
        return redirect(url_for('add_paydeposit'))

    # create new record in db
    cursor = g.conn.execute("SELECT MAX(oid) FROM Payment_Deposit_Options;")
    curoid = cursor.next()[0] + 1
    cursor.close()
    try:
        # if violate ICs, redirect to another add payment/deposit option page

        g.conn.execute("INSERT INTO Payment_Deposit_Options(oid, oname, olabel, odescription, uid) VALUES "
                       "(%s,  %s, %s, %s, %s);", (curoid, POST_ONAME, POST_OLABEL, POST_ODESCRIPTION, session['uid']))
    except:
        flash('Payment/deposit option cannot be created.')
        return redirect(url_for('add_paydeposit'))
    flash('Option created.')
    return redirect(url_for('paydeposit'))

##################################################################################
# edit a payment/deposit option
##################################################################################
@app.route('/edit_paydeposit/<int:oid>', methods=['GET', 'POST'])
def edit_paydeposit(oid):
    if request.method == 'GET':
        cursor = g.conn.execute("SELECT * FROM Payment_Deposit_Options WHERE oid = %s", (oid,))
        record = cursor.next()
        cursor.close()
        return render_template("edit_paydeposit.html", oid=oid, oname=record['oname'],
                               olabel=record['olabel'], odescription=record['odescription'])

    POST_ONAME = request.form['oname'].rstrip()
    POST_OLABEL = request.form['olabel'].rstrip()
    POST_ODESCRIPTION = request.form['odescription'].rstrip()
    if not POST_ONAME:
        flash('name should not be null.')
        return redirect('/edit_paydeposit/{oid}'.format(oid=oid))

    try:
        g.conn.execute("UPDATE Payment_Deposit_Options SET oname=%s, olabel=%s, odescription=%s "
                       "WHERE oid=%s;", (POST_ONAME, POST_OLABEL, POST_ODESCRIPTION, oid))
    except:
        flash('Option cannot be updated!')
        return redirect(url_for('paydeposit'))
    flash('Option updated successfully!')
    return redirect(url_for('paydeposit'))


##################################################################################
# delete a payment/deposit option
##################################################################################
@app.route('/delete_paydeposit/<int:oid>', methods=['GET', 'POST'])
def delete_paydeposit(oid):
    if request.method == 'GET':
        return render_template("delete_paydeposit.html", oid=oid)

    # delete the item from the database
    try:
        g.conn.execute("DELETE FROM Payment_Deposit_Options WHERE oid = %s;", (oid,))
        flash('Option deleted successfully!')
    except:
        flash('Option cannot be deleted!')
        return redirect(url_for("paydeposit"))
    return redirect(url_for("paydeposit"))


##################################################################################
# Use Flask_table module to generate html table for People
# (third-party library)
##################################################################################
class People(Table):
    pid = Col('Id', show=False)
    pname = Col('Name')
    plabel = Col('Label')
    pdescription = Col('Description')
    # Called edit_people() when the link is clicked.
    edit = LinkCol('Edit', 'edit_people', url_kwargs=dict(pid='pid'))
    # Called delete_people() when the link is clicked.
    delete = LinkCol('Delete', 'delete_people', url_kwargs=dict(pid='pid'))


##################################################################################
# view people
##################################################################################
@app.route('/people', methods=['POST', 'GET'])
def people():
    cursor = g.conn.execute("SELECT * FROM People WHERE uid = %s ORDER BY pid", (session['uid'],))
    results = []
    for result in cursor:
        results.append({'pid': result['pid'],
                        'pname': result['pname'],
                        'plabel': result['plabel'],
                        'pdescription': result['pdescription']})
    cursor.close()
    table = People(results)
    table.border = True
    return render_template('people.html', table=table)


##################################################################################
# add new people
##################################################################################
@app.route('/add_people', methods=['POST', 'GET'])
def add_people():
    if request.method == 'GET':
        return render_template("add_people.html")

    POST_PNAME = request.form['pname']
    POST_PLABEL = request.form['plabel']
    POST_PDESCRIPTION = request.form['pdescription']
    if not POST_PNAME:
        flash('name should not be null.')
        return redirect(url_for('add_people'))

    # create new record in db
    cursor = g.conn.execute("SELECT MAX(pid) FROM People;")
    curpid = cursor.next()[0] + 1
    cursor.close()
    try:
        # if violate ICs, redirect to another add payment/deposit option page

        g.conn.execute("INSERT INTO People(pid, pname, plabel, pdescription, uid) VALUES "
                       "(%s,  %s, %s, %s, %s);", (curpid, POST_PNAME, POST_PLABEL, POST_PDESCRIPTION, session['uid']))
    except:
        flash('People (Payer/Payee) cannot be created.')
        return redirect(url_for('add_people'))
    flash('People (Payer/Payee) created.')
    return redirect(url_for('people'))


##################################################################################
# edit people record
##################################################################################
@app.route('/edit_people/<int:pid>', methods=['GET', 'POST'])
def edit_people(pid):
    if request.method == 'GET':
        cursor = g.conn.execute("SELECT * FROM People WHERE pid = %s", (pid,))
        record = cursor.next()
        cursor.close()
        return render_template("edit_people.html", pid=pid, pname=record['pname'],
                               plabel=record['plabel'], pdescription=record['pdescription'])

    POST_PNAME = request.form['pname'].rstrip()
    POST_PLABEL = request.form['plabel'].rstrip()
    POST_PDESCRIPTION = request.form['pdescription'].rstrip()
    if not POST_PNAME:
        flash('name should not be null.')
        return redirect('/edit_people/{pid}'.format(pid=pid))

    try:
        g.conn.execute("UPDATE People SET pname=%s, plabel=%s, pdescription=%s "
                       "WHERE pid=%s;", (POST_PNAME, POST_PLABEL, POST_PDESCRIPTION, pid))
    except:
        flash('People (Payer/Payee) cannot be updated!')
        return redirect(url_for('paydeposit'))
    flash('People (Payer/Payee) updated successfully!')
    return redirect(url_for('people'))


##################################################################################
# delete people record
##################################################################################
@app.route('/delete_people/<int:pid>', methods=['GET', 'POST'])
def delete_people(pid):
    if request.method == 'GET':
        return render_template("delete_people.html", pid=pid)

    # delete the item from the database
    try:
        g.conn.execute("DELETE FROM People WHERE pid = %s;", (pid,))
        flash('People (Payer/Payee) deleted successfully!')
    except:
        flash('People (Payer/Payee) cannot be deleted!')
        return redirect(url_for("people"))
    return redirect(url_for("people"))

if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using

        python server.py

    Show the help text using

        python server.py --help

    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

  app.secret_key = 'supersupersupersecretkey'
  run()
