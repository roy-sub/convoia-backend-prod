import json
import sys
import email
import base64
from pathlib import Path
from typing import Dict, Any, Union

# Google API imports
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials as OAuthCredentials
from googleapiclient.errors import HttpError

# Custom imports
sys.path.append(str(Path(__file__).resolve().parent.parent))
from aws.utils import fetch_tokens

class GmailMessageDetailsFetcher:
    
    def __init__(self, email: str):

        self.email = email
        self._tokens = None
        self._credentials = None
        self._service = None
    
    def _load_credentials(self) -> Dict[str, Any]:

        try:
            credentials_path = Path("credentials/credential_gcp.json")
            with credentials_path.open() as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Credentials file not found at {credentials_path}")
        except json.JSONDecodeError:
            raise json.JSONDecodeError("Invalid JSON in credentials file", "", 0)
    
    def _authenticate(self) -> None:
 
        # Fetch tokens from DynamoDB
        self._tokens = fetch_tokens(self.email)
        
        if not self._tokens:
            raise ValueError(f"No authentication tokens found for {self.email}")
        
        try:
            # Load credentials
            credentials_data = self._load_credentials()
            
            # Initialize credentials
            self._credentials = OAuthCredentials(
                token=self._tokens['access_token'],
                refresh_token=self._tokens['refresh_token'],
                client_id=credentials_data['web']['client_id'],
                client_secret=credentials_data['web']['client_secret'],
                token_uri=credentials_data['web']['token_uri']
            )
            
            # Build Gmail service
            self._service = build('gmail', 'v1', credentials=self._credentials)
        
        except (ValueError, HttpError) as e:
            print(f"Authentication error: {e}")
            raise
    
    def _decode_body(self, payload: Dict[str, Any]) -> Dict[str, str]:

        body_content = {
            'plain_text': '',
            'html_text': ''
        }
        
        try:
            # Handle multipart messages
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        if 'data' in part['body']:
                            body_content['plain_text'] = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    elif part['mimeType'] == 'text/html':
                        if 'data' in part['body']:
                            body_content['html_text'] = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
            
            # Handle single part messages
            elif payload['mimeType'] in ['text/plain', 'text/html']:
                if 'data' in payload['body']:
                    decoded_data = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
                    if payload['mimeType'] == 'text/plain':
                        body_content['plain_text'] = decoded_data
                    else:
                        body_content['html_text'] = decoded_data
            
            return body_content
        except Exception as e:
            print(f"Error decoding message body: {e}")
            return body_content
    
    def _parse_email_header(self, header_value: str) -> Dict[str, str]:

        try:
            name, email_addr = email.utils.parseaddr(header_value)
            return {
                'name': name or email_addr,
                'email': email_addr
            }
        except Exception:
            return {
                'name': header_value,
                'email': header_value
            }
    
    def fetch_message_details(self, message_id: str) -> Dict[str, Any]:

        # Validate input
        if not message_id or not isinstance(message_id, str):
            raise ValueError("Invalid message ID. Must be a non-empty string.")
        
        try:
            # Ensure authentication
            if not self._service:
                self._authenticate()
            
            # Fetch the specific message
            message = self._service.users().messages().get(
                userId='me', 
                id=message_id, 
                format='full'
            ).execute()
            
            # Extract headers
            headers = {header['name']: header['value'] for header in message.get('payload', {}).get('headers', [])}
            
            # Decode body
            body_content = self._decode_body(message['payload'])
            
            # Prepare message details
            message_details = {
                'message_id': message_id,
                'thread_id': message.get('threadId', ''),
                'subject': headers.get('Subject', ''),
                'from': self._parse_email_header(headers.get('From', '')),
                'to': self._parse_email_header(headers.get('To', '')),
                'timestamp': headers.get('Date', ''),
                'body': body_content
            }
            
            return message_details
        
        except HttpError as e:
            error_details = {
                'status_code': e.resp.status,
                'reason': e.resp.reason,
                'error_message': str(e)
            }
            print(f"Gmail API Error: {error_details}")
            raise
        except Exception as e:
            print(f"Unexpected error fetching message details: {e}")
            raise

    def fetch_message_details_condensed(self, message_id: str) -> Dict[str, Union[str, Dict[str, str]]]:

        # Validate input
        if not message_id or not isinstance(message_id, str):
            raise ValueError("Invalid message ID. Must be a non-empty string.")
        
        try:
            # Ensure authentication
            if not self._service:
                self._authenticate()
            
            # Fetch the specific message
            message = self._service.users().messages().get(
                userId='me', 
                id=message_id, 
                format='full'
            ).execute()
            
            # Extract headers
            headers = {
                header['name']: header['value'] 
                for header in message.get('payload', {}).get('headers', [])
            }
            
            # Decode body
            body_content = self._decode_body(message['payload'])
            
            # Return condensed message details
            return {
                'subject': headers.get('Subject', ''),
                'body': body_content
            }
        
        except HttpError as e:
            error_details = {
                'status_code': e.resp.status,
                'reason': e.resp.reason,
                'error_message': str(e)
            }
            print(f"Gmail API Error: {error_details}")
            raise
        except Exception as e:
            print(f"Unexpected error fetching condensed message details: {e}")
            raise

    def fetch_message_essentials(self, message_id: str) -> Dict[str, Union[str, Dict[str, str]]]:

        # Validate input
        if not message_id or not isinstance(message_id, str):
            raise ValueError("Invalid message ID. Must be a non-empty string.")
        
        try:
            # Ensure authentication
            if not self._service:
                self._authenticate()
            
            # Fetch the specific message
            message = self._service.users().messages().get(
                userId='me', 
                id=message_id, 
                format='full'
            ).execute()
            
            # Extract headers
            headers = {
                header['name']: header['value'] 
                for header in message.get('payload', {}).get('headers', [])
            }
            
            # Parse sender's email
            sender_info = self._parse_email_header(headers.get('From', ''))
            
            # Decode body
            body_content = self._decode_body(message['payload'])
            
            # Return essential message details
            return {
                'subject': headers.get('Subject', ''),
                'body': body_content,
                'sender_email': sender_info['email']
            }
        
        except HttpError as e:
            error_details = {
                'status_code': e.resp.status,
                'reason': e.resp.reason,
                'error_message': str(e)
            }
            print(f"Gmail API Error: {error_details}")
            raise
        except Exception as e:
            print(f"Unexpected error fetching message essentials: {e}")
            raise
