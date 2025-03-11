import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Union

# Google API imports
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials as OAuthCredentials
from googleapiclient.errors import HttpError

# Custom imports
sys.path.append(str(Path(__file__).resolve().parent.parent))
from aws.utils import fetch_tokens

class GmailMessageLabelsFetcher:
    
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
    
    def fetch_labels_from_messageid(self, message_id: str) -> List[str]:

        # Validate input
        if not message_id or not isinstance(message_id, str):
            raise ValueError("Invalid thread ID. Must be a non-empty string.")
        
        try:
            # Ensure authentication
            if not self._service:
                self._authenticate()

            # Fetch the specific message with full details
            message = self._service.users().messages().get(userId='me', id=message_id, format='full').execute()
            
            # Extract and return all available labels
            labels_list = message.get('labelIds', [])
            
            label_ids = []
            label_names = []

            for label_id in labels_list:
                label_info = self._service.users().labels().get(userId='me', id=label_id).execute()

                label_ids.append(label_id)
                label_names.append(label_info.get('name', 'Unknown'))
            
            return label_ids, label_names
        
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
