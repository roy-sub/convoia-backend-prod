import os
import sys
import asyncio
from pathlib import Path
from typing import Optional

# Environment and third-party imports
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, EmailStr

# Add parent directory to system path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Custom imports
from aws.automated_priority_response import ImportantEmailManager
from aws.utils import fetch_tokens, get_user_credentials
from dataExtraction.gmail.message_details import GmailMessageDetailsFetcher
from dataExtraction.gmail.message_ids import GmailMessageFetcher
from email_operations.gmail import GmailAutomation
from services.send_email import EmailGenerator, EmailID_Extractor
from email_operations.custom import EmailClient

class ContactOutput(BaseModel):
    email: EmailStr

class ImportantContactsManager:
    
    def __init__(self):
        pass

    def add_important_contact(self, user_email: str, user_input_text: str) -> bool:

        try:
            namespace = user_email.split('@')[0]
            emailID_extractor = EmailID_Extractor()
            sender_email_id = emailID_extractor.get_email(user_input_text, namespace)

            if sender_email_id:
                important_email_manager = ImportantEmailManager()
                status = important_email_manager.add_sender(user_email, sender_email_id)
                
                if status:
                    return True
                else:
                    False
            else:
                return False

        except Exception as e:
            print(f"Error adding important contact: {str(e)}")
            return False

    def remove_important_contact(self, user_email: str, user_input_text: str) -> bool:

        try:
            namespace = user_email.split('@')[0]
            emailID_extractor = EmailID_Extractor()
            sender_email_id = emailID_extractor.get_email(user_input_text, namespace)

            if sender_email_id:
                important_email_manager = ImportantEmailManager()
                status = important_email_manager.delete_specific_sender(user_email, sender_email_id)
                
                if status:
                    return True
                else:
                    False
            else:
                return False

        except Exception as e:
            print(f"Error adding important contact: {str(e)}")
            return False

