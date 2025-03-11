import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from dataExtraction.gmail.data_extraction import GmailDataExtractor
from dataExtraction.custom.data_extraction import customEmailDataExtractor
from aws.utils import get_manual_email_password
from vectorDatabase.data_preprocessing import DataPreprocessor
from vectorDatabase.pinecone_chatbot_handler import Chatbot

class UserDataExtractor:

    def __init__(self):
        pass

    def new_user_data_extraction(self, email_id, mode):

        try:

            # if mode == "oauth": 
            #     gmailDataExtractor = GmailDataExtractor(email_id)
            #     json_file_path = gmailDataExtractor.fetch_email_threads()
            
            # elif mode == "manual":
            #     email_address = email_id
            #     password = get_manual_email_password(email_address)
            #     fetcher = customEmailDataExtractor(email_address, password)
            #     json_file_path = fetcher.fetch_email_threads()

            # dataPreprocessor = DataPreprocessor(json_file_path)
            # txt_file_path = dataPreprocessor.convert()

            txt_file_path = "subhraturning@gmail.com.txt"

            chatbot = Chatbot()
            namespace = email_id.split('@')[0]

            print(f"namespace: {namespace}")
            
            chatbot.upload_file(txt_file_path, namespace)

            # os.remove(json_file_path)
            # os.remove(txt_file_path)

            return True
        
        except Exception as e:
            print(e)
            return False
    
    def existing_user_data_extraction(self, email_id, mode):

        try:

            if mode == "oauth": 
                gmailDataExtractor = GmailDataExtractor(email_id)
                json_file_path = gmailDataExtractor.fetch_email_threads()
            
            elif mode == "manual":
                email_address = email_id
                password = get_manual_email_password(email_address)
                fetcher = customEmailDataExtractor(email_address, password)
                json_file_path = fetcher.fetch_email_threads(1)

            dataPreprocessor = DataPreprocessor(json_file_path)
            txt_file_path = dataPreprocessor.convert()

            chatbot = Chatbot()
            namespace = email_id.split('@')[0]
            chatbot.upload_file(txt_file_path, namespace)

            # os.remove(json_file_path)
            # os.remove(txt_file_path)

            return True
        
        except Exception as e:
            print(e)
            return False

if __name__ == "__main__":
    # Initialize the UserDataExtractor
    # Test user data extraction with sample email
    extractor = UserDataExtractor()
    email_id = "subhraturning@gmail.com"
    mode = "manual"
    
    # Test with OAuth mode
    result = extractor.new_user_data_extraction(email_id, mode)
    print(f"result: {result}")
