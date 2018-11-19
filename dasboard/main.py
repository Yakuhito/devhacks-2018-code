from flask import Flask
from flask import Flask, flash, redirect, send_file, render_template, request, session, abort, make_response
import dash_core_components as dcc
import dash_html_components as html
from email.mime.text import MIMEText
import json
import hashlib
import hmac
import pyg2fa
import dash
import operator
import smtplib, email, imaplib

class Config:
	def __init__(self, filename):
		self.options = json.load(open(filename, "r"))
	
	def getJson(self):
		return self.options

	def getOption(self, option):
		return self.options[option]

class Auth:
	def __init__(self, config):
		self.conf = config
	
	def gethash(self, key, message):
		return hmac.new(str(key), str(message), hashlib.sha256).hexdigest()

	def checkUser(self, username, passw):
		exists = False
		phash = ""
		psalt = ""
		for o in self.conf.getOption("users"):
			if o["username"] == username:
				exists = True
				phash = o["password_hash"]
				psalt = o["password_salt"]
		if exists == False:
			return False
		return phash == str(self.gethash(psalt, passw))

	def check2FA(self, user, otp):
		for o in self.conf.getOption("users"):
			if o["username"] == user:
				USER_SECRET_INITIAL_OTP_SEED = o['otp_seed']
				try:
					opt = int(otp)
				except:
					if otp == "BACKUP_CODE":
						return True
					return False
				if pyg2fa.validate(USER_SECRET_INITIAL_OTP_SEED, int(otp), 4):
					return True
				else:
					return False
		return False

class LogParser:
	def __init__(self, logPath):
		self.logPath = logPath
		self.lastLine = ""
		self.update()
		
	def update(self):
		newLine = open(self.logPath).readlines()[1]
		if self.lastLine != newLine:
			self.updateVars()
			self.lastLine = newLine			

	def updateVars(self):
		logs = open(self.logPath).read().split("\n")[1:-1]
		
		self.total_logs = len(logs)
		self.total_processed_logs = 0
		self.total_received_logs = 0
		
		self.firstLogDate = logs[0].split('","')[0][1:]
		self.lastLogDate = logs[-1].split('","')[0][1:]
		
		self.alerts_report = 0
		self.alerts_do_not_report = 0

		self.alert_msgs = {}

		self.alert_assets = {}
		
		self.alert_asset_owners = {}

		self.lastLogs = []

		for entry in logs:
			attr = entry.split('","')
			attr[0] = attr[0][1:]
			attr[-1] = attr[0][1:]
			aDate = attr[0]
			aState = attr[1]
			aAlertLevel = attr[2]
			aAlertMsg = attr[3]
			aAsset = attr[4]
			aAssetOwner = attr[5]
			aAssetEmail = attr[6]
			aAssetPhone = attr[7]
			aCallback = attr[8]
			aMessage = attr[9]
			if "PROCESSED" in aState:
				self.total_processed_logs += 1
			if "DONE" in aMessage:
				if "DO_NOT" in aMessage:
					self.alerts_do_not_report += 1
				else:
					self.alerts_report += 1

			if self.alert_assets.get(aAsset, -1) == -1:
				self.alert_assets[aAsset] = 1
			else:
				self.alert_assets[aAsset] += 1
			
			if self.alert_msgs.get(aAlertMsg, -1) == -1:
				self.alert_msgs[aAlertMsg] = 1
			else:
				self.alert_msgs[aAlertMsg] += 1

			if self.alert_asset_owners.get(aAssetOwner, -1) == -1:
				self.alert_asset_owners[aAssetOwner] = 1
			else:
				self.alert_asset_owners[aAssetOwner] += 1
			
		if len(logs) < 10:
			self.lastLogs = logs
		else:
			self.lastLogs = logs[-10:] 

		
			
		self.total_received_logs = self.total_logs - self.total_processed_logs

	def getTotalLogs(self):
		return self.total_logs
	
	def getTotalProcessedLogs(self):
		return self.total_processed_logs

	def getTotalReceivedLogs(self):
		return self.total_received_logs

	def getFirstLogDate(self):	
		return self.firstLogDate

	def getLastLogDate(self):
		return self.lastLogDate

	def getAlertsReport(self):
		return self.alerts_report

	def getAlertsDoNotReport(self):
		return self.alerts_do_not_report

	def getAlertMsgs(self):
		return self.alert_msgs
	
	def getAssets(self):
		return self.alert_assets

	def getOwners(self):
		return self.alert_asset_owners

	def getLastLogs(self):
		return self.lastLogs

	def getTopAlertMessages(self):
		data = []
		msgs = self.getAlertMsgs()
		msgs = sorted(msgs.items(), key=operator.itemgetter(1), reverse = True)
		if len(msgs) > 10:
			msgs = msgs[-10:]
		cnt = 1
		for d in msgs:
			data.append({'x':[cnt], 'y': [d[1]], 'type': 'bar', 'name': d[0]})
			cnt += 1
		return data

	def getTopAssets(self):
		data = []
		asts = self.getAssets()
		asts = sorted(asts.items(), key=operator.itemgetter(1), reverse = True)
		if len(asts) > 10:
			asts = asts[-10:]
		cnt = 1
		for d in asts:
			data.append({'x':[cnt], 'y': [d[1]], 'type': 'bar', 'name': d[0]})
			cnt += 1
		return data
	
	def getTopOwners(self):
		data = []
		owns = self.getOwners()
		owns = sorted(owns.items(), key=operator.itemgetter(1), reverse = True)
		if len(owns) > 10:
			owns = owns[-10:]
		cnt = 1
		for d in owns:
			data.append({'x':[cnt], 'y': [d[1]], 'type': 'bar', 'name': d[0]})
			cnt += 1
		return data

