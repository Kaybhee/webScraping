#Sending an Email through an SMTP server
from email.message import EmailMessage
from email.headerregistry import Address
from email.utils import make_msgid, localtime
import smtplib
import poplib
import imaplib
import re
import time

class FieldMissing(Exception):
	def __init__(self, missing_field):
		self.err_msg = '{} is missing'.format(missing_field)
	def __str__(self):
		return self.err_msg

class IMAPError(Exception):
	def __init__(self, error):
		self.err_msg = error

class Message(object):

	def create_mime(self, **kwargs):
		'''create a mine message'''

		if not kwargs.get('recipient_email_addr'):
			raise FieldMissing('recipient_email_addr')
		if not kwargs.get('sender_email_addr'):
			raise FieldMissing('sender_email_addr')

		subject = kwargs.get('subject') or ''
		sender_display_name = kwargs.get('sender_display_name') or ''
		sender_email_addr = kwargs['sender_email_addr']
		recipient_display_name = kwargs.get('recipient_display_name') or ''
		recipient_email_addr = kwargs['recipient_email_addr']
		content_html = kwargs.get('content_html') or ''
		content_text = kwargs.get('content_text') or ''
		custom_header = kwargs.get('custom_header') # a dictionary containing customized headers

		message_id = make_msgid(domain =sender_email_addr.split('@')[1])

		self.msg = EmailMessage()
		self.msg['Subject'] = subject
		self.msg['From'] = Address(display_name=sender_display_name, addr_spec=sender_email_addr)
		self.msg['To'] = Address(display_name=recipient_display_name, addr_spec=recipient_email_addr)
		self.msg['Date'] = localtime()
		self.msg.add_header('Message-ID', '<'+message_id[1:-1]+'>')
		if custom_header:
			for key, value in custom_header.items():
				self.msg.add_header(key, value)
		if content_text:
			self.msg.set_content(content_text)
			if content_html:
				self.msg.add_alternative(content_html, subtype='html')
		else:
			self.msg.set_content(content_html,subtype='html')
		
		return self.msg

	def __str__(self):
		return str(self.msg)

class User(object):
	def __init__(self, **kwargs):

		#parameters for SMTP server
		self.SMTP_server = kwargs.get('SMTP_server')
		self.SMTP_account = kwargs.get('SMTP_account')
		self.SMTP_password = kwargs.get('SMTP_password')
		self.SMTP_server = kwargs.get('SMTP_server')

		#parameters for POP3 server
		self.POP3_server = kwargs.get('POP3_server')
		self.POP3_password = kwargs.get('POP3_password')
		self.POP3_account = kwargs.get('POP3_account')

		#parameters for IMAP server
		self.IMAP_server = kwargs.get('IMAP_server')
		self.IMAP_password = kwargs.get('IMAP_password')
		self.IMAP_account = kwargs.get('IMAP_account')
	
class SMTP(Message, User):

	def __init__(self, SMTP_port=25, **kwargs):
		'''default port = 25'''
		self.port = SMTP_port
		super().__init__(**kwargs)
		if not self.SMTP_server:
			raise FieldMissing('SMTP_server')
		if not self.SMTP_account:
			raise FieldMissing('SMTP_account')
		if not self.SMTP_password:
			raise FieldMissing('SMTP_password')


	def send_msg(self):
		'''connect to SMTP server and send the message'''
		with smtplib.SMTP(self.SMTP_server, self.port) as server:
			server.starttls()
			server.login(self.SMTP_account, self.SMTP_password) 
			server.set_debuglevel(False)
			server.send_message(self.msg)
		return 'Success'

