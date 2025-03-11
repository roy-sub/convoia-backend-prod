import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from vectorDatabase.pinecone_chatbot_handler import Chatbot

class EmailConversational_Agent():
    
   def __init__(self):
        pass
   
   def email_conversational_agent(self, user_email, user_input_text):
       
        try:
           # Validate inputs
            if not user_email or not user_input_text:
                print("Error: Missing required inputs")
                return False
            
            # Getting the Namespace
            namespace = user_email.split('@')[0]
            
            # Calling the Chatbot
            chatbot = Chatbot()
            response = chatbot.get_response(user_input_text, namespace)

            return True, response
        except Exception as e:
            print(f"Error generating subject: {str(e)}")
            return False, ""

# if __name__ == "__main__":

#     agent = EmailConversational_Agent()
#     user_email = "roysubhradip001@gmail.com"
#     user_input_text = "What was the last email I received from Make.com about operations limit and what did he say?"
#     success, response = agent.email_conversational_agent(user_email, user_input_text)
#     print(f"Success: {success}")
#     print(f"Response: {response}")
