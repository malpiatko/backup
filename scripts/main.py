#!/usr/bin/python
import smtplib
import configReader
import md5dir
import os
import sys
import argparse
import datetime

from email.mime.text import MIMEText

def main(directory, config, output, stdout=False):
	# Read configuration file
	cf = configReader.ConfigReader(config)

	# Find the changes since last update and write to output.txt or standard output.
	if not stdout:
		outputFile = open(output, "w+")
		# Since md5dir function outputs to standard output we have to set the stdout to
		# our destination file for the time of executing the function.
		sys.stdout = outputFile
		changedFiles = md5dir.md5dir(directory, md5dir.master_list(directory), master=True)
		# Reset stdout to default.
		sys.stdout = sys.__stdout__
		outputFile.write(str(datetime.datetime.now()))
		outputFile.close()
	else:
		md5dir.md5dir(directory, md5dir.master_list(directory), master=True)

	# Send the emails to relevant people.
	emails = cf.getEmails()
	#sendEmail(emails, output)

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
	msg['Subject'] = "The content of %s" % fileName
	msg['From'] = "ela@lshift.net"
	msg['To'] = ', '.join(addrs)
	s = smtplib.SMTP('localhost')
	s.sendmail("ela@lshift.net", addrs, msg.as_string())
	s.quit()

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("dir", help=("Directory on which you want to perform the file comparison." 
		"Note the directory needs to have the md5sum already."))
	parser.add_argument("-c", "--config", help=("The location to the config file. By default it's"
		"config.txt in the directory to be analyzed."))
	parser.add_argument("-o", "--output", help=("The location of the file where you want to store the"
		"result of the comparison."))
	parser.add_argument("--stdout", action="store_true", help=("If set the output of the comparison is"
	 "not saved to file but is written to standard output. It's pure purspose is debugging."))
	args = parser.parse_args()

	# Directory
	directory = args.dir if args.dir else "."
	# Config file location
	config = args.config if args.config else directory + "/config.txt"
	# Output file
	output = args.output if args.output else directory + "/output.txt"
	# Standard output
	if args.stdout:
		main(directory, config, output, stdout=True)
	else:
		main(directory, config, output)