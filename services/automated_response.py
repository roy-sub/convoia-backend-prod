import asyncio
import os
import sys
from pathlib import Path
from typing import Dict

# Pydantic imports
from pydantic import BaseModel, Field

# OpenAI and LangChain imports
import openai
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain_openai import ChatOpenAI

# Add parent directory to system path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Custom imports
from aws.automated_response import AutomatedResponseManager
from aws.utils import fetch_tokens, get_user_credentials
from email_operations.gmail import GmailAutomation
from dataExtraction.gmail.message_details import GmailMessageDetailsFetcher
from dataExtraction.gmail.message_ids import GmailMessageFetcher
from email_operations.custom import EmailClient

from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()

# Get the OpenAI API key from the environment variables
openai_api_key = os.getenv('OPENAI_API_KEY')

class AutoResponseConfig(BaseModel):
    
    category: str = Field(
        min_length=1,
        max_length=100,
        description="The category of the email type"
    )
    description: str = Field(
        min_length=1,
        max_length=200,
        description="Brief description of the email type"
    )
    response_directive: str = Field(
        min_length=1,
        description="Template or directive for automated response"
    )

class CategoryOutput(BaseModel):
    category: str = Field(
        min_length=1,
        description="The category name to be removed"
    )

class AutoResponseCategoryExtractor:
    
    def __init__(self):
        
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0,
            api_key=openai_api_key
        )
        self.parser = PydanticOutputParser(pydantic_object=AutoResponseConfig)
        
        self.extract_prompt = """Analyze the following request to enable automated email responses and extract the category, description, and response directive.

        CRITICAL INSTRUCTIONS:
        1. Extract or determine an appropriate category name (like "Meeting Confirmation", "Order Updates", etc.)
        2. Generate a clear description of when this automation should trigger
        3. Either extract the provided response directive or generate an appropriate one
        4. Format must match exactly as shown in the examples
        5. Return ONLY the JSON object, no additional text

        EXAMPLES:
        Input: "Set up automatic replies for meeting confirmation emails"
        Output:
        {{"category": "Meeting Confirmation", "description": "Meeting confirmation or details of a scheduled meeting.", "response_directive": "Thank you for confirming the meeting. We look forward to connecting on <meeting_date>."}}

        Input: "Enable auto-responses for delivery status emails"
        Output:
        {{"category": "Delivery Updates", "description": "Delivery status updates for shipments or parcels.", "response_directive": "Thank you for the update regarding the delivery of <relevant item details>."}}

        Current Request: {input_text}
        
        Return ONLY a JSON object in this format: {format_instructions}"""

    def extract_config(self, text: str) -> dict:

        try:
            # Create prompt with format instructions
            extract_prompt = PromptTemplate(
                template=self.extract_prompt,
                input_variables=["input_text"],
                partial_variables={"format_instructions": self.parser.get_format_instructions()}
            )
            
            # Get formatted prompt
            formatted_prompt = extract_prompt.format(input_text=text)
            
            # Get response from GPT-3.5
            messages = [{"role": "user", "content": formatted_prompt}]
            response = self.llm.invoke(formatted_prompt).content
            
            # Parse and validate the response
            parsed = self.parser.parse(response)
            
            return {
                "category": parsed.category,
                "description": parsed.description,
                "response_directive": parsed.response_directive
            }
            
        except Exception as e:
            print(f"Error extracting auto-response config: {str(e)}")
            return {
                "category": "",
                "description": "",
                "response_directive": ""
            }

    def extract_category_for_removal(self, text: str, email_id: str) -> str:
 
        try:

            available_categories = AutomatedResponseManager().get_categories_for_email(email_id)

            category_parser = PydanticOutputParser(pydantic_object=CategoryOutput)
            
            removal_prompt = """Extract ONLY the category name from this automated response removal request.

            CRITICAL INSTRUCTIONS:
            1. Return ONLY the exact category name that matches one from the available categories
            2. Must return in the specified JSON format
            3. Match with the closest available category
            4. If no match found, return the closest match from available categories

            Available Categories:
            {categories}

            EXAMPLES:
            Input: "Remove automated responses for meeting confirmations"
            Output: {{"category": "meeting confirmation"}}

            Input: "Disable auto-replies for Order Updates"
            Output: {{"category": "order updates"}}

            Current Request: {input_text}
            
            Return the category in this format: {format_instructions}"""

            # Create prompt template
            prompt = PromptTemplate(
                template=removal_prompt,
                input_variables=["input_text", "categories"],
                partial_variables={"format_instructions": category_parser.get_format_instructions()}
            )
            
            # Get formatted prompt
            formatted_prompt = prompt.format(
                input_text=text,
                categories=', '.join(available_categories)
            )
            
            # Get response from GPT-3.5
            response = self.llm.invoke(formatted_prompt).content
            
            # Parse and validate response
            parsed = category_parser.parse(response)
            category = parsed.category.strip().lower()
            
            # Validate against available categories
            if category in [cat.lower() for cat in available_categories]:
                return category
            return ""
                
        except Exception as e:
            print(f"Error extracting category for removal: {str(e)}")
            return ""

