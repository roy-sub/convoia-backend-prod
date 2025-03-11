from typing import Dict, Optional
from datetime import datetime, timedelta
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import pytz
from collections import defaultdict
import json
import re
from pathlib import Path

def decode_header_value(header_value: str) -> str:
    try:
        decoded_headers = decode_header(header_value or '')
        decoded_parts = []
        for content, charset in decoded_headers:
            if isinstance(content, bytes):
                decoded_parts.append(content.decode(charset or 'utf-8', errors='replace'))
            else:
                decoded_parts.append(str(content))
        return ' '.join(decoded_parts)
    except Exception as e:
        print(f"Error decoding header: {str(e)}")
        return str(header_value)

def extract_email_address(header: str) -> str:
    try:
        match = re.search(r'<([^>]+)>', header)
        if match:
            return match.group(1)
        else:
            # If no angle brackets, try to find something that looks like an email
            match = re.search(r'[\w\.-]+@[\w\.-]+', header)
            if match:
                return match.group(0)
            return header
    except Exception as e:
        print(f"Error extracting email address: {str(e)}")
        return header

def extract_email_details(email_message) -> Dict:
    try:
        # Parse subject
        subject = decode_header_value(email_message.get("Subject", ""))
        
        # Parse from/to headers and extract just the email addresses
        from_header = decode_header_value(email_message.get("From", ""))
        to_header = decode_header_value(email_message.get("To", ""))
        from_email = extract_email_address(from_header)
        to_email = extract_email_address(to_header)
        
        # Parse date
        date_str = email_message.get("Date")
        if date_str:
            try:
                date = parsedate_to_datetime(date_str)
                date = date.astimezone(pytz.UTC)  # Ensure UTC timezone
            except:
                date = datetime.now(pytz.UTC)
        else:
            date = datetime.now(pytz.UTC)
        
        # Extract body
        body = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode('utf-8', errors='replace')
                            break
                    except:
                        continue
        else:
            try:
                payload = email_message.get_payload(decode=True)
                if payload:
                    body = payload.decode('utf-8', errors='replace')
            except:
                body = email_message.get_payload(decode=False) or ""
        
        # Get labels/flags
        labels = []
        flags = getattr(email_message, 'flags', []) or []
        for flag in flags:
            if isinstance(flag, bytes):
                flag = flag.decode('utf-8', errors='replace')
            labels.append(str(flag))
        
        # Add INBOX or SENT label based on folder
        folder = getattr(email_message, 'folder', '')
        if folder:
            if 'sent' in folder.lower():
                labels.append('SENT')
            elif 'inbox' in folder.lower():
                labels.append('INBOX')
        
        # Creating a structure similar to the first script
        message_details = {
            "message_id": email_message.get("Message-ID", ""),
            "datetime": date.strftime("%Y-%m-%d %H:%M:%S UTC"),  # Standard UTC format
            "timestamp": date.timestamp(),
            "sender": from_email,  # Just the email address
            "receiver": to_email,  # Just the email address
            "subject": subject,
            "body": body,
            "references": [],  # Empty array to match first script
            "in_reply_to": "",  # Empty string to match first script
            "labels": labels
        }
        
        # Get Gmail thread ID if available (X-GM-THRID header)
        thread_id = getattr(email_message, 'thread_id', None)
        if thread_id:
            message_details["thread_id"] = thread_id
            
        return message_details
    except Exception as e:
        print(f"Error extracting email details: {str(e)}")
        return {}

