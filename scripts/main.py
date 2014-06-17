#!/usr/bin/python
import smtplib
import configReader

from email.mime.text import MIMEText

def main():
	cf = configReader.ConfigReader("config.txt")
	emails = cf.getEmails()
	sendEmail(emails, "output.txt")
	print "hello"

def getFileContent(name):
	"""Returns the content of the file with given name"""
	fp = open(name, 'r')
	content = MIMEText(fp.read())
	fp.close()
	return content

def sendEmail(addrs, fileName):
	"""Sends an email to each of the addresses specified by addr with
	the content of the file with fileName."""
	msg = getFileContent(fileName)
	msg['Subject'] = "The content of  2 %s" % fileName
	msg['From'] = "ela@lshift.net"
	msg['To'] = ', '.join(addrs)
	s = smtplib.SMTP('localhost')
	s.sendmail("ela@lshift.net", addrs, msg.as_string())
	s.quit()

if __name__ == "__main__":
	main()