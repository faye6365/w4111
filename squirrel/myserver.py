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
from datetime import datetime
from flask import Flask, request, render_template, g, redirect, Response, session, flash, url_for
from flask_table import Table, Col, LinkCol

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

DB_USER = "cy2472"
DB_PASSWORD = "g7cu7643"

DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/w4111"


months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

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
    print ("uh oh, problem connecting to database")
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
# cache variable to store the view tracking account time
##################################################################################
CURRENT_MONTH = '{year}-{month}'.format(year=datetime.now().year, month=datetime.now().month)
CACHE = {'time': CURRENT_MONTH}

##################################################################################
# index page
##################################################################################
@app.route('/')
def index():
    if 'uid' in session:
        uid = session['uid']

        # retrieve the name of the user for greeting message
        
        #storing sql query as a string variable protexts against sql injections (I think)
        #qname = "SELECT name FROM Users WHERE uid = %s;"
        #cursor = g.conn.execute(qname, (uid,))
        cursor = g.conn.execute("SELECT name FROM Users "
                               "WHERE uid = %s", (uid,))
        name = cursor.next()[0]
        cursor.close()

        cursor = g.conn.execute("SELECT * FROM Tracking_Accounts WHERE uid = %s ORDER BY aid;", (session['uid'],))
        results = []
        for result in cursor:
            summaryStats = superSum(result['aid'], 0000, 00, 1)
            netExchange = summaryStats.split("Net exchange: ",1)[1]
            results.append({'aid': result['aid'],
                            'aname': result['aname'],
                            'adescription': result['adescription'],
                            'aNet': netExchange})
        cursor.close()
        table = TrackingAccountResults(results)
        table.border = True

        return render_template('dashboard.html', table=table, name=name)
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
        #qNewUser = "INSERT INTO Users(uid, username, name, password) VALUES (%s, %s, %s, %s);"
        #g.conn.execute(qNewUser, (curuid, POST_USERNAME, POST_NAME, POST_PASSWORD))
        g.conn.execute("INSERT INTO Users(uid, username, name, password) VALUES"
                        "(%s, %s, %s, %s);", (curuid, POST_USERNAME, POST_NAME, POST_PASSWORD))
    except:
        flash('User cannot be created.')
        return redirect(url_for('signup'))
    flash('User created.')
    return redirect(url_for('index'))


##################################################################################
# Use Flask_table module to generate html table for Tracking Account
# (third-party library)
##################################################################################
class TrackingAccountResults(Table):
    aid = Col('Id', show=False)
    aname = Col('Name')
    adescription = Col('Description')
    aNet = Col('Net Exchange')
    # Called edit_trackingaccount() when the link is clicked.
    edit = LinkCol('Edit', 'edit_trackingaccount', url_kwargs=dict(aid='aid'))
    # Called delete_trackingaccount() when the link is clicked.
    delete = LinkCol('Delete', 'delete_trackingaccount', url_kwargs=dict(aid='aid'))
    view = LinkCol('View', 'view_trackingaccount', url_kwargs=dict(aid='aid'), url_kwargs_extra=dict(time=CURRENT_MONTH))


##################################################################################
# Use Flask_table module to generate html table for Trades (Expenses/Incomes)
# (third-party library)
##################################################################################
class TradeResults(Table):
    aid = Col('Aid', show = False)
    tid = Col('Id', show=False)
    tdate = Col('Date')
    tperson = Col('From/To Whom')
    tpayment = Col('Payment/Deposit Options')
    ttype = Col('Type')
    tlabel = Col('Label')
    tamount = Col('Amount')
    tdescription = Col('Description')

    # # Called edit_trade() when the link is clicked.
    edit = LinkCol('Edit', 'edit_trade', url_kwargs=dict(aid='aid', tid='tid', ttype='ttype'))
    # Called delete_trade() when the link is clicked.
    delete = LinkCol('Delete', 'delete_trade', url_kwargs=dict(aid='aid', tid='tid', ttype='ttype'))