class customEmailDataExtractor:
    
    def __init__(self, email_address: str, password: str, imap_server: str = "imap.gmail.com"):
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server

    def fetch_email_threads_complete(self, output_file: Optional[str] = None) -> str:
        return self._fetch_emails(None, output_file)
    
    def fetch_email_threads_by_prev_days(self, num_prev_days: int, output_file: Optional[str] = None) -> str:
        return self._fetch_emails(num_prev_days, output_file)
    
    def fetch_email_threads(self, num_prev_days: Optional[int] = None, output_file: Optional[str] = None) -> str:
        try:
            if num_prev_days is None:
                return self.fetch_email_threads_complete(output_file)
            else:
                return self.fetch_email_threads_by_prev_days(num_prev_days, output_file)
                
        except Exception as e:
            print(f"Error fetching email threads: {str(e)}")
            
            # Log additional error details if needed
            print(f"Error type: {type(e).__name__}")
            print(f"Error occurred while fetching {'all threads' if num_prev_days is None else f'threads for past {num_prev_days} days'}")
            
            return ""  # Return empty string on error
    
    def _fetch_emails(self, num_prev_days: Optional[int], output_file: Optional[str]) -> str:
        email_address = self.email_address
        password = self.password
        imap_server = self.imap_server
        
        if output_file is None:
            output_file = f"{email_address}.json"
            
        try:
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(imap_server)
            mail.login(email_address, password)
            
            all_emails = []
            
            def fetch_folder_emails(folder_name):
                """Helper function to fetch emails from a specific folder."""
                try:
                    # Handle Gmail's special folder names
                    if '[Gmail]' in folder_name:
                        # Remove any existing quotes
                        folder_name = folder_name.replace('"', '')
                        # Properly quote the entire folder name
                        folder_name = f'"{folder_name}"'
                    elif ' ' in folder_name and not (folder_name.startswith('"') and folder_name.endswith('"')):
                        folder_name = f'"{folder_name}"'

                    status, _ = mail.select(folder_name, readonly=True)
                    if status != 'OK':
                        print(f"Failed to select folder {folder_name}: {status}")
                        return []
                    
                    # Set search criteria
                    if num_prev_days is not None:
                        date_filter = (datetime.now(pytz.UTC) - timedelta(days=num_prev_days))
                        search_criteria = f'SINCE "{date_filter.strftime("%d-%b-%Y")}"'
                    else:
                        search_criteria = "ALL"
                    
                    status, message_numbers = mail.search(None, search_criteria)
                    if status != 'OK':
                        return []
                    
                    folder_emails = []
                    for num in message_numbers[0].split():
                        try:
                            # First, try to get Gmail-specific headers including X-GM-THRID (thread ID)
                            try:
                                if imap_server == "imap.gmail.com":
                                    status, thrid_data = mail.fetch(num, "(X-GM-THRID)")
                                    if status == 'OK' and thrid_data and thrid_data[0]:
                                        # Extract thread ID from the response
                                        thread_id_match = re.search(r'X-GM-THRID\s+([0-9]+)', thrid_data[0].decode('utf-8'))
                                        if thread_id_match:
                                            thread_id = thread_id_match.group(1)
                                        else:
                                            thread_id = None
                            except Exception as e:
                                print(f"Error getting thread ID: {str(e)}")
                                thread_id = None
                                
                            # Get email content - FIX HERE
                            status, msg_data = mail.fetch(num, "(RFC822)")
                            if status != 'OK' or not msg_data or not msg_data[0]:
                                continue
                            
                            # Check the structure of msg_data to ensure we access it correctly
                            if isinstance(msg_data[0], tuple) and len(msg_data[0]) > 1:
                                email_body = msg_data[0][1]
                                if not isinstance(email_body, bytes):
                                    print(f"Email body is not bytes, it's {type(email_body)}")
                                    continue
                                email_message = email.message_from_bytes(email_body)
                            else:
                                print(f"Unexpected msg_data structure: {type(msg_data[0])}")
                                continue
                            
                            email_message.folder = folder_name  # Add folder info
                            
                            # Add thread ID if we found one
                            if thread_id:
                                email_message.thread_id = thread_id
                            
                            # Get flags
                            status, flag_data = mail.fetch(num, "(FLAGS)")
                            if status == 'OK' and flag_data and flag_data[0]:
                                flags_str = flag_data[0].decode('utf-8') if isinstance(flag_data[0], bytes) else str(flag_data[0])
                                email_message.flags = re.findall(r'\(([^)]*)\)', flags_str)
                            
                            email_details = extract_email_details(email_message)
                            if email_details:
                                folder_emails.append(email_details)
                                
                        except Exception as e:
                            print(f"Error processing email {num}: {str(e)}")
                            continue
                    
                    return folder_emails
                except Exception as e:
                    print(f"Error accessing folder {folder_name}: {str(e)}")
                    return []
            
            # Fetch from Sent folder
            print("\nFetching from Sent Mail...")
            sent_folders = ['[Gmail]/Sent Mail', '[Gmail]/Sent', 'Sent', 'Sent Items']
            for folder in sent_folders:
                sent_emails = fetch_folder_emails(folder)
                if sent_emails:
                    print(f"Found {len(sent_emails)} sent emails")
                    all_emails.extend(sent_emails)
                    break
            
            # Fetch from Inbox
            print("\nFetching from Inbox...")
            inbox_emails = fetch_folder_emails('INBOX')
            if inbox_emails:
                print(f"Found {len(inbox_emails)} inbox emails")
                all_emails.extend(inbox_emails)
            
            mail.logout()
            
            # Create a map of thread IDs to messages for Gmail
            thread_map = defaultdict(list)
            for email_data in all_emails:
                if "thread_id" in email_data:
                    thread_map[email_data["thread_id"]].append(email_data)
            
            # If no Gmail thread IDs, reconstruct threads based on subject and references
            if not thread_map:
                print("No Gmail thread IDs found, reconstructing threads...")
                # Try to reconstruct threads based on References and In-Reply-To headers
                msg_id_map = {msg["message_id"]: msg for msg in all_emails if msg["message_id"]}
                reply_map = defaultdict(list)
                
                # Build reply relationships
                for email_data in all_emails:
                    msg_id = email_data.get("message_id")
                    if not msg_id:
                        continue
                        
                    # Find if this message is replying to another
                    in_reply_to = email_data.get("in_reply_to")
                    if in_reply_to and in_reply_to in msg_id_map:
                        reply_map[in_reply_to].append(msg_id)
                    
                    # Check references too
                    for ref in email_data.get("references", []):
                        if ref in msg_id_map:
                            reply_map[ref].append(msg_id)
                
                # If we have reply relationships, use them
                if reply_map:
                    # Find root messages (not replying to anything in our dataset)
                    roots = set()
                    for msg in all_emails:
                        msg_id = msg.get("message_id")
                        if not msg_id:
                            continue
                            
                        # Find if this has a parent in our dataset
                        has_parent = False
                        in_reply_to = msg.get("in_reply_to")
                        if in_reply_to and in_reply_to in msg_id_map:
                            has_parent = True
                            
                        if not has_parent:
                            roots.add(msg_id)
                    
                    # Function to build thread from root
                    processed_msgs = set()
                    def build_thread(root_id, thread_id):
                        if root_id in processed_msgs:
                            return
                        
                        processed_msgs.add(root_id)
                        if root_id in msg_id_map:
                            thread_map[thread_id].append(msg_id_map[root_id])
                            
                        # Add all replies
                        for reply_id in reply_map.get(root_id, []):
                            build_thread(reply_id, thread_id)
                    
                    # Process all roots
                    for root_id in roots:
                        build_thread(root_id, root_id)  # Use root message ID as thread ID
                    
                # If we still don't have threads, fallback to subject-based grouping
                if not thread_map:
                    # Group by normalized subject (remove Re:, Fwd:, etc.)
                    subject_map = defaultdict(list)
                    for email_data in all_emails:
                        normalized_subject = re.sub(r'^(?:Re|Fwd):\s*', '', email_data["subject"], flags=re.IGNORECASE)
                        subject_map[normalized_subject].append(email_data)
                    
                    # Create artificial thread IDs
                    for subject, emails in subject_map.items():
                        thread_id = f"thread_{hash(subject) % 10000000:07d}"
                        for email_data in emails:
                            thread_map[thread_id].append(email_data)
            
            # Format threads to match the first script output
            threads = []
            for thread_id, thread_messages in thread_map.items():
                if not thread_messages:
                    continue
                    
                # Sort messages by timestamp
                thread_messages.sort(key=lambda x: x["timestamp"])
                
                # Collect all unique labels
                all_labels = set()
                for msg in thread_messages:
                    all_labels.update(msg.get("labels", []))
                
                thread_data = {
                    "thread_id": thread_id,
                    "total_messages": len(thread_messages),
                    "labels": list(all_labels),
                    "reply_to_message_id": thread_messages[-1]["message_id"] if thread_messages else None,
                    "messages": thread_messages
                }
                
                # Add a sort timestamp
                thread_data["sort_timestamp"] = thread_messages[-1]["timestamp"] if thread_messages else 0
                
                threads.append(thread_data)
            
            # Sort threads by newest message first
            threads.sort(key=lambda x: x["sort_timestamp"], reverse=True)
            
            # Remove the temporary sort_timestamp field
            for thread in threads:
                if "sort_timestamp" in thread:
                    del thread["sort_timestamp"]
            
            # Save to JSON
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(threads, f, indent=2, ensure_ascii=False)
            
            print(f"\nSuccessfully saved {len(threads)} threads to {output_path.absolute()}")
            return str(output_path.absolute())
        
        except Exception as e:
            print(f"Error: {str(e)}")
            return ""


if __name__ == '__main__':
    # Simple test code
    email_address = "subhraturning@gmail.com"  # Use a different variable name
    password = "iqgh oiay rzfz qqce"   
    
    # Create the fetcher
    fetcher = customEmailDataExtractor(email_address, password)
    
    # Test fetching all emails
    output_path = fetcher.fetch_email_threads()
    print(f"output_path: {output_path}")
    
    # Test fetching emails from the last 7 days
    # output_path = fetcher.fetch_email_threads(num_prev_days=1)
    
    # Test with a specific output file
    # output_path = fetcher.fetch_email_threads(output_file="my_emails.json")
