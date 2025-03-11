import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Union
from datetime import datetime, timedelta

# Google API imports
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials as OAuthCredentials
from googleapiclient.errors import HttpError

import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Custom imports
sys.path.append(str(Path(__file__).resolve().parent.parent))
from aws.utils import fetch_tokens

class GmailMessageFetcher:
    
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
    
    def fetch_message_ids_from_thread(self, thread_id: str) -> List[str]:

        # Validate input
        if not thread_id or not isinstance(thread_id, str):
            raise ValueError("Invalid thread ID. Must be a non-empty string.")
        
        try:
            # Ensure authentication
            if not self._service:
                self._authenticate()
            
            # Fetch the specific thread
            thread = self._service.users().threads().get(userId='me', id=thread_id).execute()
            
            # Process thread details
            message_ids = []
            
            # Iterate through messages in the thread
            for message in thread.get('messages', []):
                message_id = message.get('id')
                if message_id:
                    message_ids.append(message_id)
            
            return message_ids
        
        except HttpError as e:
            error_details = {
                'status_code': e.resp.status,
                'reason': e.resp.reason,
                'error_message': str(e)
            }
            print(f"Gmail API Error: {error_details}")
            raise
        except Exception as e:
            print(f"Unexpected error fetching thread messages: {e}")
            raise

    def fetch_message_ids_by_prev_mins(self, num_prev_mins: int = 3) -> List[str]:

        # Validate input
        if not isinstance(num_prev_mins, int) or num_prev_mins <= 0:
            raise ValueError("Number of previous minutes must be a positive integer")

        try:
            # Ensure authentication
            if not self._service:
                self._authenticate()

            # Calculate the cutoff datetime
            cutoff_datetime = datetime.now() - timedelta(minutes=num_prev_mins)
            cutoff_timestamp = int(cutoff_datetime.timestamp())

            message_ids = []
            page_token = None

            while True:
                try:
                    # Use the 'after:' query to filter messages by timestamp
                    query = f'after:{cutoff_timestamp}'
                    
                    results = self._service.users().messages().list(
                        userId='me',
                        pageToken=page_token,
                        q=query
                    ).execute()

                    # Extract message IDs from the current page
                    current_messages = results.get('messages', [])
                    message_ids.extend(message['id'] for message in current_messages)

                    # Get the next page token
                    page_token = results.get('nextPageToken')

                    # Break the loop if no more pages
                    if not page_token:
                        break

                except HttpError as e:
                    error_details = {
                        'status_code': e.resp.status,
                        'reason': e.resp.reason,
                        'error_message': str(e)
                    }
                    print(f"Gmail API Error: {error_details}")
                    raise
                
            return message_ids

        except Exception as e:
            print(f"Unexpected error fetching message IDs: {e}")
            raise