##################################################################################
# Attempt to make a method/function for producing transaction tables. That way we can
# simplify the view_tracking account route
##################################################################################
def transactionTable(aid, year, month, monthOrAll):
    if monthOrAll == 0:
        results = []
        cursor = g.conn.execute("WITH transactions as (SELECT tid, tdate, tdescription, -1*tamount AS tamount, expense_label, oid, pid, 1 AS isexpense "
                                "FROM expenses WHERE aid = %s AND "
                                "tdate >= DATE \'%s-%s-1\' AND "
                                "tdate < DATE \'%s-%s-1\'  + INTERVAL \'1 month\' "
                                "UNION "
                                "SELECT tid, tdate, tdescription, tamount, income_label, oid, pid, 0 AS isexpense "
                                "FROM incomes WHERE aid = %s AND "
                                "tdate >= DATE \'%s-%s-1\' AND "
                                "tdate < DATE \'%s-%s-1\'  + INTERVAL \'1 month\') "
                                "SELECT * FROM transactions T "
                                "LEFT OUTER JOIN Payment_Deposit_Options PDO ON T.oid = PDO.oid "
                                "LEFT OUTER JOIN People PPL ON T.pid = PPL.pid "                                
                                "ORDER BY T.tdate asc;",
                                (aid, year, month, year, month, aid, year, month, year, month))
        for result in cursor:
            results.append({'aid': aid,
                            'tid': result['tid'],
                            'tdate': result['tdate'],
                            'tdescription': result['tdescription'],
                            'tamount': result['tamount'],
                            'tlabel': result['expense_label'],
                            'tperson': result['pname'],
                            'tpayment': result['oname'],
                            'ttype': 'Expense' if result['isexpense'] else 'Income'})
        cursor.close()
        table = TradeResults(results)
        table.border = True
        if not results:
            table = "No transactions for this period"
        return table
    elif monthOrAll == 1:
        results = []
        cursor = g.conn.execute("WITH transactions as (SELECT tid, tdate, tdescription, -1*tamount AS tamount, expense_label, oid, pid, 1 AS isexpense "
                                "FROM expenses WHERE aid = %s "
                                "UNION "
                                "SELECT tid, tdate, tdescription, tamount, income_label, oid, pid, 0 AS isexpense "
                                "FROM incomes WHERE aid = %s) "
                                "SELECT * FROM transactions T "
                                "LEFT OUTER JOIN Payment_Deposit_Options PDO ON T.oid = PDO.oid "
                                "LEFT OUTER JOIN People PPL ON T.pid = PPL.pid "
                                "ORDER BY T.tdate asc;",
                                (aid, aid))
        for result in cursor:
           results.append({ 'aid': aid,
                            'tid': result['tid'],
                            'tdate': result['tdate'],
                            'tdescription': result['tdescription'],
                            'tamount': result['tamount'],
                            'tlabel': result['expense_label'],
                            'tperson': result['pname'],
                            'tpayment': result['oname'],
                            'ttype': 'Expense' if result['isexpense'] else 'Income'})
        cursor.close()
        table = TradeResults(results)
        table.border = True
        if not results:
            table = "No transactions for this period"
        return table
    table = "Something went wrong. Try submitting a time period, again."
    return table

