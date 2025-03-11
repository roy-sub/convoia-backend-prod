import re
import sys
from pathlib import Path
from pydantic import BaseModel, EmailStr, Field
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser

sys.path.append(str(Path(__file__).resolve().parent.parent))
from vectorDatabase.pinecone_chatbot_handler import Chatbot
from email_operations.gmail import GmailAutomation
from aws.utils import fetch_tokens
from email_operations.custom import EmailClient

class EmailOutput(BaseModel):
    email: EmailStr

class EmailBody(BaseModel):
    body: str = Field(min_length=1)

class EmailSubject(BaseModel):
    subject: str = Field(min_length=1, max_length=100)

class EmailID_Extractor:
    
    def __init__(self):
        
        self.chatbot = Chatbot()
        self.parser = PydanticOutputParser(pydantic_object=EmailOutput)
        
        # First prompt to get context with email
        self.context_prompt = """Find the exact email address for the person mentioned in this text by searching through the conversation history. 
        First find the most relevant conversation mentioning this person, then locate their exact email address.
        
        MUST extract email address from historical conversations - do not generate or guess emails.
        Only respond with the exact email address found in the conversations. 
        If multiple emails are found, choose the most recently used one.
        
        Input: {input_text}"""

        # Second prompt to ensure valid email output
        self.email_prompt = """Given this context and email information, output ONLY a valid email address in the required format.
        If no valid email is found, output 'user@example.com' as a fallback.

        Context: {context}
        Required format: {format_instructions}"""

    def _extract_email(self, text: str) -> str:

        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        matches = re.findall(email_pattern, text)
        return matches[0] if matches else ""

    def _direct_email_check(self, text: str) -> str:

        email = self._extract_email(text)
        if email:
            try:
                # Validate using our parser
                parsed = self.parser.parse(f'{{"email": "{email}"}}')
                return str(parsed.email)
            except:
                return ""
        return ""

    def get_email(self, text: str, namespace: str) -> str:
        
        try:
            # First check for direct email in input
            direct_email = self._direct_email_check(text)
            if direct_email:
                return direct_email

            # Get context with email information
            context_response = self.chatbot.get_response(self.context_prompt.format(input_text=text), namespace)
            
            # Extract email from context response
            email_from_context = self._extract_email(context_response)
            if email_from_context:
                try:
                    parsed = self.parser.parse(f'{{"email": "{email_from_context}"}}')
                    return str(parsed.email)
                except:
                    pass

            # If no valid email found yet, try one more time with structured prompt
            email_prompt = PromptTemplate(
                template=self.email_prompt,
                input_variables=["context"],
                partial_variables={"format_instructions": self.parser.get_format_instructions()}
            )
            
            final_response = self.chatbot.get_response(
                email_prompt.format(context=context_response), 
                namespace
            )
            
            # Final attempt to extract and validate email
            email_from_final = self._extract_email(final_response)
            
            if email_from_final:
                try:
                    parsed = self.parser.parse(f'{{"email": "{email_from_final}"}}')
                    return str(parsed.email)
                except:
                    return ""
                    
            return ""

        except Exception as e:
            print(f"Error in get_email: {str(e)}")
            return ""

