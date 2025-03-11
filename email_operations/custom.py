# Add AI & Database Storage Mechanism to Indentify and Save Folder Details

import smtplib
import imaplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import email
from email.parser import BytesParser
from email.policy import default
import email.utils
import re
import logging
from typing import Dict, Union, List
from datetime import datetime, timedelta

class EmailClient:
    
    def __init__(
        self,
        email_address: str,
        password: str,
        smtp_server: str,
        imap_server: str,
        smtp_port: int = 587,
        imap_port: int = 993
    ):

        self.email_address = email_address
        self.password = password
        self.smtp_server = smtp_server
        self.imap_server = imap_server
        self.smtp_port = smtp_port
        self.imap_port = imap_port
        
        # Logger setup
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def send_email(
        self,
        receiver_email: str,
        subject: str,
        body: str
    ) -> Dict[str, Union[bool, str]]:

        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = receiver_email
            msg['Subject'] = subject
            
            # Attach body text
            msg.attach(MIMEText(body, 'plain'))
            
            # Connect to server
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()  # Enable TLS encryption
            server.login(self.email_address, self.password)
            
            # Send the message
            server.sendmail(self.email_address, receiver_email, msg.as_string())
            server.quit()
            
            return {
                "success": True,
                "message": f"Email sent successfully to {receiver_email}"
            }
            
        except Exception as e:
            error_message = f"Failed to send email: {str(e)}"
            self.logger.error(error_message)
            return {
                "success": False,
                "message": error_message
            }
    
    def draft_email(
        self,
        receiver_email: str,
        subject: str,
        body: str,
        draft_folder: str
    ) -> Dict[str, Union[bool, str]]:

        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = receiver_email
            msg['Subject'] = subject
            msg['Date'] = email.utils.formatdate(localtime=True)
            msg['Message-ID'] = email.utils.make_msgid()
            
            # Attach body text
            msg.attach(MIMEText(body, 'plain'))
            
            # Connect to IMAP server
            server = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            server.login(self.email_address, self.password)
            
            # Select drafts folder
            server.select(draft_folder)
            
            # Save message as draft
            message_string = msg.as_string()
            server.append(draft_folder, '\\Draft', None, message_string.encode('utf-8'))
            
            server.logout()
            
            return {
                "success": True,
                "message": "Email draft saved successfully"
            }
            
        except Exception as e:
            error_message = f"Failed to save draft: {str(e)}"
            self.logger.error(error_message)
            return {
                "success": False,
                "message": error_message
            }
    
    def create_label(self, label_name: str) -> Dict[str, Union[bool, str]]:

        try:
            # Connect to the IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.password)
            
            # Check if the label already exists
            status, existing_labels = mail.list()
            
            # Check if label already exists
            label_exists = False
            if status == "OK":
                for label in existing_labels:
                    if isinstance(label, bytes):
                        label = label.decode('utf-8')
                    if f'"{label_name}"' in label or f'/{label_name}' in label:
                        label_exists = True
                        break
            
            if label_exists:
                mail.logout()
                return {
                    "success": True,
                    "message": f"Label '{label_name}' already exists"
                }
            
            # For Gmail, labels might need special formatting
            # Enclose the label name in quotes to handle spaces
            quoted_label = f'"{label_name}"'
            
            # Create the label/folder
            status, response = mail.create(quoted_label)
            
            if status != "OK":
                raise Exception(f"Failed to create label '{label_name}': {response}")
            
            mail.logout()
            
            return {
                "success": True,
                "message": f"Label '{label_name}' created successfully"
            }
            
        except Exception as e:
            error_message = f"Failed to create label: {str(e)}"
            self.logger.error(error_message)
            return {
                "success": False,
                "message": error_message
            }
    
    def add_label_to_email(self, message_id: str, label: str) -> bool:

        try:
            # Connect to the IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_address, self.password)
            mail.select("INBOX")  # Ensure we're in the correct folder
            
            # Search for the email by Message-ID
            status, message_numbers = mail.search(None, f'HEADER Message-ID "{message_id}"')
            if status != "OK" or not message_numbers[0]:
                raise Exception(f"Email with Message-ID {message_id} not found.")
            
            # Get the email's unique identifier
            email_id = message_numbers[0].split()[0]
            
            # Add the Gmail label using X-GM-LABELS
            status, response = mail.store(email_id, "+X-GM-LABELS", f'"{label}"')
            if status != "OK":
                raise Exception(f"Failed to add label '{label}' to email.")
            
            self.logger.info(f"Label '{label}' added to email with Message-ID {message_id}.")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding label: {str(e)}")
            return False
    
    def mark_as_starred(self, message_id: str) -> bool:

        try:
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_address, self.password)
            
            # Select the inbox
            status, messages = mail.select("INBOX")
            if status != "OK":
                raise Exception("Could not access INBOX")

            # Search for the email with the given Message-ID
            search_criteria = f'HEADER Message-ID "{message_id}"'
            status, message_numbers = mail.search(None, search_criteria)
            if status != "OK" or not message_numbers[0]:
                raise Exception(f"Email with Message-ID {message_id} not found")

            # Mark the email as starred
            email_id = message_numbers[0].split()[0]
            mail.store(email_id, "+FLAGS", "\\Flagged")
            self.logger.info(f"Email with Message-ID {message_id} marked as starred.")
            mail.logout()
            return True
            
        except Exception as e:
            self.logger.error(f"Error marking email as starred: {str(e)}")
            return False
    
    def send_reply(self, message_id: str, reply_body: str) -> Dict[str, Union[bool, str]]:

        try:
            # Connect to IMAP server to find the original message
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.password)
            mail.select("INBOX")
            
            # Search for the email with the given Message-ID
            search_criteria = f'HEADER Message-ID "{message_id}"'
            status, message_numbers = mail.search(None, search_criteria)
            if status != "OK" or not message_numbers[0]:
                raise Exception(f"Email with Message-ID {message_id} not found")
            
            # Get the email data
            email_id_num = message_numbers[0].split()[0]
            status, msg_data = mail.fetch(email_id_num, '(RFC822)')
            if status != "OK":
                raise Exception("Failed to fetch email data")
            
            # Parse the email
            raw_email = msg_data[0][1]
            original_msg = BytesParser(policy=default).parsebytes(raw_email)
            
            # Get original sender and subject
            original_sender = original_msg['From']
            original_subject = original_msg['Subject']
            
            # Extract email address from sender (might be in format "Name <email@example.com>")
            email_match = re.search(r'<(.+?)>', original_sender)
            if email_match:
                receiver_email = email_match.group(1)
            else:
                receiver_email = original_sender
            
            # Create reply subject (add Re: if not already present)
            if original_subject.lower().startswith('re:'):
                reply_subject = original_subject
            else:
                reply_subject = f"Re: {original_subject}"
            
            # Create reply message
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = receiver_email
            msg['Subject'] = reply_subject
            msg['In-Reply-To'] = message_id
            msg['References'] = message_id
            
            # Attach body text
            msg.attach(MIMEText(reply_body, 'plain'))
            
            # Connect to SMTP server and send the message
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_address, self.password)
            server.sendmail(self.email_address, receiver_email, msg.as_string())
            server.quit()
            
            # Close IMAP connection
            mail.logout()
            
            return {
                "success": True,
                "message": f"Reply sent successfully to {receiver_email}"
            }
            
        except Exception as e:
            error_message = f"Failed to send reply: {str(e)}"
            self.logger.error(error_message)
            return {
                "success": False,
                "message": error_message
            }
    
    def draft_reply(
        self, 
        message_id: str, 
        reply_body: str, 
        draft_folder: str
    ) -> Dict[str, Union[bool, str]]:

        try:
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.password)
            mail.select("INBOX")
            
            # Search for the email with the given Message-ID
            search_criteria = f'HEADER Message-ID "{message_id}"'
            status, message_numbers = mail.search(None, search_criteria)
            if status != "OK" or not message_numbers[0]:
                raise Exception(f"Email with Message-ID {message_id} not found")
            
            # Get the email data
            email_id_num = message_numbers[0].split()[0]
            status, msg_data = mail.fetch(email_id_num, '(RFC822)')
            if status != "OK":
                raise Exception("Failed to fetch email data")
            
            # Parse the email
            raw_email = msg_data[0][1]
            original_msg = BytesParser(policy=default).parsebytes(raw_email)
            
            # Get original sender and subject
            original_sender = original_msg['From']
            original_subject = original_msg['Subject']
            
            # Extract email address from sender
            email_match = re.search(r'<(.+?)>', original_sender)
            if email_match:
                receiver_email = email_match.group(1)
            else:
                receiver_email = original_sender
            
            # Create reply subject
            if original_subject.lower().startswith('re:'):
                reply_subject = original_subject
            else:
                reply_subject = f"Re: {original_subject}"
            
            # Create draft reply message
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = receiver_email
            msg['Subject'] = reply_subject
            msg['Date'] = email.utils.formatdate(localtime=True)
            msg['Message-ID'] = email.utils.make_msgid()
            msg['In-Reply-To'] = message_id
            msg['References'] = message_id
            
            # Attach body text
            msg.attach(MIMEText(reply_body, 'plain'))
            
            # Switch to drafts folder
            mail.select(draft_folder)
            
            # Save message as draft
            message_string = msg.as_string()
            mail.append(draft_folder, '\\Draft', None, message_string.encode('utf-8'))
            
            mail.logout()
            
            return {
                "success": True,
                "message": f"Reply draft saved successfully for email to {receiver_email}"
            }
            
        except Exception as e:
            error_message = f"Failed to save reply draft: {str(e)}"
            self.logger.error(error_message)
            return {
                "success": False,
                "message": error_message
            }
    
    def list_folders(self) -> Dict[str, Union[bool, List[str], str]]:

        try:
            # Connect to the IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.password)
            
            # List all available folders/mailboxes
            status, folder_list = mail.list()
            
            if status != "OK":
                raise Exception(f"Failed to retrieve folder list: {folder_list}")
            
            # Parse folder names
            folders = []
            for folder in folder_list:
                if folder:
                    # Decode bytes to string if necessary
                    if isinstance(folder, bytes):
                        folder = folder.decode('utf-8')
                    
                    # Extract the folder name (typically the last part after the delimiter)
                    parts = folder.split(' "/"' if ' "/" ' in folder else ' "." ' if ' "." ' in folder else ' ')
                    folder_name = parts[-1].strip('"')
                    folders.append(folder_name)
            
            mail.logout()
            
            # return {
            #     "success": True,
            #     "folders": folders,
            #     "message": f"Successfully retrieved {len(folders)} folders"
            # }
        
            return folders
            
        except Exception as e:
            error_message = f"Failed to list email folders: {str(e)}"
            self.logger.error(error_message)
            return {
                "success": False,
                "folders": [],
                "message": error_message
            }
    
    def get_recent_message_ids(
        self, 
        minutes: int = 3, 
        folder: str = "INBOX"
    ) -> Dict[str, Union[bool, List[str], str]]:

        try:
            # Connect to the IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.password)
            mail.select(folder)
            
            # Calculate the time threshold (current time - minutes)
            time_threshold = datetime.now() - timedelta(minutes=minutes)
            # Format the date according to IMAP4 search criteria (DD-MMM-YYYY)
            date_str = time_threshold.strftime("%d-%b-%Y")
            
            # Search for emails newer than the threshold
            status, message_numbers = mail.search(None, f'SENTSINCE {date_str}')
            
            if status != "OK":
                raise Exception(f"Failed to search for recent emails: {message_numbers}")
            
            message_ids = []
            
            # If we have message numbers, fetch each message header
            if message_numbers and message_numbers[0]:
                message_number_list = message_numbers[0].split()
                
                for num in message_number_list:
                    # Fetch the message headers
                    status, msg_data = mail.fetch(num, '(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID DATE)])')
                    if status != "OK":
                        continue
                    
                    # Parse the headers
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            # Parse header
                            header_data = response_part[1]
                            parser = BytesParser(policy=default)
                            headers = parser.parsebytes(header_data)
                            
                            # Get message ID and date
                            message_id = headers.get('Message-ID', headers.get('Message-Id', None))
                            date_str = headers.get('Date', None)
                            
                            if message_id and date_str:
                                # Parse the date to compare with our threshold
                                try:
                                    # Parse email date format
                                    date_tuple = email.utils.parsedate_tz(date_str)
                                    if date_tuple:
                                        # Convert to timestamp and then to datetime
                                        timestamp = email.utils.mktime_tz(date_tuple)
                                        message_date = datetime.fromtimestamp(timestamp)
                                        
                                        # Check if the message is within our time window
                                        if message_date >= time_threshold:
                                            message_ids.append(message_id)
                                except Exception as date_error:
                                    self.logger.warning(f"Error parsing date: {date_error}")
            
            mail.logout()
            
            # return {
            #     "success": True,
            #     "message_ids": message_ids,
            #     "message": f"Found {len(message_ids)} messages in the last {minutes} minutes"
            # }

            return message_ids
            
        except Exception as e:
            error_message = f"Failed to retrieve recent message IDs: {str(e)}"
            self.logger.error(error_message)
            return {
                "success": False,
                "message_ids": [],
                "message": error_message
            }
    
    def get_recent_thread_ids(
        self, 
        minutes: int = 3, 
        folder: str = "INBOX"
    ) -> Dict[str, Union[bool, List[str], str]]:

        try:
            # Connect to the IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.password)
            mail.select(folder)
            
            # Calculate the time threshold (current time - minutes)
            time_threshold = datetime.now() - timedelta(minutes=minutes)
            # Format the date according to IMAP4 search criteria (DD-MMM-YYYY)
            date_str = time_threshold.strftime("%d-%b-%Y")
            
            # Search for emails newer than the threshold
            status, message_numbers = mail.search(None, f'SENTSINCE {date_str}')
            
            if status != "OK":
                raise Exception(f"Failed to search for recent emails: {message_numbers}")
            
            thread_ids = set()  # Use a set to avoid duplicates
            
            # If we have message numbers, fetch each message
            if message_numbers and message_numbers[0]:
                message_number_list = message_numbers[0].split()
                
                # Determine if this is Gmail (which supports X-GM-THRID)
                is_gmail = "gmail" in self.imap_server.lower()
                
                for num in message_number_list:
                    # For Gmail, fetch the thread ID using X-GM-THRID
                    if is_gmail:
                        try:
                            # Fetch Gmail's thread ID
                            status, response = mail.fetch(num, '(X-GM-THRID)')
                            if status == "OK" and response and response[0]:
                                # Extract thread ID from response
                                response_str = response[0].decode('utf-8') if isinstance(response[0], bytes) else response[0]
                                thread_match = re.search(r'X-GM-THRID\s+(\d+)', response_str)
                                if thread_match:
                                    thread_id = thread_match.group(1)
                                    
                                    # Fetch the message date to check if it's within our time window
                                    status, msg_data = mail.fetch(num, '(BODY.PEEK[HEADER.FIELDS (DATE)])')
                                    if status == "OK" and msg_data and msg_data[0]:
                                        for response_part in msg_data:
                                            if isinstance(response_part, tuple):
                                                # Parse header
                                                header_data = response_part[1]
                                                parser = BytesParser(policy=default)
                                                headers = parser.parsebytes(header_data)
                                                
                                                date_str = headers.get('Date', None)
                                                
                                                if date_str:
                                                    try:
                                                        # Parse email date format
                                                        date_tuple = email.utils.parsedate_tz(date_str)
                                                        if date_tuple:
                                                            # Convert to timestamp and then to datetime
                                                            timestamp = email.utils.mktime_tz(date_tuple)
                                                            message_date = datetime.fromtimestamp(timestamp)
                                                            
                                                            # Check if the message is within our time window
                                                            if message_date >= time_threshold:
                                                                thread_ids.add(thread_id)
                                                    except Exception as date_error:
                                                        self.logger.warning(f"Error parsing date: {date_error}")
                        except Exception as thread_error:
                            self.logger.warning(f"Error fetching Gmail thread ID: {thread_error}")
                    
                    # For non-Gmail or as fallback, use References and In-Reply-To headers
                    if not is_gmail or len(thread_ids) == 0:
                        try:
                            # Fetch message headers
                            status, msg_data = mail.fetch(num, '(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID REFERENCES IN-REPLY-TO DATE)])')
                            if status == "OK" and msg_data and msg_data[0]:
                                for response_part in msg_data:
                                    if isinstance(response_part, tuple):
                                        # Parse header
                                        header_data = response_part[1]
                                        parser = BytesParser(policy=default)
                                        headers = parser.parsebytes(header_data)
                                        
                                        # Get message ID, references, and date
                                        message_id = headers.get('Message-ID', headers.get('Message-Id', None))
                                        references = headers.get('References', None)
                                        in_reply_to = headers.get('In-Reply-To', None)
                                        date_str = headers.get('Date', None)
                                        
                                        # Check if it's within our time window
                                        if date_str:
                                            try:
                                                # Parse email date format
                                                date_tuple = email.utils.parsedate_tz(date_str)
                                                if date_tuple:
                                                    # Convert to timestamp and then to datetime
                                                    timestamp = email.utils.mktime_tz(date_tuple)
                                                    message_date = datetime.fromtimestamp(timestamp)
                                                    
                                                    # Check if the message is within our time window
                                                    if message_date >= time_threshold:
                                                        # For non-Gmail, we'll use the first message ID in References
                                                        # or the In-Reply-To as the thread ID
                                                        thread_id = None
                                                        
                                                        if references:
                                                            # Get the first Message-ID in the References header
                                                            ref_ids = references.split()
                                                            if ref_ids:
                                                                thread_id = ref_ids[0].strip('<>')
                                                        
                                                        if not thread_id and in_reply_to:
                                                            thread_id = in_reply_to.strip('<>')
                                                        
                                                        # If no thread information, use its own Message-ID
                                                        if not thread_id and message_id:
                                                            thread_id = message_id.strip('<>')
                                                        
                                                        if thread_id:
                                                            thread_ids.add(thread_id)
                                            except Exception as date_error:
                                                self.logger.warning(f"Error parsing date: {date_error}")
                        except Exception as header_error:
                            self.logger.warning(f"Error fetching message headers: {header_error}")
            
            mail.logout()
            
            # return {
            #     "success": True,
            #     "thread_ids": list(thread_ids),
            #     "message": f"Found {len(thread_ids)} thread IDs in the last {minutes} minutes"
            # }

            return list(thread_ids)
            
        except Exception as e:
            error_message = f"Failed to retrieve recent thread IDs: {str(e)}"
            self.logger.error(error_message)
            return {
                "success": False,
                "thread_ids": [],
                "message": error_message
            }

    def fetch_message_details_condensed(self, message_id: str) -> Dict[str, Union[str, Dict[str, str]]]:

        try:
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.password)
            mail.select("INBOX")
            
            # Search for the email with the given Message-ID
            search_criteria = f'HEADER Message-ID "{message_id}"'
            status, message_numbers = mail.search(None, search_criteria)
            
            if status != "OK" or not message_numbers[0]:
                raise Exception(f"Email with Message-ID {message_id} not found")
            
            # Get the email data
            email_id_num = message_numbers[0].split()[0]
            status, msg_data = mail.fetch(email_id_num, '(RFC822)')
            
            if status != "OK":
                raise Exception("Failed to fetch email data")
            
            # Parse the email
            raw_email = msg_data[0][1]
            msg = BytesParser(policy=default).parsebytes(raw_email)
            
            # Extract subject
            subject = msg.get('Subject', '')
            
            # Extract sender email
            sender = msg.get('From', '')
            # Extract just the email address from the sender field
            email_match = re.search(r'<(.+?)>', sender)
            if email_match:
                sender_email = email_match.group(1)
            else:
                sender_email = sender
            
            # Extract body content
            body = ""
            
            # Handle multipart messages
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    # Skip attachments
                    if "attachment" in content_disposition:
                        continue
                    
                    # Get plain text body
                    if content_type == "text/plain":
                        body = part.get_payload(decode=True).decode()
                        break
                    
                    # Fallback to HTML if no plain text
                    elif content_type == "text/html" and not body:
                        body = part.get_payload(decode=True).decode()
            else:
                # For non-multipart messages
                body = msg.get_payload(decode=True).decode()
            
            mail.logout()
            
            return {
                "subject": subject,
                "body": body,
                "sender_email": sender_email
            }
            
        except Exception as e:
            error_message = f"Failed to fetch message details: {str(e)}"
            self.logger.error(error_message)
            return {
                "success": False,
                "message": error_message
            }