##################################################################################
# Sum incomes, expenses or net change
##################################################################################
def superSum(aid, year, month, monthOrAll):
    income = []
    expense = []
    if monthOrAll == 0:
        cursor = g.conn.execute("SELECT sum(-1*tamount) as sum FROM expenses where aid = %s AND "
                                "tdate >= DATE \'%s-%s-1\' AND "
                                "tdate < DATE \'%s-%s-1\'  + INTERVAL \'1 month\';", (aid, year, month, year, month))
        for result in cursor:
            expense.append({'sum': result['sum']})
        cursor.close()
        cursor = g.conn.execute("SELECT sum(tamount) as sum FROM incomes where aid = %s AND "
                                "tdate >= DATE \'%s-%s-1\' AND "
                                "tdate < DATE \'%s-%s-1\'  + INTERVAL \'1 month\';", (aid, year, month, year, month))
        for result in cursor:
            income.append({'sum': result['sum']})
        cursor.close()
        incomeSum = income[0].get('sum')
        expenseSum = expense[0].get('sum')
        if incomeSum is None:
            incomeSum = 0000.00
        if expenseSum is None:
            expenseSum = 0000.00
        netSum = float(expenseSum) + float(incomeSum)

        return "Total incomes: " + str(incomeSum) + " | Total expenses: " + str(expenseSum) + " | Net exchange: " + str(netSum) 
    elif monthOrAll == 1:
        cursor = g.conn.execute("SELECT sum(-1*tamount) as sum FROM expenses where aid = %s", aid)
        for result in cursor:
            expense.append({'sum': result['sum']})
        cursor.close()
        income = []
        cursor = g.conn.execute("SELECT sum(tamount) FROM incomes where aid = %s", aid)
        for result in cursor:
            income.append({'sum': result['sum']})
        incomeSum = income[0].get('sum')
        expenseSum = expense[0].get('sum')
        if incomeSum is None:
            incomeSum = 0000.00
        if expenseSum is None:
            expenseSum = 0000.00
        netSum = float(incomeSum) + float(expenseSum)
        return "Total incomes: " + str(incomeSum) + " | Total expenses: " + str(expenseSum) + " | Net exchange: " + str(netSum) 
    return "Could not calculate summary statistics"

##################################################################################
# view trades/statement in the tracking account
##################################################################################
@app.route('/view_trackingaccount/<int:aid>/<string:time>', methods=['GET', 'POST'])
def view_trackingaccount(aid, time):
    if request.method == 'GET':
        if "byAll" == time:
            table = transactionTable(aid, 0000, 00, 1)  # 1 tells the function to execute for all transactions
            summaryStats = superSum(aid, 0000, 00, 1)
            return render_template("view_trackingaccount.html", aid=aid, table=table, byMonth="", byAll="checked",
                                   summaryStats=summaryStats, time=time)
        else:
            try:
                POST_YEARMONTH = time
                POST_YEAR, POST_MONTH = map(int, POST_YEARMONTH.split('-'))
                table = transactionTable(aid, POST_YEAR, POST_MONTH, 0) #0 tells the function to execute by month. As opposed to 1 telling to execute for all expenses
                summaryStats = superSum(aid, POST_YEAR, POST_MONTH, 0)
                budgetButton = "Click here to set budget for " + months[POST_MONTH-1] + ", " + str(POST_YEAR)
                # Check if there is a statement in db, if so retrieve the budget
                try:
                    cursor = g.conn.execute("SELECT sbudget FROM Statements "
                                            "WHERE aid = %s AND "
                                            "syear = %s AND "
                                            "smonth = %s;", (aid, POST_YEAR, POST_MONTH))
                    budget = cursor.next()[0]
                    budgetLeft = float(budget) + float(summaryStats.split("Net exchange: ",1)[1])
                    cursor.close()
                except:
                    return render_template("view_trackingaccount.html", aid=aid, table=table,
                                           dateSendBack=POST_YEARMONTH, byMonth = "checked", byAll = "",
                                           isbudget=0, budget = 0.0, summaryStats = summaryStats,
                                           budgetButton = budgetButton, time=time)

                return render_template("view_trackingaccount.html", aid=aid, table=table,
                                       dateSendBack=POST_YEARMONTH, byMonth = "checked", byAll = "",
                                       isbudget=1, budget=budget, summaryStats = summaryStats,
                                       budgetButton = budgetButton, budgetLeft = budgetLeft, time=time)
            except:
                return render_template("view_trackingaccount.html", aid = aid, byMonth = "checked", byAll = "",
                                       isbudget=0, budget=0.0, time=time)

    if "byMonth" == request.form['transactions']:
        CACHE['time'] = request.form['month']
        return redirect('/view_trackingaccount/{aid}/{time}'.format(aid=aid, time=CACHE['time']))
    else:
        CACHE['time'] = 'byAll'
        return redirect('/view_trackingaccount/{aid}/byAll'.format(aid=aid))

