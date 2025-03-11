import re
import sys
from pathlib import Path
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser

sys.path.append(str(Path(__file__).resolve().parent.parent))

from services.send_email import EmailGenerator
from services.send_reply_helpr import MessageID_Extractor_Manual_Account
from email_operations.gmail import GmailAutomation
from vectorDatabase.pinecone_chatbot_handler import Chatbot
from aws.utils import fetch_tokens
from email_operations.custom import EmailClient

class MessageIDOutput(BaseModel):
    message_id: str = Field(pattern=r'^[0-9a-f]{16}$')

class MessageID_Extractor:
    
    def __init__(self):
        self.chatbot = Chatbot()
        self.parser = PydanticOutputParser(pydantic_object=MessageIDOutput)
        
        # Enhanced search prompt with more specific instructions
        self.search_prompt = """Find the EXACT email being referenced in the following request.

        User Request: {input_text}

        SEARCH INSTRUCTIONS:
        1. First, identify the key search criteria (sender, subject, or content mentioned)
        2. Find the most recent email matching these criteria
        3. Return the COMPLETE email details with message ID
        4. Pay special attention to names, subjects, and any identifying information
        5. Include ALL metadata, especially the message ID (format: 16 hexadecimal characters)

        IMPORTANT:
        - Search thoroughly through recent conversations first
        - Look for exact matches of names and subjects
        - Return the full email content, not just a summary
        - Make sure to include any identifiers or message IDs found

        Return the most relevant email with all its details."""
        
        # More precise extraction prompt
        self.extract_prompt = """Given this email context, extract the message ID.
        The message ID must be a 16-character hexadecimal string (like: 193bf753c6682486).
        
        Email Details:
        {context}
        
        EXTRACTION RULES:
        1. Look for a 16-character hexadecimal ID
        2. Return ONLY the message ID, nothing else
        3. Check thoroughly through all metadata
        4. Ensure the ID belongs to THIS specific email
        5. If found, return ONLY the ID
        6. If not found, return NO_ID_FOUND
        
        Message ID:"""

    def _extract_message_id(self, text: str) -> str:
        """Extract 16-character hexadecimal message ID"""
        pattern = r'[0-9a-f]{16}'
        matches = re.findall(pattern, text.lower())
        # If multiple matches, take the last one as it's more likely to be from recent content
        return matches[-1] if matches else ""

    def get_message_id(self, text: str, namespace: str) -> str:
        
        try:
            # Initial search for the email
            search_response = self.chatbot.get_response(
                self.search_prompt.format(input_text=text),
                namespace
            )
            
            # First attempt to extract message ID
            message_id = self._extract_message_id(search_response)
            if message_id:
                try:
                    parsed = self.parser.parse(f'{{"message_id": "{message_id}"}}')
                    return str(parsed.message_id)
                except:
                    pass
            
            # Second attempt with explicit extraction
            extract_response = self.chatbot.get_response(
                self.extract_prompt.format(context=search_response),
                namespace
            )
            
            # Final attempt to extract and validate
            message_id = self._extract_message_id(extract_response)
            if message_id:
                try:
                    parsed = self.parser.parse(f'{{"message_id": "{message_id}"}}')
                    return str(parsed.message_id)
                except:
                    return ""
            
            return ""

        except Exception as e:
            print(f"Error in get_message_id: {str(e)}")
            return ""

class EmailReplier:

    def __init__(self):
        pass
    
    def send_reply(self, user_email: str, user_input_text: str) -> bool:
        
        try:

            # Validate inputs
            if not user_email or not user_input_text:
                print("Error: Missing required inputs")
                return False
            
            # Getting the Namespace
            namespace = user_email.split('@')[0]
            
            # Get User Details
            user_details = fetch_tokens(user_email)
            
            if not user_details:
                print(f"Error: Could not fetch user details for {user_email}")
                return False
            
            refresh_token = user_details.get('refresh_token')
            access_token = user_details.get('access_token')

            password = user_details.get('password')
            smtp_server = user_details.get('emailServer')
            imap_server = user_details.get('imap_server')

            # Divide Based on User 'Mode'
            if user_details.get('mode') == 'oauth':

                # Get Message_ID
                messageID_extractor = MessageID_Extractor()
                message_id = messageID_extractor.get_message_id(user_input_text, namespace)

                if not message_id:
                    print("Error: Could not determine message_id")
                    return False
                
                # Generate Email Body
                email_generator = EmailGenerator()
                email_body = email_generator.generate_body(user_input_text, namespace)
                
                if not email_body:
                    print("Error: Could not generate email body")
                    return False
                
                # refresh_token = user_details.get('refresh_token')
                # access_token = user_details.get('access_token')

                gmail_automation = GmailAutomation(user_email, refresh_token, access_token)
                result = gmail_automation.draft_reply(message_id, email_body)

                if result and result.get('status') == 'success':
                    return True
                else:
                    print("Error: Failed to create reply draft")
                    return False
            
            elif user_details.get('mode') == 'manual':

                # Get Message_ID
                messageID_extractor = MessageID_Extractor_Manual_Account()
                message_id = messageID_extractor.get_message_id(user_input_text, namespace)

                if not message_id:
                    print("Error: Could not determine message_id")
                    return False

                # Generate Email Body
                email_generator = EmailGenerator()
                email_body = email_generator.generate_body(user_input_text, namespace)
                
                if not email_body:
                    print("Error: Could not generate email body")
                    return False

                smtp_port = 587
                imap_port = 993

                client = EmailClient(
                    email_address=user_email,
                    password=password,
                    smtp_server=smtp_server,
                    imap_server=imap_server,
                    smtp_port=smtp_port,
                    imap_port=imap_port
                )

                result = client.send_reply(
                    message_id=message_id,
                    reply_body=email_body
                )
                
                return result.get('success')
                
            else:
                print("Error: Manual mode not yet implemented")
                return True
        
        except Exception as e:
            print(f"Error in get_message_id: {str(e)}")
            return False

# if __name__ == "__main__":
    
#     user_email = "subhraturning@gmail.com"
#     user_input_text = "Send a reply to the email from Flipkart about answering question regarding products"
#     email_replier = EmailReplier()
#     result = email_replier.send_reply(user_email, user_input_text)
#     print(result)