# if __name__ == "__main__":
    
#     # User Inputs
#     email_id = "subhraturning@gmail.com"
#     password = "iqgh oiay rzfz qqce"
#     smtp_server = "smtp.gmail.com"
#     imap_server = "imap.gmail.com"
#     smtp_port = 587
#     imap_port = 993
#     receiver_email_id = "roysubhradip001@gmail.com"
#     subject = "Test Email Subject"
#     body = "This is a test email body."
#     message_id = "<CAAYr76TsyzdwgNTVBDrS40GthPgs6wpEUKMk1NPfjV6SmGz8Zg@mail.gmail.com>"  
#     thread_id = "1825487172355256469"
#     label_name = "Priority"
#     draft_folder = "[Gmail]/Drafts"
#     reply_body = "This is a reply to your email."
    
#     # Initialize the EmailClient
#     client = EmailClient(
#         email_address=email_id,
#         password=password,
#         smtp_server=smtp_server,
#         imap_server=imap_server,
#         smtp_port=smtp_port,
#         imap_port=imap_port
#     )

#     result = client.fetch_message_details_condensed("<cplwhl.m7vxj7qprr5hhde@shows.bookmyshow.com>")
#     print(result)
        
#     # # Send a new email
#     # result = client.send_email(
#     #     receiver_email=receiver_email_id,
#     #     subject=subject,
#     #     body=body
#     # )
#     # print("Send email result:", result)
    