##################################################################################
# func to retrieve pre-set value lists for adding/editing an income/expense
##################################################################################
def retrieveTradePreset(aid, type='Expense'):

    people = [[None, 'None']] # User can add an expense without specifying the payer/payee
    options = [[None, 'None']] # User can add an expense without specifying the payment/deposit option
    labels = [None]
    uid = session['uid']

    # Retrieve all Payment_Deposit_Options of the user to make the selection list
    cursor = g.conn.execute("SELECT * FROM Payment_Deposit_Options WHERE uid = %s;", (uid,))
    for result in cursor:
        options.append([result['oid'],
                        "{oname} ({olabel}, {odescription})".format(oname=result['oname'], olabel=result['olabel'],
                                                                   odescription=result['odescription'])])
    cursor.close()

    # Retrieve all People of the user to make the selection list
    cursor = g.conn.execute("SELECT * FROM People WHERE uid = %s;", (uid,))
    for result in cursor:
        people.append([result['pid'],
                        "{pname} ({plabel}, {pdescription})".format(pname=result['pname'], plabel=result['plabel'],
                                                                   pdescription=result['pdescription'])])
    cursor.close()

    # Retrieve all Expense/Income labels of the account to make the data list
    if type == 'Expense':
        cursor = g.conn.execute("SELECT DISTINCT expense_label FROM Expenses WHERE aid = %s;", (aid,))
        for result in cursor:
            labels.append(result['expense_label'])
        cursor.close()
    else:
        cursor = g.conn.execute("SELECT DISTINCT income_label FROM Incomes WHERE aid = %s;", (aid,))
        for result in cursor:
            labels.append(result['income_label'])
        cursor.close()

    return dict(people=people, options=options, labels=labels)

##################################################################################
# add an expense
##################################################################################
@app.route('/add_expense/<int:aid>', methods=['POST', 'GET'])
def add_expense(aid):

    # Get the selection list and data list from database
    presets = retrieveTradePreset(aid, 'Expense')
    people = presets['people']
    options = presets['options']
    labels = presets['labels']

    if request.method == 'GET':
        return render_template("add_expense.html", aid=aid, people=people, options=options, labels=labels,
                               cacheTime=CACHE['time'], today=datetime.today().date())

    POST_AID = aid
    POST_PID = request.form['pid']
    POST_OID = request.form['oid']
    POST_TDATE = request.form['tdate']
    POST_TLABEL = request.form['tlabel']
    POST_TDESCRIPTION = request.form['tdescription']
    POST_TAMOUNT = request.form['tamount']

    # create new record in db
    cursor = g.conn.execute("SELECT MAX(tid) FROM Expenses;")
    exptid = cursor.next()[0] + 1
    cursor.close()
    cursor = g.conn.execute("SELECT MAX(tid) FROM Incomes;")
    inctid = cursor.next()[0] + 1
    cursor.close()
    curtid = max(exptid, inctid)
    try:
        # if violate ICs, redirect to another add expense page
        g.conn.execute("INSERT INTO Expenses(tid, tdate, tdescription, tamount, aid, pid, oid, expense_label) VALUES "
                       "(%s,  DATE %s, %s, %s, %s, %s, %s, %s);", (curtid, POST_TDATE, POST_TDESCRIPTION,
                                                                   POST_TAMOUNT, POST_AID, POST_PID, POST_OID,
                                                                   POST_TLABEL))
    except:
        flash('Expense cannot be created.')
        return redirect('/add_expense/{aid}'.format(aid=aid))
    flash('Expense created.')
    return redirect('/view_trackingaccount/{aid}/{time}'.format(aid=aid, time=CACHE['time']))

