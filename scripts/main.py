#!/usr/bin/python
import smtplib
import configReader
import md5dir
import os
import sys

from email.mime.text import MIMEText

def main():
	# Read configuration file
	cf = configReader.ConfigReader("config.txt")
	currentDir = os.getcwd()

	# Find the changes since last update and save to output.txt
	outputFile = open('output.txt', 'w+')
	sys.stdout = outputFile
	changedFiles = md5dir.md5dir(currentDir, md5dir.master_list(currentDir), master=True)
	sys.stdout = sys.__stdout__
	outputFile.close()
	print "blab"

	# Send the emails to relevant people.
	emails = cf.getEmails()
	sendEmail(emails, "output.txt")

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