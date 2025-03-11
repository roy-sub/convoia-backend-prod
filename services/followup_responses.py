import os
import sys
import json
from pathlib import Path
from typing import Optional, Tuple
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain.output_parsers import BooleanOutputParser
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate

sys.path.append(str(Path(__file__).resolve().parent.parent))

from aws.utils import fetch_tokens
from email_operations.gmail import GmailAutomation
from vectorDatabase.pinecone_chatbot_handler import Chatbot
from dataExtraction.gmail.data_extraction import GmailDataExtractor

# Load OpenAI API key from .env file
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

class FollowUpError(Exception):
    pass

class ThreadProcessingError(FollowUpError):
    pass

class FollowUpConfig(BaseModel):

    label_name: str = Field(default="Follow Up")
    num_prev_days: int = Field(default=3, ge=1, le=30)
    model_name: str = Field(default="gpt-3.5-turbo")
    temperature: float = Field(default=0.0, ge=0.0, le=1.0)

class EmailBody(BaseModel):

    body: str = Field(
        min_length=1,
        max_length=10000,
        description="The follow-up email body text",
        examples=["Thank you for your response. Regarding your question about..."]
    )
    
    class Config:
        
        json_schema_extra = {
            "examples": [
                {
                    "body": "Thank you for your email. I wanted to follow up on..."
                }
            ]
        }

class FollowUpGenerator:
    
    def __init__(self):
        
        self.chatbot = Chatbot()
        self.parser = PydanticOutputParser(pydantic_object=EmailBody)
        
        self.followup_prompt = """Generate a professional follow-up email based on this thread.

        CRITICAL INSTRUCTIONS:
        1. Generate ONLY the email body content
        2. Must be relevant to the thread's context
        3. Address any pending points from previous messages
        4. Keep a professional but consistent tone
        5. Do not include any greetings, signatures, or subject lines
        6. Return only the body text, nothing else
        
        THREAD CONTENT:
        {thread_content}
        
        Return the email body in this format: {format_instructions}"""

    def create_followup_message(self, formatted_thread: str) -> str:

        try:
            prompt = PromptTemplate(
                template=self.followup_prompt,
                input_variables=["thread_content"],
                partial_variables={"format_instructions": self.parser.get_format_instructions()}
            )
            
            response = self.chatbot.get_response(
                prompt.format(thread_content=formatted_thread),
                "followup"
            )
            
            parsed = self.parser.parse(response)
            return parsed.body.strip()
            
        except Exception as e:
            print(f"Error generating follow-up message: {str(e)}")
            return ""

class SingleThreadProcessor:

    def analyze_email_thread(self, formatted_thread: str) -> bool:

        try:
            
            llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.0
            )
            
            output_parser = BooleanOutputParser()

            prompt_template = ChatPromptTemplate(
                
                messages=[
                    HumanMessagePromptTemplate.from_template(
                        """Analyze this email thread and determine if it requires follow-up.
                        
                        RULES:
                        1. Return TRUE if:
                        - There are unanswered questions
                        - There are pending requests
                        - The last message expects a response
                        - There are unresolved issues
                        
                        2. Return FALSE if:
                        - All queries are answered
                        - The conversation is concluded
                        - No response is expected
                        - The thread is complete
                        
                        IMPORTANT: Reply ONLY with 'true' or 'false'
                        
                        EMAIL THREAD:
                        {thread_content}
                        """
                    )
                ]
            )

            prompt = prompt_template.format_messages(thread_content=formatted_thread)
            response = llm.invoke(prompt).content.strip().lower()
            
            return output_parser.parse(response)

        except Exception as e:
            print(f"Error analyzing thread: {str(e)}")
            return False
    
    def format_message(self, message: dict, message_number: int) -> str:

        try:
            
            formatted = []
            formatted.append(f"MESSAGE {message_number}")
            formatted.append(f"Subject: {message['subject']}")
            formatted.append("")
            formatted.append("BODY:")
            formatted.append(message['body'])
            
            return "\n".join(formatted)
        
        except Exception as e:
            print(f"Error formatting message: {str(e)}")
            return ""

    def format_thread(self, thread: dict) -> str:

        try:
            formatted = []
            formatted.append("=" * 58)
            formatted.append(f"THREAD ID: {thread['thread_id']}")
            formatted.append(f"Total Messages: {thread['total_messages']}")
            
            for i, message in enumerate(thread['messages'], 1):
                formatted.append("-" * 58)
                formatted.append("")
                formatted.append(self.format_message(message, i))
                formatted.append("")
            
            formatted.append("=" * 58)
            return "\n".join(formatted)
        
        except Exception as e:
            print(f"Error formatting thread: {str(e)}")
            return ""