##################################################################################
# add an income
##################################################################################
@app.route('/add_income/<int:aid>', methods=['POST', 'GET'])
def add_income(aid):

    # Get the selection list and data list from database
    presets = retrieveTradePreset(aid, 'Income')
    people = presets['people']
    options = presets['options']
    labels = presets['labels']

    if request.method == 'GET':
        return render_template("add_income.html", aid=aid, people=people, options=options, labels=labels,
                               cacheTime=CACHE['time'], today=datetime.today().date())

    POST_AID = aid
    POST_PID = request.form['pid']
    POST_OID = request.form['oid']
    POST_TDATE = request.form['tdate']
    POST_TLABEL = request.form['tlabel']
    POST_TDESCRIPTION = request.form['tdescription']
    POST_TAMOUNT = request.form['tamount']

    # create new record in db
    cursor = g.conn.execute("SELECT MAX(tid) FROM Expenses;")
    exptid = cursor.next()[0] + 1
    cursor.close()
    cursor = g.conn.execute("SELECT MAX(tid) FROM Incomes;")
    inctid = cursor.next()[0] + 1
    cursor.close()
    curtid = max(exptid, inctid)
    try:
        # if violate ICs, redirect to another add expense page
        g.conn.execute("INSERT INTO Incomes(tid, tdate, tdescription, tamount, aid, pid, oid, income_label) VALUES "
                       "(%s,  DATE %s, %s, %s, %s, %s, %s, %s);", (curtid, POST_TDATE, POST_TDESCRIPTION,
                                                                   POST_TAMOUNT, POST_AID, POST_PID, POST_OID,
                                                                   POST_TLABEL))
    except:
        flash('Income cannot be created.')
        return redirect('/add_income/{aid}'.format(aid=aid))
    flash('Income created.')
    return redirect('/view_trackingaccount/{aid}/{time}'.format(aid=aid, time=CACHE['time']))

##################################################################################
# edit a trade
##################################################################################
@app.route('/edit_trade/<int:aid>_<int:tid>_<string:ttype>', methods=['GET', 'POST'])
def edit_trade(aid, tid, ttype):
    # Get the selection list and data list from database
    presets = retrieveTradePreset(aid, ttype)
    people = presets['people']
    options = presets['options']
    labels = presets['labels']

    if request.method == 'GET':
        if ttype == 'Expense':
            cursor = g.conn.execute("SELECT * FROM Expenses WHERE tid = %s;", (tid,))
            record = cursor.next()
            tlabel = record['expense_label']
            cursor.close()
        else:
            cursor = g.conn.execute("SELECT * FROM Incomes WHERE tid = %s;", (tid,))
            record = cursor.next()
            tlabel = record['income_label']
            cursor.close()
        return render_template("edit_trade.html", aid=aid, tid=tid, ttype=ttype, prepid=record['pid'],
                               preoid=record['oid'], pretdate=record['tdate'], pretlabel=tlabel,
                               pretdescription=record['tdescription'], pretamount=record['tamount'],
                               people=people, options=options, labels=labels,
                               cacheTime=CACHE['time'], today=datetime.today().date())

    POST_AID = aid
    POST_PID = request.form['pid']
    POST_OID = request.form['oid']
    POST_TDATE = request.form['tdate']
    POST_TLABEL = request.form['tlabel'].rstrip()
    POST_TDESCRIPTION = request.form['tdescription'].rstrip()
    POST_TAMOUNT = request.form['tamount']

    try:
        if ttype == 'Expense':
            g.conn.execute("UPDATE Expenses SET tdate = DATE %s, tdescription = %s, tamount = %s, aid = %s, pid = %s, "
                           "oid = %s, expense_label = %s "
                           "WHERE tid = %s;", (POST_TDATE, POST_TDESCRIPTION, POST_TAMOUNT, POST_AID, POST_PID,
                                               POST_OID, POST_TLABEL, tid))
        else:
            g.conn.execute("UPDATE Incomes SET tdate = DATE %s, tdescription = %s, tamount = %s, aid = %s, pid = %s, "
                           "oid = %s, income_label = %s "
                           "WHERE tid = %s;", (POST_TDATE, POST_TDESCRIPTION, POST_TAMOUNT, POST_AID, POST_PID,
                                               POST_OID, POST_TLABEL, tid))
    except:
        flash('Trade cannot be updated!')
        return redirect('/edit_trade/{aid}_{tid}_{ttype}'.format(aid=aid, tid=tid, ttype=ttype))
    flash('Trade updated successfully!')

    POST_TYEAR, POST_TMONTH = map(int, POST_TDATE.split('-'))[:-1]
    return redirect('/view_trackingaccount/{aid}/{time}'.format(aid=aid, time='{}-{}'.format(POST_TYEAR, POST_TMONTH)))

