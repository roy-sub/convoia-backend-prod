import os
from enum import Enum
from constants import FEATURES
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import EnumOutputParser

# Load environment variables
load_dotenv()

# Create an Enum dynamically from FEATURES
FeatureEnum = Enum('FeatureEnum', {k.replace(" ", "_"): k for k in FEATURES.keys()})
OPENAI_AI_KEY = os.getenv('OPENAI_API_KEY')

class FeatureMatcher:
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):

        self.llm = ChatOpenAI(
            temperature=0,
            model_name=model_name,
            openai_api_key=OPENAI_AI_KEY
        )
        self.output_parser = EnumOutputParser(enum=FeatureEnum)
        
        # Create the prompt template
        template = """You are a feature matching assistant. Your task is to match user input to the most appropriate feature from the following list:

        {features_list}

        IMPORTANT INSTRUCTIONS:
        1. You must choose exactly ONE feature from the list above that best matches the user's request.
        2. If no feature matches well, choose "Others".
        3. Output only the exact feature name, nothing else.
        4. The feature name must match exactly one of the options provided.

        User Request: {user_input}

        Feature:"""

        self.prompt = ChatPromptTemplate.from_template(template)

    def _format_features_list(self) -> str:

        return "\n".join([f"- {key}: {value}" for key, value in FEATURES.items()])

    def get_feature(self, user_input: str) -> str:

        try:
            # Format the prompt with features list and user input
            formatted_prompt = self.prompt.format_messages(
                features_list=self._format_features_list(),
                user_input=user_input
            )
            
            # Get the response and parse it
            response = self.llm(formatted_prompt)
            parsed_feature = self.output_parser.parse(response.content)
            
            # Convert back to original feature name
            return parsed_feature.value

        except Exception as e:
            print(f"Error occurred while processing input: {str(e)}")
            return "Others"