class AutomatedResponseCategoryManager:
    
    def __init__(self):
        pass

    def add_categories_to_automated_responses(self, user_email: str, user_input_text: str) -> bool:
        try:
            auto_response_category_extractor = AutoResponseCategoryExtractor()
            config = auto_response_category_extractor.extract_config(user_input_text)
            category = config['category']
            description = config['description']
            response_directive = config['response_directive']
            automated_response_manager = AutomatedResponseManager()
            status = automated_response_manager.add_category_to_automated_response(user_email, category, description, response_directive)
            return status
        except Exception as e:
            print(f"Error adding important contact: {str(e)}")
            return False
    
    def remove_categories_from_automated_responses(self, user_email: str, user_input_text: str) -> bool:
        try:
            auto_response_category_extractor = AutoResponseCategoryExtractor()
            category = auto_response_category_extractor.extract_category_for_removal(user_input_text, user_email)
            automated_response_manager = AutomatedResponseManager()
            status = automated_response_manager.delete_specific_category(user_email, category) 
            return status
        except Exception as e:
            print(f"Error adding important contact: {str(e)}")
            return False

class CategoryResponse(BaseModel):

    category: str = Field(
        description="The matching category name or empty string if no match",
        default=""
    )

class ResponseOutput(BaseModel):

    response: str = Field(
        description="The generated email response",
        default=""
    )