#retrieve messages via SSL enabled POP3
class POP3(User):

	def __init__(self, POP3_port=995, **kwargs):
		self.port = POP3_port
		super().__init__(**kwargs)
		if not self.POP3_server:
			raise FieldMissing('POP3_server')
		if not self.POP3_account:
			raise FieldMissing('POP3_account')
		if not self.POP3_password:
			raise FieldMissing('POP3_password')
		self.mailbox = POP3Connect(self.POP3_server, POP3_port,
						self.POP3_account, self.POP3_password)


	def retrieve_msg(self):
		with self.mailbox as _mailbox:
			num_msg = len(_mailbox.list()[1])
			for i in range(num_msg):
				for msg in _mailbox.retr(i+1)[1]:
					yield msg

	def mailbox_size(self):
		with self.mailbox as _mailbox:
			stat = _mailbox.stat()
			size = {'message count': stat[0], 'mailbox size': stat[1]}
		return size

	def retrieve_entire_msg(self, start:int=1, end=int()):
		with self.mailbox as _mailbox:
			num_msg = len(_mailbox.list()[1])
			for i in range(start, end+1 if end and end<num_msg else num_msg+1):
				msg = ''
				for line in _mailbox.retr(i)[1]:
					msg += line.decode() + '\n'
				yield msg


