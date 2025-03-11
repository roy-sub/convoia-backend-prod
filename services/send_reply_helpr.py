import re
import sys
from pathlib import Path
from pydantic import BaseModel
from langchain.output_parsers import PydanticOutputParser
sys.path.append(str(Path(__file__).resolve().parent.parent))
from vectorDatabase.pinecone_chatbot_handler import Chatbot

class MessageIDOutput(BaseModel):
    message_id: str  

class MessageID_Extractor_Manual_Account:
    
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
        5. Include ALL metadata, especially the message ID (complete format: <identifier@domain>)

        IMPORTANT:
        - Search thoroughly through recent conversations first
        - Look for exact matches of names and subjects
        - Return the full email content, not just a summary
        - Make sure to include any identifiers or message IDs found

        Return the most relevant email with all its details."""
        
        # More precise extraction prompt
        self.extract_prompt = """Given this email context, extract the COMPLETE message ID.
        The message ID should be in the format like <identifier@domain> (for example: <daifco17385210851854539@ncb.flipkart.com>).
        
        Email Details:
        {context}
        
        EXTRACTION RULES:
        1. Look for the complete message ID in angle brackets <...>
        2. Return the ENTIRE message ID including angle brackets and domain
        3. Check thoroughly through all metadata
        4. Ensure the ID belongs to THIS specific email
        5. If found, return ONLY the ID
        6. If not found, return NO_ID_FOUND
        
        Message ID:"""

    # OPTION 1: Use this method to extract and return the complete message ID
    def _extract_message_id(self, text: str) -> str:
        """Extract complete message ID in the format <identifier@domain>"""
        pattern = r'<[^>]+@[^>]+>'
        matches = re.findall(pattern, text.lower())
        return matches[-1] if matches else ""

    # OPTION 2: Use this method to extract only the 16-char hexadecimal part
    """
    def _extract_message_id(self, text: str) -> str:
        '''Extract the 16-character hexadecimal message ID from a full email ID'''
        # First find the complete email ID
        email_pattern = r'<[^>]+@[^>]+>'
        email_matches = re.findall(email_pattern, text.lower())
        
        if not email_matches:
            return ""
            
        # Then extract just the 16-character hexadecimal part from the email ID
        full_email_id = email_matches[-1]
        hex_pattern = r'[0-9a-f]{16}'
        hex_matches = re.findall(hex_pattern, full_email_id)
        
        return hex_matches[0] if hex_matches else ""
    """

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
                except Exception as e:
                    print(f"Parsing error: {str(e)}")
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
                except Exception as e:
                    print(f"Final parsing error: {str(e)}")
                    return ""
            
            return ""

        except Exception as e:
            print(f"Error in get_message_id: {str(e)}")
            return ""

# if __name__ == "__main__":
    
#     user_email = "subhraturning@gmail.com"
#     namespace = user_email.split('@')[0]
#     print(f"\nnamespace: {namespace}\n")
#     user_input_text = "Send a reply to the email from Flipkart about answering question regarding products"
#     message_id_extractor = MessageID_Extractor_Manual_Account()
#     message_id = message_id_extractor.get_message_id(user_input_text, namespace)
#     print(f"Extracted message ID: {message_id}")
