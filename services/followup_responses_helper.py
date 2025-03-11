import os
import sys
import json
import boto3
import codecs
import imaplib
import smtplib
import csv
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from botocore.exceptions import ClientError
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain.output_parsers import BooleanOutputParser, PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from datetime import datetime, timedelta
from aws.utils import get_user_credentials

sys.path.append(str(Path(__file__).resolve().parent.parent))

from vectorDatabase.pinecone_chatbot_handler import Chatbot

# Load OpenAI API key from .env file
load_dotenv()

class FollowUpError(Exception):
    pass

class ThreadProcessingError(FollowUpError):
    pass

class EmailBody(BaseModel):
    body: str = Field(
        min_length=1,
        max_length=10000,
        description="The follow-up email body text",
        examples=["Thank you for your response. Regarding your question about..."]
    )
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "body": "Thank you for your email. I wanted to follow up on..."
                }
            ]
        }

class ManualGmailAutomation:
    def __init__(self, email_id, password, smtp_server, imap_server):
        self.email_id = email_id
        self.password = password
        self.smtp_server = smtp_server
        self.imap_server = imap_server
        self.imap = None
        self.smtp = None
        
    def connect_imap(self):
        try:
            self.imap = imaplib.IMAP4_SSL(self.imap_server)
            self.imap.login(self.email_id, self.password)
            return True
        except Exception as e:
            print(f"Error connecting to IMAP server: {str(e)}")
            return False
            
    def connect_smtp(self):
        try:
            self.smtp = smtplib.SMTP_SSL(self.smtp_server)
            self.smtp.login(self.email_id, self.password)
            return True
        except Exception as e:
            print(f"Error connecting to SMTP server: {str(e)}")
            return False
    
    def create_label(self, label_name):
        try:
            if not self.imap:
                if not self.connect_imap():
                    return False
            
            # Check if label exists
            status, labels = self.imap.list()
            labels = [label.decode().split('"')[-2] for label in labels if '"' in label.decode()]
            
            if label_name not in labels:
                self.imap.create(label_name)
            
            return True
        except Exception as e:
            print(f"Error creating label: {str(e)}")
            return False
    
    def add_label_to_message(self, message_id, label_name):
        try:
            if not self.imap:
                if not self.connect_imap():
                    return False
            
            # Select inbox
            self.imap.select('INBOX')
            
            # Search for the message
            status, data = self.imap.search(None, f'(HEADER Message-ID "{message_id}")')
            
            if status != 'OK' or not data[0]:
                print(f"Message not found with ID: {message_id}")
                return False
            
            # Add label to the message
            msg_num = data[0].split()[0]
            self.imap.store(msg_num, '+X-GM-LABELS', label_name)
            
            return True
        except Exception as e:
            print(f"Error adding label to message: {str(e)}")
            return False
    
    def draft_reply(self, message_id, reply_body):
        try:
            if not self.imap:
                if not self.connect_imap():
                    return False
                
            if not self.smtp:
                if not self.connect_smtp():
                    return False
            
            # Find the original message
            self.imap.select('INBOX')
            status, data = self.imap.search(None, f'(HEADER Message-ID "{message_id}")')
            
            if status != 'OK' or not data[0]:
                print(f"Message not found with ID: {message_id}")
                return False
            
            msg_num = data[0].split()[0]
            status, msg_data = self.imap.fetch(msg_num, '(RFC822)')
            
            if status != 'OK':
                print("Failed to fetch message")
                return False
            
            # Parse the message
            msg = email.message_from_bytes(msg_data[0][1])
            
            # Create reply message
            reply_msg = MIMEMultipart()
            reply_msg["From"] = self.email_id
            reply_msg["To"] = msg["From"]
            
            # Set subject with Re: prefix if not already present
            subject = msg["Subject"]
            if not subject.startswith("Re:"):
                subject = f"Re: {subject}"
            reply_msg["Subject"] = subject
            
            # Set In-Reply-To and References headers
            if msg["Message-ID"]:
                reply_msg["In-Reply-To"] = msg["Message-ID"]
                if msg["References"]:
                    reply_msg["References"] = f"{msg['References']} {msg['Message-ID']}"
                else:
                    reply_msg["References"] = msg["Message-ID"]
            
            # Add the reply body
            reply_msg.attach(MIMEText(reply_body, "plain"))
            
            # Save as draft (append to Drafts folder)
            draft_folder = '"[Gmail]/Drafts"'
            self.imap.append(draft_folder, '\\Draft', None, reply_msg.as_bytes())
            
            return True
        except Exception as e:
            print(f"Error creating draft reply: {str(e)}")
            return False
    
    def fetch_email_threads(self, num_prev_days=3) -> List[Dict[str, Any]]:
        try:
            if not self.imap:
                if not self.connect_imap():
                    return []
            
            # Select inbox
            self.imap.select('INBOX')
            
            # Calculate date for filtering
            date_since = (datetime.now() - timedelta(days=num_prev_days)).strftime("%d-%b-%Y")
            
            # Search for messages since the date
            status, data = self.imap.search(None, f'(SINCE "{date_since}")')
            
            if status != 'OK':
                print("Failed to search for messages")
                return []
            
            threads = []
            thread_ids = set()
            
            # Process each message
            for num in data[0].split():
                status, msg_data = self.imap.fetch(num, '(RFC822)')
                
                if status != 'OK':
                    continue
                
                msg = email.message_from_bytes(msg_data[0][1])
                
                # Extract thread ID (References or In-Reply-To)
                thread_id = None
                if msg["References"]:
                    thread_id = msg["References"].split()[0].strip('<>')
                elif msg["In-Reply-To"]:
                    thread_id = msg["In-Reply-To"].strip('<>')
                else:
                    thread_id = msg["Message-ID"].strip('<>')
                
                # Skip if we've already processed this thread
                if thread_id in thread_ids:
                    continue
                
                thread_ids.add(thread_id)
                
                # Extract message body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = msg.get_payload(decode=True).decode()
                
                # Create thread object
                thread = {
                    "thread_id": thread_id,
                    "total_messages": 1,
                    "messages": [{
                        "subject": msg["Subject"] or "(No Subject)",
                        "body": body,
                        "message_id": msg["Message-ID"].strip('<>')
                    }],
                    "reply_to_message_id": msg["Message-ID"].strip('<>')
                }
                
                threads.append(thread)
            
            return threads
        
        except Exception as e:
            print(f"Error fetching email threads: {str(e)}")
            return []