class FollowUpEmailMonitor:
   
    def __init__(self, config: Optional[FollowUpConfig] = None):

        self.config = config or FollowUpConfig()
        self.processor = SingleThreadProcessor()
        self.generator = FollowUpGenerator()
   
    def _setup_gmail_automation(self, user_email: str, user_details: dict) -> Optional[GmailAutomation]:

        try:
            
            refresh_token = user_details.get('refresh_token')
            access_token = user_details.get('access_token')
            return GmailAutomation(user_email, refresh_token, access_token)
        
        except Exception as e:
            
            print(f"Error setting up Gmail automation: {str(e)}")
            return None

    def _process_single_thread(self, thread: dict, gmail_automation: GmailAutomation) -> bool:

        try:
            
            message_id = thread['reply_to_message_id']
            formatted_thread = self.processor.format_thread(thread)
            
            if self.processor.analyze_email_thread(formatted_thread):
                
                followup_message = self.generator.create_followup_message(formatted_thread)
                gmail_automation.create_label(self.config.label_name)
                gmail_automation.add_label_to_message(message_id, self.config.label_name)
                return gmail_automation.draft_reply(message_id, followup_message)
            
            return False
        
        except Exception as e:
            print(f"Error processing thread: {str(e)}")
            return False

    def monitor_followup_emails(self, user_email: str, num_prev_days: Optional[int] = None) -> bool:

        try:
            
            user_details = fetch_tokens(user_email)
            if not user_details:
                raise FollowUpError("Could not fetch user details")

            mode = user_details.get('mode')
            
            # Handle OAuth mode
            if mode == 'oauth':
                gmail_automation = self._setup_gmail_automation(user_email, user_details)
                if not gmail_automation:
                    raise FollowUpError("Failed to setup Gmail automation")

                extractor = GmailDataExtractor(user_email)
                json_file_path = extractor.fetch_email_threads(
                    num_prev_days or self.config.num_prev_days
                )

                with open(json_file_path, 'r', encoding='utf-8') as file:
                    threads = json.load(file)
                    
                for thread in threads:
                    if self._process_single_thread(thread, gmail_automation):
                        return True
                return False
                
            # Handle Manual mode
            elif mode == 'manual':
                print(f"Processing {user_email} using manual mode")
                from services.followup_responses_helper import ManualFollowUpEmailHandler
                
                manual_handler = ManualFollowUpEmailHandler(self.config)
                return manual_handler.process_manual_followup(user_email, num_prev_days)
                
            # Unsupported mode
            else:
                raise FollowUpError(f"Unsupported authentication mode: {mode}")

        except FollowUpError as e:
            print(f"Follow-up error: {str(e)}")
            return False
        
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return False

class EmailFollowUpService:
    
    async def initiate_followup_email(email_id: str, label_name: str = "Follow Up", num_prev_days: int = 3) -> bool:

        try:
            # Create config and monitor
            config = FollowUpConfig(label_name=label_name, num_prev_days=num_prev_days)
            monitor = FollowUpEmailMonitor(config)
            
            # Run the monitoring process
            return monitor.monitor_followup_emails(email_id)
            
        except Exception as e:
            print(f"Error processing follow-up emails: {str(e)}")
            return False

# if __name__ == "__main__":
#     config = FollowUpConfig(label_name="Follow Up", num_prev_days=3)
#     monitor = FollowUpEmailMonitor(config)
#     monitor.monitor_followup_emails("roysubhradip001@gmail.com")