#     # # Save email as draft
#     # result = client.draft_email(
#     #     receiver_email=receiver_email_id,
#     #     subject=subject,
#     #     body=body,
#     #     draft_folder=draft_folder
#     # )
#     # print("Draft email result:", result)
    
#     # Create a new label
#     result = client.create_label(
#         label_name=label_name
#     )
#     print("Create label result:", result)
    
#     # # Add label to an email
#     # result = client.add_label_to_email(
#     #     message_id=message_id,
#     #     label=label_name
#     # )
#     # print("Add label result:", result)
    
#     # # Mark an email as starred
#     # result = client.mark_as_starred(
#     #     message_id=message_id
#     # )
#     # print("Mark as starred result:", result)
    
#     # # Send a reply to an email
#     # result = client.send_reply(
#     #     message_id=message_id,
#     #     reply_body=reply_body
#     # )
#     # print("Send reply result:", result)
    
#     # # Save reply as draft
#     # result = client.draft_reply(
#     #     message_id=message_id,
#     #     reply_body=reply_body,
#     #     draft_folder=draft_folder
#     # )
#     # print("Draft reply result:", result)
    
#     # # List all email folders
#     # result = client.list_folders()
#     # print("List folders result:", result)
    
#     # # Get recent message IDs
#     # result = client.get_recent_message_ids(
#     #     minutes=3
#     # )
#     # print("Recent message IDs result:", result)
    
#     # # Get recent thread IDs
#     # result = client.get_recent_thread_ids(
#     #     minutes=10
#     # )
#     # print("Recent thread IDs result:", result)
