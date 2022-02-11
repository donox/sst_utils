
import smtplib
import ssl
from email.message import EmailMessage


class ManageEmail(object):
    def __init__(self, sender, password):
        self.smtp_server = "smtp.ionos.com"
        self.port = 587  # For starttls
        self.sender_email = sender
        self.password = password
        self.recipients = []
        self.subject = None
        self.attachments = []
        self.body = None

    def add_recipient(self, recipient_email):
        self.recipients.append(recipient_email)

    def set_subject(self, subject):
        self.subject = subject

    def add_attachment(self, attachment_path):
        self.attachments.append(attachment_path)

    def set_body(self, body):
        self.body = body

    def send_email(self):
        if not self.recipients:
            raise ValueError("Attempt to send email with no recipients.")
        if not self.subject:
            raise ValueError("Attempt to send email with no subject.")
        if not self.body:
            raise ValueError("Attempt to send email with no body.")

        message = EmailMessage()
        message['Subject'] = self.subject
        message['From'] = self.sender_email
        receiver_email = self.recipients[0]
        if len(self.recipients) > 1:
            for receiver in self.recipients[1:]:
                receiver_email += ', ' + receiver
        message['To'] = receiver_email
        message.preamble = 'Message received by non-MIME-aware mail reader.\n'
        message.set_content(self.body)

        for path in self.attachments:
            filename = path.split('/')[-1]
            with open(path, 'rb') as fp:
                message.add_attachment(fp.read(), maintype='text', subtype='plain',
                                       filename=filename)

        # Create a secure SSL context
        context = ssl.create_default_context()

        # Try to log in to server and send email
        try:
            server = smtplib.SMTP(self.smtp_server, self.port)
            server.ehlo()  # Can be omitted
            server.starttls(context=context)  # Secure the connection
            server.ehlo()  # Can be omitted
            server.login(self.sender_email, self.password)
            server.send_message(message)
        except Exception as e:
            raise e
        finally:
            server.quit()

    def test_email(self):

        path = '/home/don/Documents/helpful commands'
        receiver_email = "don@theoxleys.com, donoxley@gmail.com"
        # receiver_email = "donoxley@gmail.com"
        content = "Hello there, how's it goin'"

        message = EmailMessage()
        message['Subject'] = "Testing"
        message['From'] = self.sender_email
        message['To'] = receiver_email
        message.preamble = 'Message received by non-MIME-aware mail reader.\n'
        message.set_content(content)

        with open(path, 'rb') as fp:
            message.add_attachment(fp.read(), maintype='text', subtype='plain',
                                   filename='helpful commands')

        # Create a secure SSL context
        context = ssl.create_default_context()

        # Try to log in to server and send email
        try:
            server = smtplib.SMTP(self.smtp_server, self.port)
            server.ehlo()  # Can be omitted
            server.starttls(context=context)  # Secure the connection
            server.ehlo()  # Can be omitted
            server.login(self.sender_email, self.password)
            server.send_message(message)
        except Exception as e:
            # Print any error messages to stdout
            print(e)
        finally:
            server.quit()
