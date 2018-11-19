#!/usr/bin/python
from twilio.rest import Client
from email.mime.text import MIMEText
import imaplib
import time
import smtplib
import datetime
import requests
from slackclient import SlackClient

class SlackBot:
	def __init__(self):
		self.slack_oauth_token = "<slack_oauth_token>"
		self.slack_bot_token = "<slack_bot_token>"
		self.slack_client = SlackClient(self.slack_bot_token)
	
	def sendAlert(self, alert):
		self.slack_client.api_call(
			"chat.postMessage",
			channel="alerts",
			text="@all " + alert
		)

class RequestBot:
	def __init__(self):
		self.phoneNumber = "<twilio_phone_number>"
		self.account_sid = open("account_sid.txt", "r").read()
		self.auth_token = open("auth_token.txt", "r").read()
		self.client = Client(self.account_sid, self.auth_token)

	def process(self, info):
		message = "DONE_REPORT"
		call_to = info["Asset phone"]
		execution = self.client.studio \
			.flows('<twilio_studio_flow_sid>') \
	 		.executions \
			.create(to=call_to, from_=self.phoneNumber, parameters={"message": info["Alert message"], "passcode": info["Confirmation-Pin"], "assetname": info["Asset"].replace("-", " ")})
		
		exec_sid = execution.sid
		flow_sid = execution.flow_sid

		counter = 0
		sleepInterval = 2
		
		report = True
		
		while counter < 250:
			e = self.client.studio \
				.flows(flow_sid) \
				.executions(exec_sid) \
				.fetch()
			if e.status == "ended":
				break
			counter += sleepInterval
			time.sleep(sleepInterval)
		
		if counter >= 250 or e.status != "ended":
			try:
				self.client.studio.flows(flow_sid) \
					.executions(exec_sid) \
					.delete()
			except:
				print("Could not stop execution: " + exec_sid)
			report = True
		else:
			steps = self.client.studio.flows(flow_sid) \
					.executions(exec_sid) \
					.steps \
					.list()
			for s in steps:
				if "report" in s.name or "report" in s.transitioned_from or "report" in s.transitioned_to:
					report = True
					break
				elif "discard" in s.name or "discard" in s.transitioned_from or "discard" in s.transitioned_to:
					report = False
					break
		
		if report == True:
			message = "DONE_REPORT"
		else:
			message = "DONE_DO_NOT_REPORT"
		
		return message


class Logger:
	def __init__(self):
		#open("log.backup", "w").write(open("log.csv", "r").read())
		#open("log.csv", "w").write("DATE,STATE,ALERT LEVEL,ALERT MSG,ASSET,ASSET OWNER,ASSET EMAIL,ASSET PHONE,CALLBACK,MESSAGE\n")
		pass

	def log(self, info):
		st = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
		with open("log.csv", "a") as f:
			f.write('"' + st + '","' + info["State"] + '","' + info["Alert level"] + '","' + info["Alert message"] + '","' + info["Asset"] + '","' + info["Asset owner"] + '","' + info["Asset email"] + '","' + info["Asset phone"] + '","' + info["Callback"] + '","' + info["Message"] + "\"\n")



def main():
	logger = Logger()
	requestBot = RequestBot()
	slackBot = SlackBot()

	mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
	#----------------------
	mail.login('<email>', '<email_pass>')
	#----------------------


	#----------------------
	sleepTime = 1
	#----------------------

	def sendMail(info):
		smtp_ssl_host = 'smtp.gmail.com'  # smtp.mail.yahoo.com
		smtp_ssl_port = 465
		username = '<email>'
		password = '<email_pass>'
		sender = '<email>'
		targets = [info["Callback"]]

		msg = MIMEText("NEW TICKET:\n" + info["originalBody"])
		msg['Subject'] = "[ALERT]" + info["Subject"]
		msg['From'] = sender
		msg['To'] = ', '.join(targets)

		server = smtplib.SMTP_SSL(smtp_ssl_host, smtp_ssl_port)
		server.login(username, password)
		server.sendmail(sender, targets, msg.as_string())
		server.quit()

	while True:
		try:
			mail.list()
			mail.select()
			#----------------------
			typ,data=mail.search(None,'ALL', '(UNSEEN)')
			#typ, data = mail.search(None, 'ALL')
			#----------------------
		except:
			data = []
			print("Could not read mail")
			pass
		if len(data) > 0 and data[0]:
			if len(data) == 1:
				data = data[0].split(" ")
			for d in data:
				try:
					result, data = mail.fetch(d, "(RFC822)")
				except:
					print("Except reading data: " + d)
					continue
				subj = data[0][1].split("Subject: ")[1].split("\r\n")[0]
				print("Found new mail: " + subj)
				body_unfiltered = data[0][1].split("Content-Type: text/plain; charset=\"UTF-8\"")[1].split("Content-Type: text/html; charset=\"UTF-8\"")[0].split("\n")[:-1]
				body = []
				for b in body_unfiltered:
					if b != '\r' and not "--" in b:
						body.append(b.strip('\r').lstrip())
				info = {}
				for l in body:
					info[l.split(": ")[0]] = l.split(": ")[1]

				info["originalBody"] = ''.join([a + '\n' for a in body])
				info["Confirmation-Pin"] = "1234"
				info["Subject"] = subj
				info["Callback"] = "<your_email>"
				info["Message"] = "PENDING"
				info["State"] = "RECEIVED"

				logger.log(info)
				message = requestBot.process(info)
				info["Message"] = message
				info["State"] = "PROCESSED"
				
				if info["Message"] == "DONE_REPORT":
					sendMail(info)
					slackBot.sendAlert("New alert added: " + info["Subject"])
					print("Sent mail for: " + info["Subject"])

				logger.log(info)


		time.sleep(sleepTime)
	

if __name__ == "__main__":
	main()