##################################################################################
# delete a trade
##################################################################################
@app.route('/delete_trade/<int:aid>_<int:tid>_<string:ttype>', methods=['GET', 'POST'])
def delete_trade(aid, tid, ttype):
    if request.method == 'GET':
        return render_template("delete_trade.html", aid=aid, tid=tid, ttype=ttype, cacheTime=CACHE['time'])

    # delete the item from the database
    try:
        if ttype == 'Expense':
            g.conn.execute("DELETE FROM Expenses WHERE tid = %s;", (tid,))
        else:
            g.conn.execute("DELETE FROM Incomes WHERE tid = %s;", (tid,))
        flash('Trade deleted successfully!')
    except:
        flash('Trade cannot be deleted!')
        return redirect('/view_trackingaccount/{aid}/{time}'.format(aid=aid, time=CACHE['time']))
    return redirect('/view_trackingaccount/{aid}/{time}'.format(aid=aid, time=CACHE['time']))

##################################################################################
# add new tracking account
##################################################################################
@app.route('/add_trackingaccount', methods=['POST', 'GET'])
def add_trackingaccount():
    if request.method == 'GET':
        return render_template("add_trackingaccount.html")

    POST_ANAME = request.form['aname']
    POST_ADESCRIPTION = request.form['adescription']
    if not POST_ANAME:
        flash('name should not be null.')
        return redirect(url_for('add_trackingaccount'))

    # create new record in db
    cursor = g.conn.execute("SELECT MAX(aid) FROM Tracking_Accounts;")
    curaid = cursor.next()[0] + 1
    cursor.close()
    try:
        # if violate ICs, redirect to another add tracking account page
        qInsertTAcc = "INSERT INTO Tracking_Accounts(aid, aname, adescription, uid) VALUES (%s,  %s, %s, %s);"
        g.conn.execute(qInsertTAcc, (curaid, POST_ANAME, POST_ADESCRIPTION, session['uid']))
        #g.conn.execute("INSERT INTO Tracking_Accounts(aid, aname, adescription, uid) VALUES "
        #               "(%s,  %s, %s, %s);", (curaid, POST_ANAME, POST_ADESCRIPTION, session['uid']))
    except:
        flash('Tracking account cannot be created.')
        return redirect(url_for('add_trackingaccount'))
    flash('Tracking account created.')
    return redirect('/')


##################################################################################
# edit a tracking account
##################################################################################
@app.route('/edit_trackingaccount/<int:aid>', methods=['GET', 'POST'])
def edit_trackingaccount(aid):
    if request.method == 'GET':
        qTAccInfo = "SELECT * FROM Tracking_Accounts WHERE aid = %s;"
        cursor = g.conn.execute(qTAccInfo, (aid,))
        #cursor = g.conn.execute("SELECT * FROM Tracking_Accounts WHERE aid = %s;", (aid,))
        record = cursor.next()
        cursor.close()
        return render_template("edit_trackingaccount.html", aid=aid, aname=record['aname'],
                               adescription=record['adescription'])

    POST_ANAME = request.form['aname'].rstrip()
    POST_ADESCRIPTION = request.form['adescription'].rstrip()
    if not POST_ANAME:
        flash('name should not be null.')
        return redirect('/edit_trackingaccount/{aid}'.format(aid=aid))

    try:
        qUpdateTAcc = "UPDATE Tracking_Accounts SET aname=%s, adescription=%s WHERE aid=%s;"
        #g.conn.execute("UPDATE Tracking_Accounts SET aname=%s, adescription=%s "
        #               "WHERE aid=%s;", (POST_ANAME, POST_ADESCRIPTION, aid))
        g.conn.execute(qUpdateTAcc, (POST_ANAME, POST_ADESCRIPTION, aid))
    except:
        flash('Tracking account cannot be updated!')
        return redirect(url_for('paydeposit'))
    flash('Tracking account updated successfully!')
    return redirect('/')


