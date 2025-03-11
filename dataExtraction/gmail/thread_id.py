import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Google API imports
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials as OAuthCredentials
from googleapiclient.errors import HttpError

# Add the root directory to the Python path
root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root_dir))

# Now import aws module
from aws.utils import fetch_tokens

class GmailThreadFetcher:
    
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
            raise json.JSONDecodeError("Invalid JSON in credentials file")
    
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
    
    def fetch_all_thread_ids(self) -> List[str]:

        try:
            # Ensure authentication
            if not self._service:
                self._authenticate()
            
            thread_ids = []
            page_token = None
            
            while True:
                # Retrieve threads with pagination
                results = self._service.users().threads().list(
                    userId='me', 
                    pageToken=page_token
                ).execute()
                
                # Extract thread IDs from current page
                current_thread_ids = [thread['id'] for thread in results.get('threads', [])]
                thread_ids.extend(current_thread_ids)
                
                # Get the next page token
                page_token = results.get('nextPageToken')
                
                # Break the loop if no more pages
                if not page_token:
                    break
            
            print(f"Total number of thread IDs: {len(thread_ids)}")
            return thread_ids
        
        except HttpError as e:
            print(f"Gmail API error: {e}")
            raise
        except Exception as e:
            print(f"Unexpected error fetching thread IDs: {e}")
            raise
    
    def fetch_thread_ids_by_prev_days(self, num_prev_days: int) -> List[str]:

        # Validate input
        if not isinstance(num_prev_days, int) or num_prev_days <= 0:
            raise ValueError("Number of previous days must be a positive integer")
        
        try:
            # Ensure authentication
            if not self._service:
                self._authenticate()
            
            # Calculate the cutoff date in the format Gmail API expects (YYYY/MM/DD)
            cutoff_date = (datetime.now() - timedelta(days=num_prev_days)).strftime('%Y/%m/%d')
            
            thread_ids = []
            page_token = None
            
            while True:
                # Use the 'after:' query to filter threads by date
                results = self._service.users().threads().list(
                    userId='me', 
                    pageToken=page_token,
                    q=f'after:{cutoff_date}'  # This filters threads newer than the cutoff date
                ).execute()
                
                # Extract thread IDs from current page
                current_thread_ids = [thread['id'] for thread in results.get('threads', [])]
                thread_ids.extend(current_thread_ids)
                
                # Get the next page token
                page_token = results.get('nextPageToken')
                
                # Break the loop if no more pages
                if not page_token:
                    break
            
            print(f"Total number of thread IDs in the last {num_prev_days} days: {len(thread_ids)}")
            return thread_ids
        
        except HttpError as e:
            print(f"Gmail API error: {e}")
            raise
        except Exception as e:
            print(f"Unexpected error fetching thread IDs: {e}")
            raise