class EmailGenerator:
    
    def __init__(self):
        
        self.chatbot = Chatbot()
        self.body_parser = PydanticOutputParser(pydantic_object=EmailBody)
        self.subject_parser = PydanticOutputParser(pydantic_object=EmailSubject)
        
        # Prompt for generating just the email body
        self.body_prompt = """Generate the body of an email based on this request. Use the conversation history for context and tone.

        IMPORTANT INSTRUCTIONS:
        1. Generate ONLY the email body content
        2. Match the writing style from previous emails
        3. Include relevant context from past conversations if helpful
        4. Use clear paragraphs with proper line breaks
        5. Do not include any greetings, signatures, subject lines, or headers
        6. Output only the email body paragraphs

        User Request: {input_text}

        Return the email body in this format: {format_instructions}"""

        # Prompt for generating just the subject
        self.subject_prompt = """Create a subject line for this email body.

        RULES:
        1. Return ONLY the subject line
        2. Make it clear and specific
        3. Keep it under 100 characters
        4. No punctuation at the end
        5. Do not include any other text or explanation

        Email Body:
        {email_body}

        Return the subject in this format: {format_instructions}"""

    def generate_body(self, text: str, namespace: str) -> str:

        try:
            # Create body prompt
            body_prompt = PromptTemplate(
                template=self.body_prompt,
                input_variables=["input_text"],
                partial_variables={"format_instructions": self.body_parser.get_format_instructions()}
            )
            
            # Get response from chatbot
            response = self.chatbot.get_response(
                body_prompt.format(input_text=text),
                namespace
            )
            
            # Parse and validate the response
            parsed = self.body_parser.parse(response)
            return parsed.body.strip()
            
        except Exception as e:
            print(f"Error generating email body: {str(e)}")
            return ""

    def generate_subject(self, body: str, namespace: str) -> str:

        try:
            # Create subject prompt
            subject_prompt = PromptTemplate(
                template=self.subject_prompt,
                input_variables=["email_body"],
                partial_variables={"format_instructions": self.subject_parser.get_format_instructions()}
            )
            
            # Get response from chatbot
            response = self.chatbot.get_response(
                subject_prompt.format(email_body=body),
                namespace
            )
            
            # Parse and validate the response
            parsed = self.subject_parser.parse(response)
            return parsed.subject.strip()
            
        except Exception as e:
            print(f"Error generating subject: {str(e)}")
            return ""

class EmailSender:

    def __init__(self):
        pass
    
    def send_email(self, user_email: str, user_input_text: str) -> bool:
        
        try:
            # print(f"\n\n In function send_email \n\n")
            # Validate inputs
            if not user_email or not user_input_text:
                print("Error: Missing required inputs")
                return False
            
            # Getting the Namespace
            namespace = user_email.split('@')[0]

            # Get To_Email_ID
            emailID_extractor = EmailID_Extractor()
            to_email = emailID_extractor.get_email(user_input_text, namespace)
            # print(f"\nto_email: {to_email}\n")
            if not to_email:
                print("Error: Could not determine recipient email")
                return False

            # Generate Email Body
            email_generator = EmailGenerator()
            email_body = email_generator.generate_body(user_input_text, namespace)
            # print(f"\nemail_body: {email_body}\n")
            if not email_body:
                print("Error: Could not generate email body")
                return False

            # Generate Subject
            email_subject = email_generator.generate_subject(email_body, namespace)
            # print(f"\nemail_subject: {email_subject}\n")
            if not email_subject:
                print("Error: Could not generate email subject")
                return False

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
                
                # refresh_token = user_details.get('refresh_token')
                # access_token = user_details.get('access_token')

                gmail_automation = GmailAutomation(user_email, refresh_token, access_token)
                result = gmail_automation.create_draft(to_email, email_subject, email_body)

                if result and result.get('status') == 'success':
                    return True
                else:
                    print("Error: Failed to create email draft")
                    return False
            
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

                result = client.send_email(
                    receiver_email=to_email,
                    subject=email_subject,
                    body=email_body
                )
                
                return result.get('success')

            else:
                print("Mode not identified")
                return True
        
        except Exception as e:
            print(f"Error generating subject: {str(e)}")
            return False

# if __name__ == "__main__":
    
#     user_email = "subhraturning@gmail.com"
    
#     # user_details = fetch_tokens(user_email)
#     # print(f"\nuser_details: {user_details}\n")
    
#     user_input_text = "Send an email to subhrastien@gmail.com about the project updates and next steps we discussed in our last meeting"
#     email_sender = EmailSender()
#     result = email_sender.send_email(user_email, user_input_text)
#     print(result)
