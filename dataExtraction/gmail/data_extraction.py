import sys
import json
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime
import pytz

import json
from datetime import datetime
from email.utils import parsedate_to_datetime

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from dataExtraction.gmail.thread_id import GmailThreadFetcher
from dataExtraction.gmail.message_ids import GmailMessageFetcher
from dataExtraction.gmail.message_details import GmailMessageDetailsFetcher
from dataExtraction.gmail.message_labels import GmailMessageLabelsFetcher

class GmailDataExtractor:

    def __init__(self, email):
        self.email = email
        self.thread_fetcher = GmailThreadFetcher(email)
        self.message_fetcher = GmailMessageFetcher(email)
        self.detail_fetcher = GmailMessageDetailsFetcher(email)
        self.label_fetcher = GmailMessageLabelsFetcher(email)

    def transform_threads(self, file_path: str) -> None:
    
        # Read the input file
        with open(file_path, 'r', encoding='utf-8') as f:
            threads_data = json.load(f)

        transformed_threads = []
        
        for thread in threads_data:
            if not thread:  # Skip empty threads
                continue
                
            # Sort messages within thread by timestamp
            messages_in_thread = sorted(
                thread,
                key=lambda x: parsedate_to_datetime(x['timestamp']).timestamp()
            )
            
            # Collect all unique labels from messages
            all_labels = set()
            for msg in messages_in_thread:
                all_labels.update(msg.get('label', []))
            
            formatted_messages = []
            for msg in messages_in_thread:
                # Parse the email's timestamp
                dt = parsedate_to_datetime(msg['timestamp'])
                dt = dt.astimezone(pytz.UTC)  # Convert to UTC
                
                formatted_msg = {
                    "message_id": msg['message_id'],
                    "datetime": dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "timestamp": dt.timestamp(),
                    "sender": msg['from']['email'],
                    "receiver": msg['to']['email'],
                    "subject": msg['subject'],
                    "body": msg['body']['plain_text'],
                    "references": [],  # No references in input data
                    "in_reply_to": "",  # No in-reply-to in input data
                    "labels": msg.get('label', [])
                }
                formatted_messages.append(formatted_msg)
            
            thread_data = {
                "thread_id": messages_in_thread[0]['thread_id'],  # Use first message's thread ID
                "total_messages": len(messages_in_thread),
                "labels": list(all_labels),
                "reply_to_message_id": messages_in_thread[-1]['message_id'],  # Last message ID
                "messages": formatted_messages,
                "sort_timestamp": formatted_messages[-1]['timestamp']  # For sorting
            }
            
            transformed_threads.append(thread_data)
        
        # Sort threads by the timestamp of their last message (newest first)
        transformed_threads.sort(
            key=lambda x: x['sort_timestamp'],
            reverse=True
        )
        
        # Remove the temporary sort_timestamp field
        for thread in transformed_threads:
            del thread['sort_timestamp']
        
        # Save the transformed data back to the same file - now just as an array
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(transformed_threads, f, indent=2, ensure_ascii=False)

    def fetch_email_threads_complete(self):
        
        email = self.email
        gmail_thread_id_fetcher = self.thread_fetcher
        gmail_message_id_fetcher = self.message_fetcher
        gmail_message_detail_fetcher = self.detail_fetcher
        gmail_message_label_fetcher = self.label_fetcher

        thread_ids = gmail_thread_id_fetcher.fetch_all_thread_ids()
        # thread_ids = thread_ids[:3] # For Development Environment

        print(f"thread_ids: {thread_ids}")

        threads = []

        for thread_id in thread_ids:

            try:
                message_ids = gmail_message_id_fetcher.fetch_message_ids_from_thread(thread_id)
                thread = []
                
                for message_id in message_ids:
                    
                    try:
                        message = gmail_message_detail_fetcher.fetch_message_details(message_id)

                        _, label = gmail_message_label_fetcher.fetch_labels_from_messageid(message_id)
                        message['label'] = label

                        if 'html_text' in message['body']:
                            message['body'].pop('html_text')

                        thread.append(message)

                    except Exception as e:
                        
                        print(f"Error processing message ID {message_id}: {e}")
                        continue
                
                threads.append(thread)

            except Exception as e:

                print(f"Error processing thread ID {thread_id}: {e}")
                continue

        thread_file_path = f'{email}.json'
        
        with open(thread_file_path, 'w') as json_file:
            json.dump(threads, json_file, indent=2)

        self.transform_threads(thread_file_path)
        
        return thread_file_path
    
    def fetch_email_threads_by_prev_days(self, num_prev_days):
        
        email = self.email
        gmail_thread_id_fetcher = self.thread_fetcher
        gmail_message_id_fetcher = self.message_fetcher
        gmail_message_detail_fetcher = self.detail_fetcher
        gmail_message_label_fetcher = self.label_fetcher

        thread_ids = gmail_thread_id_fetcher.fetch_thread_ids_by_prev_days(num_prev_days)

        print(f"thread_ids: {thread_ids}")

        threads = []

        for thread_id in thread_ids:

            try:
                message_ids = gmail_message_id_fetcher.fetch_message_ids_from_thread(thread_id)
                thread = []
                
                for message_id in message_ids:
                    
                    try:
                        message = gmail_message_detail_fetcher.fetch_message_details(message_id)

                        _, label = gmail_message_label_fetcher.fetch_labels_from_messageid(message_id)
                        message['label'] = label

                        if 'html_text' in message['body']:
                            message['body'].pop('html_text')

                        thread.append(message)

                    except Exception as e:
                        
                        print(f"Error processing message ID {message_id}: {e}")
                        continue
                
                threads.append(thread)

            except Exception as e:

                print(f"Error processing thread ID {thread_id}: {e}")
                continue

        thread_file_path = f'{email}.json'
        
        with open(thread_file_path, 'w') as json_file:
            json.dump(threads, json_file, indent=2)

        self.transform_threads(thread_file_path)
        
        return thread_file_path
    
    def fetch_email_threads(self, num_prev_days: Optional[int] = None):

        try:
            if num_prev_days is None:
                return self.fetch_email_threads_complete()
            else:
                return self.fetch_email_threads_by_prev_days(num_prev_days)
                
        except Exception as e:
            
            print(f"Error fetching email threads: {str(e)}")
            
            # Log additional error details if needed
            print(f"Error type: {type(e).__name__}")
            print(f"Error occurred while fetching {'all threads' if num_prev_days is None else f'threads for past {num_prev_days} days'}")
            
            return []  # Return empty list on error

if __name__ == "__main__":
    # Set up test email address - replace with a test email when running
    test_email = "roysubhradip001@gmail.com"
    
    # Create an instance of the extractor
    extractor = GmailDataExtractor(test_email)
    
    # Test fetching all email threads
    print("Testing fetch_email_threads() with no parameters...")
    result = extractor.fetch_email_threads()
    print(f"Result: {result}")
    
    # # Test fetching email threads for the last 7 days
    # print("\nTesting fetch_email_threads() with num_prev_days=7...")
    # result = extractor.fetch_email_threads(num_prev_days=7)
    # print(f"Result: {result}")