##################################################################################
# delete a tracking account
##################################################################################
@app.route('/delete_trackingaccount/<int:aid>', methods=['GET', 'POST'])
def delete_trackingaccount(aid):
    if request.method == 'GET':
        return render_template("delete_trackingaccount.html", aid=aid)

    POST_PASSWORD = str(request.form['password'])
    try:
        qUserCheck = "Select * FROM Users Where uid = %s AND password = %s;"
        cursor = g.conn.execute(qUserCheck, (session['uid'], POST_PASSWORD))
        #cursor = g.conn.execute("SELECT * FROM Users "
        #                        "WHERE uid = %s AND "
        #                        "password = %s;", (session['uid'], POST_PASSWORD))
        cursor.close()
    except:
        flash('password not matched! not authorized to delete the tracking_account')
        return redirect("/")

    # delete the item from the database
    try:
        qDelTAcc = "DELETE FROM Tracking_Accounts WHERE aid = %s;"
        g.conn.execute("DELETE FROM Tracking_Accounts WHERE aid = %s;", (aid,))
        flash('Tracking account deleted successfully!')
    except:
        flash('Tracking account cannot be deleted!')
        return redirect("/")
    return redirect("/")


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
    cursor = g.conn.execute("SELECT * FROM Payment_Deposit_Options WHERE uid = %s ORDER BY oid;", (session['uid'],))
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
        cursor = g.conn.execute("SELECT * FROM Payment_Deposit_Options WHERE oid = %s;", (oid,))
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
class PeopleResults(Table):
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
    cursor = g.conn.execute("SELECT * FROM People WHERE uid = %s ORDER BY pid;", (session['uid'],))
    results = []
    for result in cursor:
        results.append({'pid': result['pid'],
                        'pname': result['pname'],
                        'plabel': result['plabel'],
                        'pdescription': result['pdescription']})
    cursor.close()
    table = PeopleResults(results)
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
        # if violate ICs, redirect to another add people page

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
        cursor = g.conn.execute("SELECT * FROM People WHERE pid = %s;", (pid,))
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


##################################################################################
# set a budget (if the statement record exists update it else create one)
##################################################################################
@app.route('/setbudget/<int:aid>/<string:dateSendBack>/<int:isbudget>', methods=['GET', 'POST'])
def setbudget(aid, dateSendBack, isbudget):

    POST_YEAR, POST_MONTH = map(int, dateSendBack.split('-'))

    if request.method == 'GET':
        prebudget = None
        if isbudget:
            cursor = g.conn.execute("SELECT sbudget FROM Statements "
                                    "WHERE aid = %s AND "
                                    "syear = %s AND "
                                    "smonth = %s;", (aid, POST_YEAR, POST_MONTH))
            prebudget = cursor.next()[0]
            cursor.close()

        return render_template("setbudget.html", aid=aid, dateSendBack=dateSendBack, isbudget=isbudget, prebudget=prebudget)

    POST_BUDGET = request.form['sbudget']
    try:
        # if statement(budget) exists, performing an update else performing an insertion.
        if isbudget:
            g.conn.execute("UPDATE Statements SET sbudget = %s "
                           "WHERE aid = %s AND "
                           "syear = %s AND "
                           "smonth = %s;", (POST_BUDGET, aid, POST_YEAR, POST_MONTH))
        else:
            g.conn.execute("INSERT INTO Statements(aid, syear, smonth, sbudget) VALUES "
                           "(%s,  %s, %s, %s);",
                           (aid, POST_YEAR, POST_MONTH, POST_BUDGET))
    except:
        # if violate ICs, redirect to another set budget page

        flash('Budget (Statement) cannot be set!')
        return redirect('/setbudget/{aid}/{dateSendBack}/{isbudget}'.format(aid=aid, dateSendBack=dateSendBack, isbudget=isbudget))

    flash('Budget (Statement) is set successfully!')

    return redirect('/view_trackingaccount/{aid}/{time}'.format(aid=aid, time=CACHE['time']))

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
    print ("running on %s:%d" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

  app.secret_key = 'supersupersupersecretkey'
  run()