class SingleThreadProcessor:
    def analyze_email_thread(self, formatted_thread: str) -> bool:
        try:
            llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.0
            )
            
            output_parser = BooleanOutputParser()

            prompt_template = ChatPromptTemplate(
                messages=[
                    HumanMessagePromptTemplate.from_template(
                        """Analyze this email thread and determine if it requires follow-up.
                        
                        RULES:
                        1. Return TRUE if:
                        - There are unanswered questions
                        - There are pending requests
                        - The last message expects a response
                        - There are unresolved issues
                        
                        2. Return FALSE if:
                        - All queries are answered
                        - The conversation is concluded
                        - No response is expected
                        - The thread is complete
                        
                        IMPORTANT: Reply ONLY with 'true' or 'false'
                        
                        EMAIL THREAD:
                        {thread_content}
                        """
                    )
                ]
            )

            prompt = prompt_template.format_messages(thread_content=formatted_thread)
            response = llm.invoke(prompt).content.strip().lower()
            
            return output_parser.parse(response)

        except Exception as e:
            print(f"Error analyzing thread: {str(e)}")
            return False
    
    def format_message(self, message: dict, message_number: int) -> str:
        try:
            formatted = []
            formatted.append(f"MESSAGE {message_number}")
            formatted.append(f"Subject: {message['subject']}")
            formatted.append("")
            formatted.append("BODY:")
            formatted.append(message['body'])
            
            return "\n".join(formatted)
        
        except Exception as e:
            print(f"Error formatting message: {str(e)}")
            return ""

    def format_thread(self, thread: dict) -> str:
        try:
            formatted = []
            formatted.append("=" * 58)
            formatted.append(f"THREAD ID: {thread['thread_id']}")
            formatted.append(f"Total Messages: {thread['total_messages']}")
            
            for i, message in enumerate(thread['messages'], 1):
                formatted.append("-" * 58)
                formatted.append("")
                formatted.append(self.format_message(message, i))
                formatted.append("")
            
            formatted.append("=" * 58)
            return "\n".join(formatted)
        
        except Exception as e:
            print(f"Error formatting thread: {str(e)}")
            return ""

class FollowUpGenerator:
    def __init__(self):
        self.chatbot = Chatbot()
        self.parser = PydanticOutputParser(pydantic_object=EmailBody)
        
        self.followup_prompt = """Generate a professional follow-up email based on this thread.

        CRITICAL INSTRUCTIONS:
        1. Generate ONLY the email body content
        2. Must be relevant to the thread's context
        3. Address any pending points from previous messages
        4. Keep a professional but consistent tone
        5. Do not include any greetings, signatures, or subject lines
        6. Return only the body text, nothing else
        
        THREAD CONTENT:
        {thread_content}
        
        Return the email body in this format: {format_instructions}"""

    def create_followup_message(self, formatted_thread: str) -> str:
        try:
            prompt = PromptTemplate(
                template=self.followup_prompt,
                input_variables=["thread_content"],
                partial_variables={"format_instructions": self.parser.get_format_instructions()}
            )
            
            response = self.chatbot.get_response(
                prompt.format(thread_content=formatted_thread),
                "followup"
            )
            
            parsed = self.parser.parse(response)
            return parsed.body.strip()
            
        except Exception as e:
            print(f"Error generating follow-up message: {str(e)}")
            return ""

class ManualFollowUpEmailHandler:
    def __init__(self, config=None):
        self.config = config
        self.processor = SingleThreadProcessor()
        self.generator = FollowUpGenerator()
    
    def process_manual_followup(self, user_email: str, num_prev_days: Optional[int] = None) -> bool:
        try:
            # Get credentials
            password, mode, smtp_server, imap_server = get_user_credentials(user_email)
            
            if not password or not smtp_server or not imap_server:
                raise FollowUpError(f"Missing credentials for {user_email}")
                
            # Initialize components
            gmail_automation = ManualGmailAutomation(user_email, password, smtp_server, imap_server)
            
            # Fetch threads
            threads = gmail_automation.fetch_email_threads(
                num_prev_days or self.config.num_prev_days
            )
            
            if not threads:
                print("No email threads found for processing")
                return False
                
            # Process each thread
            for thread in threads:
                message_id = thread['reply_to_message_id']
                formatted_thread = self.processor.format_thread(thread)
                
                if self.processor.analyze_email_thread(formatted_thread):
                    followup_message = self.generator.create_followup_message(formatted_thread)
                    gmail_automation.create_label(self.config.label_name)
                    gmail_automation.add_label_to_message(message_id, self.config.label_name)
                    if gmail_automation.draft_reply(message_id, followup_message):
                        return True
            
            return False
            
        except Exception as e:
            print(f"Error in manual follow-up processing: {str(e)}")
            return False
