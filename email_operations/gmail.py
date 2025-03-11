import json
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta

class GmailAutomation:
    
    def __init__(self, email_id, refresh_token, access_token):

        self.email_id = email_id
        self.refresh_token = refresh_token
        self.access_token = access_token
        self.gcp_creds = self._load_gcp_credentials()
        self.service = self._create_gmail_service()

    def _load_gcp_credentials(self):

        try:
            with open('credentials/credential_gcp.json', 'r') as f:
                creds_data = json.load(f)
            return creds_data['web']
        except FileNotFoundError:
            raise FileNotFoundError("GCP credentials file not found at 'credentials/credential_gcp.json'")
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON in GCP credentials file")

    def _create_gmail_service(self):

        try:
            creds = Credentials(
                token=self.access_token,
                refresh_token=self.refresh_token,
                token_uri=self.gcp_creds['token_uri'],
                client_id=self.gcp_creds['client_id'],
                client_secret=self.gcp_creds['client_secret'],
                scopes=['https://www.googleapis.com/auth/gmail.modify']
            )
            return build('gmail', 'v1', credentials=creds)
        except Exception as e:
            raise Exception(f"Failed to create Gmail service: {str(e)}")

    def create_draft(self, to_email, subject, body):

        try:
            # Create message container
            message = MIMEMultipart()
            message['to'] = to_email
            message['from'] = self.email_id
            message['subject'] = subject

            # Add body
            msg = MIMEText(body)
            message.attach(msg)

            # Encode the message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            draft_message = {'message': {'raw': raw_message}}

            # Create the draft
            draft = self.service.users().drafts().create(
                userId='me',
                body=draft_message
            ).execute()

            return {
                'status': 'success',
                'draft_id': draft['id'],
                'message': 'Draft created successfully'
            }

        except HttpError as error:
            return {
                'status': 'error',
                'message': f'An HTTP error occurred: {error}'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }
        
    def draft_reply(self, message_id, reply_body):

        try:
            # Get the original message to extract headers
            original = self.service.users().messages().get(
                userId='me', 
                id=message_id, 
                format='full'
            ).execute()

            # Get thread ID to maintain conversation
            thread_id = original['threadId']

            # Create reply message
            message = MIMEMultipart()
            message['References'] = thread_id
            message['In-Reply-To'] = message_id
            message['from'] = self.email_id
            
            # Extract original recipients
            headers = original['payload']['headers']
            for header in headers:
                if header['name'] == 'From':
                    message['to'] = header['value']
                if header['name'] == 'Subject':
                    message['subject'] = f"Re: {header['value']}"

            # Add reply body
            msg = MIMEText(reply_body)
            message.attach(msg)

            # Encode the message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            draft_message = {
                'message': {
                    'raw': raw_message,
                    'threadId': thread_id
                }
            }

            # Create the draft
            draft = self.service.users().drafts().create(
                userId='me',
                body=draft_message
            ).execute()

            return {
                'status': 'success',
                'draft_id': draft['id'],
                'message': 'Reply draft created successfully'
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }

    def create_label(self, label_name):

        try:
            # List all labels to check if it exists
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            # Check if label already exists
            for label in labels:
                if label['name'].lower() == label_name.lower():
                    return {
                        'status': 'success',
                        'label_id': label['id'],
                        'message': 'Label already exists'
                    }
            
            # Create new label
            label_object = {
                'name': label_name,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }
            
            created_label = self.service.users().labels().create(
                userId='me',
                body=label_object
            ).execute()

            return {
                'status': 'success',
                'label_id': created_label['id'],
                'message': 'Label created successfully'
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }

    def add_label_to_message(self, message_id, label_name):

        try:
            # First ensure label exists
            label_result = self.create_label(label_name)
            if label_result['status'] == 'error':
                return label_result
            
            label_id = label_result['label_id']

            # Modify the message labels
            modified_message = self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={
                    'addLabelIds': [label_id],
                    'removeLabelIds': []
                }
            ).execute()

            return {
                'status': 'success',
                'message_id': modified_message['id'],
                'message': f'Label "{label_name}" added successfully'
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }

    def fetch_thread_ids_by_prev_mins(self, num_prev_mins: int = 3) -> dict:

        try:
            # Validate input
            if not isinstance(num_prev_mins, int) or num_prev_mins <= 0:
                return {
                    'status': 'error',
                    'thread_ids': [],
                    'message': 'Number of previous minutes must be a positive integer'
                }
            
            # Calculate the cutoff datetime
            cutoff_datetime = datetime.now() - timedelta(minutes=num_prev_mins)
            
            # Convert to timestamp in seconds (Unix epoch time)
            cutoff_timestamp = int(cutoff_datetime.timestamp())
            
            thread_ids = []
            page_token = None
            
            while True:
                # Use the 'after:' query to filter threads by timestamp
                query = f'after:{cutoff_timestamp}'
                
                results = self.service.users().threads().list(
                    userId='me', 
                    pageToken=page_token,
                    q=query
                ).execute()
                
                # Extract thread IDs from current page
                current_threads = results.get('threads', [])
                thread_ids.extend(thread['id'] for thread in current_threads)
                
                # Get the next page token
                page_token = results.get('nextPageToken')
                
                # Break the loop if no more pages
                if not page_token:
                    break
            
            return {
                'status': 'success',
                'thread_ids': thread_ids,
                'message': f'Successfully fetched {len(thread_ids)} thread IDs from the last {num_prev_mins} minutes'
            }

        except HttpError as error:
            return {
                'status': 'error',
                'thread_ids': [],
                'message': f'An HTTP error occurred: {error}'
            }
        except Exception as e:
            return {
                'status': 'error',
                'thread_ids': [],
                'message': f'An error occurred: {str(e)}'
            }

    def star_message(self, message_id):

        try:
            # In Gmail, starring a message is equivalent to adding the STARRED system label
            modified_message = self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={
                    'addLabelIds': ['STARRED'],
                    'removeLabelIds': []
                }
            ).execute()

            return {
                'status': 'success',
                'message_id': modified_message['id'],
                'message': 'Message starred successfully'
            }

        except HttpError as error:
            return {
                'status': 'error',
                'message': f'An HTTP error occurred: {error}'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }
