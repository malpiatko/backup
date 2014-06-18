""" init function has to be called first """
class ConfigReader:
	def __init__(self, fileName):
		self.fp = open(fileName, 'r')
		self.emails = self.getEmails()
		self.fp.close()

	def getEmails(self):
		emails = []
		for line in self.fp:
			emails.append(line.strip())
		return emails