class EmailImportanceAnalyzer:

    def __init__(self):
        pass

    def check_keywords(self, text: str, email_id: str) -> bool:

        if not text:
            return False
        
        text = text.lower()

        important_email_manager = ImportantEmailManager()
        important_keywords = important_email_manager.get_keywords_for_email(email_id)
        print(f"\n\nDefault important_keywords : {important_keywords}\n\n")
        important_keywords = [keyword.lower() for keyword in important_keywords]

        return any(keyword in text for keyword in important_keywords)

    def check_sender(self, email_sender: str, email_id: str) -> bool:

        important_email_manager = ImportantEmailManager()
        important_contacts = important_email_manager.get_senders_for_email(email_id)
        print(f"\n\nDefault important_contacts : {important_contacts}\n\n")

        return email_sender.lower() in [contact.lower() for contact in important_contacts]

    async def perform_ai_analysis(self, email_subject: str, email_body_text: str, api_key: Optional[str] = None) -> bool:
        
        try:
            load_dotenv()
            api_key = os.getenv('OPENAI_API_KEY')
            
            final_api_key = api_key
            if not final_api_key:
                raise ValueError("OpenAI API key must be provided")
                
            client = OpenAI(api_key=final_api_key)
            
            system_prompt = """You are an email analyzer that only responds with 'true' or 'false'.
            Respond with 'true' if the email:
            - Requires immediate action
            - Contains critical business information
            - Involves security or legal matters
            - Has high-priority markers"""
            
            cleaned_subject = email_subject.strip() if email_subject else "[No Subject]"
            cleaned_body = email_body_text.strip() if email_body_text else "[Empty Body]"
            
            # Changed from acreate to create
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Subject: {cleaned_subject}\nBody: {cleaned_body}"}
                ],
                temperature=0.0,
                max_tokens=5
            )
            
            result = response.choices[0].message.content.strip().lower()
            return result == 'true'
            
        except Exception as e:
            print(f"AI analysis failed: {str(e)}")
            return False

    async def analyze_email_importance(self, email_sender: str, email_subject: str, email_body_text: str, user_email: str) -> bool:

        if self.check_keywords(email_subject, user_email) or self.check_keywords(email_body_text, user_email):
            return True
            
        elif self.check_sender(email_sender, user_email):
            return True
            
        else:
            return await self.perform_ai_analysis(email_subject, email_body_text)

    async def automated_priority_response_emails(self, user_email: str, num_prev_mins: int = 3) -> bool:
        
        try:
            label_name = "Priority"
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

            email_generator = EmailGenerator()

            if user_details.get('mode') == 'oauth':

                message_fetcher = GmailMessageFetcher(user_email)
                details_fetcher = GmailMessageDetailsFetcher(user_email)
                gmail_automation = GmailAutomation(user_email, refresh_token, access_token)
                
                message_ids = message_fetcher.fetch_message_ids_by_prev_mins(num_prev_mins)
                print(f"\n\nMessage IDs from the past 3 mins: {message_ids}\n\n")

                gmail_automation.create_label(label_name)

                if not message_ids:
                    return True
                
                for message_id in message_ids:
                    try:
                        message_details = details_fetcher.fetch_message_essentials(message_id)
                        
                        message_subject = message_details['subject']
                        message_body = message_details['body'].get('plain_text', '') or message_details['body'].get('html_text', '')
                        sender_email = message_details['sender_email']

                        print(f"\n\nImportant message_subject: {message_subject}\n\nImportant message_body: {message_body}\n\nsender_email: {sender_email}\n\n")
                        
                        is_important = await self.analyze_email_importance(
                            sender_email, 
                            message_subject, 
                            message_body, 
                            user_email
                        )

                        if is_important:
                            print(f"\n\nIMPORTANT EMAIL : {message_id}\n\n")

                            gmail_automation.add_label_to_message(message_id, label_name)
                            gmail_automation.star_message(message_id)

                            ai_input_text = f"""Generate a priority response for this email:
                            
                            Subject: {message_subject}
                            From: {sender_email}
                            
                            Original Message:
                            {message_body}
                            
                            Instructions:
                            - Acknowledge the urgency/importance
                            - Provide a professional and prompt response
                            - Keep it concise but comprehensive
                            - Include relevant details from the original email
                            """

                            email_body = email_generator.generate_body(ai_input_text, namespace)
                            print(f"email_body: {email_body}")
                            
                            if not email_body:
                                print("Error: Could not generate email body")
                                return False
                            
                            gmail_automation.draft_reply(message_id, email_body)

                    except Exception as e:
                        print(f"Error in priority email response monitoring: {e}\n\n{message_id}")
                        continue
                    
                return True

            elif user_details.get('mode') == 'manual':

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

                # Fetch recent message IDs
                message_ids = client.get_recent_message_ids(num_prev_mins)
                print(f"\n\nMessage IDs from the past 3 mins: {message_ids}\n\n")

                client.create_label(label_name)
                
                if not message_ids:
                    return True
                
                for message_id in message_ids:

                    try:
                        
                        # Fetch message details
                        message_details = client.fetch_message_details_condensed(message_id)
                        message_subject = message_details['subject']
                        message_body = message_details['body']
                        sender_email = message_details['sender_email']
                        
                        print(f"\n\nImportant message_subject: {message_subject}\n\nImportant message_body: {message_body}\n\nsender_email: {sender_email}\n\n")
                        
                        is_important = await self.analyze_email_importance(
                            sender_email, 
                            message_subject, 
                            message_body, 
                            user_email
                        )

                        if is_important:
                            print(f"\n\nIMPORTANT EMAIL : {message_id}\n\n")

                            client.add_label_to_email(message_id, label_name)
                            client.mark_as_starred(message_id)

                            ai_input_text = f"""Generate a priority response for this email:
                            
                            Subject: {message_subject}
                            From: {sender_email}
                            
                            Original Message:
                            {message_body}
                            
                            Instructions:
                            - Acknowledge the urgency/importance
                            - Provide a professional and prompt response
                            - Keep it concise but comprehensive
                            - Include relevant details from the original email
                            """

                            email_body = email_generator.generate_body(ai_input_text, namespace)
                            print(f"email_body: {email_body}")
                            
                            if not email_body:
                                print("Error: Could not generate email body")
                                return False
                            
                            client.send_reply(message_id, email_body)

                    except Exception as e:
                        print(f"Error in priority email response monitoring: {e}\n\n{message_id}")
                        continue
                    
                return True
               
            else:
                print(f"Error: Manual mode not yet implemented")
                return True
                
        except Exception as e:
            print(f"Error in priority email response monitoring: {e}")
            return False

# if __name__ == "__main__":
    
#     async def main():
#         email_id = "subhraturning@gmail.com"
#         email_importance_analyzer = EmailImportanceAnalyzer()
#         result = await email_importance_analyzer.automated_priority_response_emails(email_id)
#         print(f"Analysis completed with result: {result}")

#     asyncio.run(main())
