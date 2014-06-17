#!/usr/bin/python
import smtplib

from email.mime.text import MIMEText

def main():
	sendEmail("ela@lshift.net", "sampledirSmall/output.txt")
	print "hello"

def getFileContent(name):
	fp = open(name, 'r')
	content = MIMEText(fp.read())
	fp = fp.close()
	return content

def sendEmail(address, fileName):
	msg = getFileContent(fileName)
	msg['Subject'] = "The content of %s" % fileName
	msg['From'] = "ela@lshift.net"
	msg['To'] = address
	s = smtplib.SMTP('localhost')
	s.sendmail("ela@lshift.net", [address], msg.as_string())
	s.quit()

if __name__ == "__main__":
	main()