#retrieve messages via SSL enabled IMAP
class IMAP(User):
	def __init__(self, IMAP_port=993, **kwargs):
		self.port = IMAP_port
		super().__init__(**kwargs)
		if not self.IMAP_server:
			raise FieldMissing('IMAP_server')
		if not self.IMAP_account:
			raise FieldMissing('IMAP_account')
		if not self.IMAP_password:
			raise FieldMissing('IMAP_password')

	def retrieve_msg(self, delete=False, mailbox_name='', msg_id='',
					search_section='', search_text=''):
		#select a mailbox or lablel, return message IDs under the mailbox label
		'''Possible sections:

		BCC <string>
         Messages that contain the specified string in the envelope
         structure's BCC field.

		BEFORE <date>
		 Messages whose internal date (disregarding time and timezone)
		 is earlier than the specified date.

		BODY <string>
		 Messages that contain the specified string in the body of the
		 message.

		CC <string>
		 Messages that contain the specified string in the envelope
		 structure's CC field.

		FROM <string>
		 Messages that contain the specified string in the envelope
		 structure's FROM field.

		HEADER <field-name> <string>
		 Messages that have a header with the specified field-name (as
		 defined in [RFC-2822]) and that contains the specified string
		 in the text of the header (what comes after the colon).  If the
		 string to search is zero-length, this matches all messages that
		 have a header line with the specified field-name regardless of
		 the contents.

		KEYWORD <flag>
		 Messages with the specified keyword flag set.

		LARGER <n>
		 Messages with an [RFC-2822] size larger than the specified
		 number of octets.
	
		NOT <search-key>
		 Messages that do not match the specified search key.

		ON <date>
		 Messages whose internal date (disregarding time and timezone)
		 is within the specified date.
		 SENTBEFORE <date>
		 Messages whose [RFC-2822] Date: header (disregarding time and
		 timezone) is earlier than the specified date.

		SENTON <date>
		 Messages whose [RFC-2822] Date: header (disregarding time and
		 timezone) is within the specified date.

		SENTSINCE <date>
		 Messages whose [RFC-2822] Date: header (disregarding time and
		 timezone) is within or later than the specified date.

		SINCE <date>
		 Messages whose internal date (disregarding time and timezone)
		 is within or later than the specified date.

		SMALLER <n>
		 Messages with an [RFC-2822] size smaller than the specified
		 number of octets.

		SUBJECT <string>
		 Messages that contain the specified string in the envelope
		 structure's SUBJECT field.

		TEXT <string>
		 Messages that contain the specified string in the header or
		 body of the message.

		TO <string>
		 Messages that contain the specified string in the envelope
		 structure's TO field.

		UID <sequence set>
		 Messages with unique identifiers corresponding to the specified
		 unique identifier set.  Sequence set ranges are permitted.
		'''

		if search_section and not search_text:
			raise FieldMissing('search_text')
		if not search_section and search_text:
			raise FieldMissing('search_section')
		if (search_section or search_text) and msg_id:
			raise 'Unexpected field, remove msg_id or search_section and search_text'

		with imaplib.IMAP4_SSL(self.IMAP_server, self.port)	as mailbox:
			mailbox.login(self.IMAP_account, self. IMAP_password)
			if not mailbox_name:
				status, label = mailbox.list()
				if status != 'OK':
					raise IMAPError(label[0].decode())
				options = {}
				for ind, item in enumerate(label):
					flags, delimiter, mailbox_name = re.compile(r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)').match(item.decode()).groups()
					options[ind] = mailbox_name
					print('{0}. {1}'.format(ind, mailbox_name))
				choice = int(input('Please select a mailbox: '))
				mailbox_name = options[choice]
			status, num_msg = mailbox.select(mailbox_name)
			if status != 'OK':
				raise IMAPError(num_msg[0].decode())
			if (not msg_id or msg_id == 'all') and not search_section and not search_text:
				status, message_id = mailbox.search(None, 'all')
				if status != 'OK':
					raise IMAPError(message_id[0].decode())
				if not message_id[0]:
					raise ValueError('No message found in mailbox')
				if msg_id == 'all':
					_msg_id = message_id[0].decode().split(' ')
				else:
					print('message id:', message_id[0].decode())
					select_msg = input('Please select mail ID to retrieve email(e.g. 1-5,6,7): ')
					_msg_id = []
					msg_range = False
					for char in select_msg:
						if char.isdigit():
							if msg_range == False:
								_msg_id.append(int(char))
							elif msg_range == True:
								_msg_id = _msg_id + list(range(int(_msg_id[-1])+1, int(char)+1))
								msg_range = False			
						elif char == '-':
							msg_range = True

			if not msg_id and search_section and search_text:
				status, message_id = mailbox.search(None, search_section, '"{}"'.format(search_text))
				if status != 'OK':
					raise IMAPError(message_id[0].decode())
				if not message_id[0]:
					raise ValueError('No message found in mailbox')
				_msg_id = message_id[0].decode().split(' ')

			for _id in _msg_id:
				status, msg = mailbox.fetch(_id, '(RFC822)')
				if status != 'OK':
					raise IMAPError(msg)
				if delete == True:
					mailbox.store(_id, '+FLAGS', '\\Deleted')
				yield msg[0]
			mailbox.expunge()



	def list_mailbox(self):
		#list mailbox labels
		with imaplib.IMAP4_SSL(self.IMAP_server, self.port)	as mailbox:
			mailbox.login(self.IMAP_account, self.IMAP_password)
			status, label = mailbox.list()
			if status != 'OK':
				raise IMAPError(label[0].decode())
			else:
				mailbox = {}
				for ind, item in enumerate(label):
					flags, delimiter, mailbox_name = re.compile(r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)').match(item.decode()).groups()
					mailbox[ind] = mailbox_name
				return mailbox

	def list_msg(self, mailbox_name):
		#list message indexes in a mailbox
		with imaplib.IMAP4_SSL(self.IMAP_server, self.port)	as mailbox:
			mailbox.login(self.IMAP_account, self.IMAP_password)
			status, num_msg = mailbox.select(mailbox_name)
			if status != 'OK':
				raise IMAPError(num_msg[0].decode())
			else:
				status, message_id = mailbox.search(None, 'all')
				if status != 'OK':
					raise IMAPError(message_id[0].decode())
				else:
					return message_id



	def _search_query():
	    query = []
	    for name, value in kwargs.items():
	        if value is not None:
	            if isinstance(value, datetime.date):
	                value = value.strftime('%d-%b-%Y')
	            if isinstance(value, str) and '"' in value:
	                value = value.replace('"', "'")
	            query.append(imap_attribute_lookup[name].format(value))

	    if query:
	        return " ".join(query)

	    return "(ALL)"

class POP3Connect:
	'''connect to pop3 server with context manager'''
	def __init__(self, host, port, account, password, callbackOnExit=None, waitingTime=0):
		self.host = host
		self.port = port
		self.account = account
		self.password = password
		self.mailbox = None
		self.callbackOnExit = callbackOnExit
		self.waitingTime = waitingTime

	def __enter__(self):
		if self.mailbox is not None:
			raise RuntimeError('Already connected')
		self.mailbox = poplib.POP3_SSL(self.host, self.port) 
		self.mailbox.user(self.account)
		self.mailbox.pass_(self.password)

		return self.mailbox

	def __exit__(self, exc_ty, exc_val, tb):
		self.mailbox.quit()
		self.mailbox = None
		time.sleep(self.waitingTime)
		if self.callbackOnExit:
			self.callbackOnExit(f'{exc_ty}, {exc_val}, {tb}')