class AutomatedResponseMonitor:
    
    def __init__(self):

        try:
            self.openai_api_key = os.environ.get('OPENAI_API_KEY')
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            
            # Initialize OpenAI client
            openai.api_key = self.openai_api_key
            
            # Initialize output parser with Pydantic model
            self.output_parser = PydanticOutputParser(pydantic_object=CategoryResponse)
            
            # Initialize LangChain chat model
            self.chat_model = ChatOpenAI(
                model_name="gpt-3.5-turbo",
                temperature=0,
                max_tokens=50
            )
            
            # Get the format instructions
            format_instructions = self.output_parser.get_format_instructions()
            
            # Create prompt template with format instructions
            self.prompt_template = ChatPromptTemplate.from_messages([
                ("system", """You are an email categorization system. Your task is to determine if an email matches any of the provided categories.
                Rules:
                - If the email matches a category, output the exact category name
                - If no match is found, output an empty string
                - You must follow the exact output format specified
                - Be strict in matching - only return a category if the email clearly belongs to it
                
                {format_instructions}"""),
                ("user", """Categories and Descriptions:
                {categories_dict}
                
                Email Content:
                {email_content}
                
                Determine the category:""")
            ])
            
        except Exception as e:
            print(f"Error initializing AutomatedResponseMonitor: {e}")
            raise
    
    async def _generate_email_response(self, response_format: str, message_subject: str, message_body: str, max_retries: int = 3) -> str:

        try:
            # Initialize output parser with Pydantic model
            output_parser = PydanticOutputParser(pydantic_object=ResponseOutput)
            
            # Create prompt template
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", """You are an email response generator. Generate a brief, professional response using the provided template.
                Rules:
                - Use the response template as a guide but personalize it based on the email content
                - Keep the response concise and professional
                - Include relevant details from the original email
                - Output only the response text, no additional text or explanations
                
                {format_instructions}"""),
                ("user", """Response Template:
                {response_format}
                
                Original Email Subject: {message_subject}
                
                Original Email Body:
                {message_body}
                
                Generate response:""")
            ])
            
            # Initialize chat model
            chat_model = ChatOpenAI(
                model_name="gpt-3.5-turbo",
                temperature=0.7,  # Slightly higher for more natural responses
                max_tokens=150    # Limit response length
            )
            
            # Create chain
            chain = prompt_template | chat_model | output_parser
            
            retry_count = 0
            while retry_count < max_retries:
                try:
                    # Execute chain
                    result = await chain.ainvoke({
                        "response_format": response_format,
                        "message_subject": message_subject,
                        "message_body": message_body,
                        "format_instructions": output_parser.get_format_instructions()
                    })
                    
                    # Return the generated response
                    return result.response
                    
                except Exception as e:
                    print(f"Response generation attempt {retry_count + 1} failed: {e}")
                    retry_count += 1
                    if retry_count == max_retries:
                        raise
            
            return ""  # Return empty string if all retries failed
            
        except Exception as e:
            print(f"Error generating email response: {e}")
            return ""

    async def _determine_email_category(self, categories_dict: Dict[str, str], email_content: str, max_retries: int = 3) -> str:

        try:
            # Format categories for prompt
            categories_formatted = "\n".join(
                f"- {category}: {description}" 
                for category, description in categories_dict.items()
            )
            
            # Create chain with structured output parsing
            chain = self.prompt_template | self.chat_model | self.output_parser
            
            retry_count = 0
            while retry_count < max_retries:
                try:
                    # Execute chain with format instructions
                    result = await chain.ainvoke({
                        "categories_dict": categories_formatted,
                        "email_content": email_content,
                        "format_instructions": self.output_parser.get_format_instructions()
                    })
                    
                    if result.category in categories_dict or result.category == "":
                        return result.category
                    
                    # If result is invalid, retry
                    retry_count += 1
                    
                except Exception as e:
                    print(f"API call attempt {retry_count + 1} failed: {e}")
                    retry_count += 1
                    if retry_count == max_retries:
                        raise
                    
            return ""  # Return empty string if all retries failed
            
        except Exception as e:
            print(f"Error in email categorization: {e}")
            return ""

    async def automated_emails_responses(self, user_email: str, num_prev_mins: int = 3 )  -> bool:

        print(f"\nEntered the Function : user_email : {user_email} & num_prev_mins: {num_prev_mins}\n")

        try:
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

            # Process based on user mode
            if user_details.get('mode') == 'oauth':
                
                # Initialize necessary components
                message_fetcher = GmailMessageFetcher(user_email)
                details_fetcher = GmailMessageDetailsFetcher(user_email)
                response_manager = AutomatedResponseManager()
                
                # Fetch recent message IDs
                message_ids = message_fetcher.fetch_message_ids_by_prev_mins(num_prev_mins)
                print(f"\n\nMessage IDs from the past 3 mins: {message_ids}\n\n")

                if not message_ids:
                    return True
                
                # Get categories
                categories_dict = response_manager.get_categories_with_descriptions(user_email)
                response_dict = response_manager.get_categories_with_response_directive(user_email)

                print(f"\n\ncategories_dict: {categories_dict}\n\nresponse_dict: {response_dict}\n\n")
                
                if not categories_dict:
                    print(f"Error: No categories found for {user_email}")
                    return False
                
                for message_id in message_ids:
                    
                    try:
                        
                        # Fetch message details
                        message_details = details_fetcher.fetch_message_details_condensed(message_id)
                        message_subject = message_details['subject']
                        message_body = message_details['body'].get('plain_text', '') or message_details['body'].get('html_text', '')
                        
                        print(f"\n\nmessage_subject: {message_subject}\n\nmessage_body: {message_body}\n\n")
                        # Format email content
                        email_content = f"""Subject: {message_subject}

                        Body:
                        {message_body}"""

                        print(f"\n\nemail_content: {email_content}\n\n")
                        
                        # Determine category
                        matching_category = await self._determine_email_category(
                            categories_dict, 
                            email_content
                        )

                        matching_category = matching_category.strip()

                        print(f"\n\nmatching_category: {matching_category}\n\n")
                        
                        if matching_category in categories_dict:
                            
                            response_format = response_dict[matching_category]
                            print(f"\n\nresponse_format: {response_format}\n\n")
                            email_body = await self._generate_email_response(response_format, message_subject, message_body)
                            print(f"\n\nemail_body: {email_body}\n\n")
                            gmail_automation = GmailAutomation(user_email, refresh_token, access_token)
                            result = gmail_automation.draft_reply(message_id, email_body)
                            print(f"\n\nresult: {result}\n\n")
                            
                    except Exception as e:
                        print(f"Error processing message {message_id}: {e}")
                        pass
                
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
                
                if not message_ids:
                    return True
                
                # Get categories
                response_manager = AutomatedResponseManager()
                categories_dict = response_manager.get_categories_with_descriptions(user_email)
                response_dict = response_manager.get_categories_with_response_directive(user_email)

                print(f"\n\ncategories_dict: {categories_dict}\n\nresponse_dict: {response_dict}\n\n")
                
                if not categories_dict:
                    print(f"Error: No categories found for {user_email}")
                    return False
                
                for message_id in message_ids:

                    try:
                        
                        # Fetch message details
                        message_details = client.fetch_message_details_condensed(message_id)
                        message_subject = message_details['subject']
                        message_body = message_details['body']
                        
                        print(f"\n\nmessage_subject: {message_subject}\n\nmessage_body: {message_body}\n\n")
                        # Format email content
                        email_content = f"""Subject: {message_subject}

                        Body:
                        {message_body}"""

                        print(f"\n\nemail_content: {email_content}\n\n")
                        
                        # Determine category
                        matching_category = await self._determine_email_category(
                            categories_dict, 
                            email_content
                        )

                        matching_category = matching_category.strip()

                        print(f"\n\nmatching_category: {matching_category}\n\n")
                        
                        if matching_category in categories_dict:
                            
                            response_format = response_dict[matching_category]
                            print(f"\n\nresponse_format: {response_format}\n\n")
                            email_body = await self._generate_email_response(response_format, message_subject, message_body)
                            print(f"\n\nemail_body: {email_body}\n\n")
                            
                            result = client.send_reply(message_id, email_body)
                            print(f"\n\nresult: {result}\n\n")
                            
                    except Exception as e:
                        print(f"Error processing message {message_id}: {e}")
                        pass
                
                return True

            else:
                print(f"Mode not Identified")
                return True
                
        except Exception as e:
            print(f"Error in automated response monitoring: {e}")
            return False

# async def main():
#     try:
#         email_id = "subhraturning@gmail.com"
#         automated_response_monitor = AutomatedResponseMonitor()
#         result = await automated_response_monitor.automated_emails_responses(email_id)
#         print(f"Automated response result: {result}")
#     except Exception as e:
#         print(f"Error in main function: {e}")

# if __name__ == "__main__":
#     asyncio.run(main())