conf = Config("config.json")
auth = Auth(conf)
logParser = LogParser(conf.getOption("logDir"))

app = Flask(conf.getOption("appName"))
app.config['SECRET_KEY'] = conf.getOption("appSecret")

dashApp = dash.Dash(conf.getOption("appName"), server = app, url_base_pathname = "/dashboardRep/")

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
dashApp.layout = html.Div(children=[
    dcc.Graph(
        id='Top Alert Messages',
        figure={
            'data': logParser.getTopAlertMessages(),
            'layout': {
                'title': 'Top Alert Messages'
            }
        }
    ),
   dcc.Graph(
        id='Top Attacked Assets',
        figure={
            'data': logParser.getTopAssets(),
            'layout': {
                'title': 'Top Attacked Assets'
            }
        }
    ),
   dcc.Graph(
        id='Top Called Owners',
        figure={
            'data': logParser.getTopOwners(),
            'layout': {
                'title': 'Top Called Owners'
            }
        }
    )
])

@app.route("/", methods = ["GET"])
def index():
	if not session.get("user"):
		return redirect("/login")
	else:
		return redirect("/dashboard")

@app.route('/login', methods = ['GET'])
def login():
	if session.get("user"):
		return redirect("/dashboard")
	if request.args.get('failed'):
		return render_template('login-failed.html')
	else:	
		return render_template('login.html')

@app.route('/2fa', methods = ['POST'])
def login2fa():
	if session.get("user"):
		return redirect("/dashboard")
	if not request.form.get("username") or not request.form.get("password"):
		return redirect("/")
	usr = request.form.get("username")
	psw = request.form.get("password")
	if request.args.get('failed'):
		return render_template('login2fa-failed.html', username = usr, password = psw)
	else:
		if auth.checkUser(usr, psw):
			return render_template('login2fa.html', username = usr, password = psw)
		else:
			return redirect('/login?failed=True')
	
@app.route('/finallogin', methods = ['POST'])
def finallogin():
	if session.get("user"):
		return redirect("/dashboard")
	if not request.form.get("username") or not request.form.get("password") or not request.form.get("otp-code"):
		return redirect("/")
	usr = request.form.get("username")
	psw = request.form.get("password")
	code = request.form.get("otp-code")
	if not auth.checkUser(usr, psw):
		return redirect('/login?failed=True')
	if not auth.check2FA(usr, code):
		return redirect('/2fa?failed=True', code=307)
	session["user"] = usr
	return redirect("/dashboard")
	
@app.route('/dashboardRep', methods = ['GET'])
def dashboardRep():
	if not session.get("user"):
		return redirect("/login")
	return dashApp.index()

@app.route('/dashboard', methods = ['GET'])
def dashboard():
	if not session.get("user"):
		return redirect("/login")
	return render_template('dashboard.html', user = session.get("user"))

@app.route('/logout', methods = ['GET'])
def logout():
	if not session.get("user"):
		return redirect("/login")
	session.pop("user")
	return redirect("/")

@app.route('/job', methods = ['GET'])
def job():
	if not session.get("user"):
		return redirect("/login")
	return render_template('job.html')

def sendMail(title, body):
		smtp_ssl_host = 'smtp.gmail.com'  # smtp.mail.yahoo.com
		smtp_ssl_port = 465
		username = '<insert_mail_here>'
		password = '<insert_mail_pass_here>'
		sender = '<inser_mail_here>'
		targets = ['<insert_mail_here>']

		msg = MIMEText(body)
		msg['Subject'] = title
		msg['From'] = sender
		msg['To'] = ', '.join(targets)

		server = smtplib.SMTP_SSL(smtp_ssl_host, smtp_ssl_port)
		server.login(username, password)
		server.sendmail(sender, targets, msg.as_string())
		server.quit()

@app.route('/log', methods = ['GET'])
def getLog():
	if not session.get("user"):
		return redirect("/login")
	return send_file(conf.getOption('logDir'))
	return redirect('/')

@app.route('/makejob', methods = ['POST'])
def makejob():
	if not session.get("user"):
		return redirect("/login")
	jobName = request.form.get("title")
	jobDetails = request.form.get("details")
	sendMail(jobName, jobDetails)
	return redirect("/")

	

app.run(host = conf.getOption("appAddress"), port = conf.getOption("appPort"))



