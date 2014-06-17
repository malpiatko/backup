#!/usr/bin/python
import smtplib

from email.mime.text import MIMEText

def main():
	msg = getMessage("sampledirSmall/output.txt")
	print "hello"

def getMessage(name):
	fp = open(name, 'r');
	msg = MIMEText(fp.read())
	fp = fp.close()
	return msg

if __name__ == "__main__":
	main()