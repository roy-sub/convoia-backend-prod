from typing import Dict, Any
from aws.email_automation_preferences import EmailAutomationPreferences
from services.priority_response import ImportantContactsManager
from services.automated_response import AutomatedResponseCategoryManager
from services.send_email import EmailSender
from services.send_reply import EmailReplier
from services.summarization import GenerateSummarization
from services.conversational_agent import EmailConversational_Agent
from services.add_label import EmailLabel

async def send_email(text: str, email: str) -> Dict[str, Any]:
    
    try:
        email_sender = EmailSender()
        status = email_sender.send_email(email, text)

        if status:
            return {"status": "success", "message": "✉️ Great! Your email has been sent successfully."}
        else:
            return {"status": "failed", "message": "😕 I couldn't send your email. Please try again in a moment."}
    
    except Exception as e:
            print(f"Error in get_message_id: {str(e)}")
            return {"status": "failed", "message": "🚫 Oops! Something went wrong while sending your email. Please try again later."}

async def send_reply_follow_up(text: str, email: str) -> Dict[str, Any]:
    
    try:
        email_replier = EmailReplier()
        status = email_replier.send_reply(email, text)

        if status:
            return {"status": "success", "message": "✅ Perfect! Your reply has been sent successfully."}
        else:
            return {"status": "failed", "message": "❌ I wasn't able to send your reply. Would you like to try again?"}
    
    except Exception as e:
            print(f"Error in get_message_id: {str(e)}")
            return {"status": "failed", "message": "🔄 There was an issue sending your reply. Please check your connection and try again."}

async def summarize_emails(text: str, email: str) -> Dict[str, Any]:
    
    try:
        generator = GenerateSummarization()
        status, result = generator.generate_summarization(email, text)

        if status:
            return {"status": "success", "message": f"📝 Here's your email summary:\n\n{result}"}
        else:
            return {"status": "failed", "message": "📋 I couldn't create a summary right now. Would you like to try again?"}
    
    except Exception as e:
            print(f"Error in get_message_id: {str(e)}")
            return {"status": "failed", "message": "🤔 I ran into trouble generating your summary. Let's give it another try!"}

async def email_conversational_agent(text: str, email: str) -> Dict[str, Any]:
    
    try:
        generator = EmailConversational_Agent()
        status, result = generator.email_conversational_agent(email, text)

        if status:
            return {"status": "success", "message": f"💬 {result}"}
        else:
            return {"status": "failed", "message": "🤖 I'm having trouble processing your request. Could you rephrase that?"}
    
    except Exception as e:
            print(f"Error in get_message_id: {str(e)}")
            return {"status": "failed", "message": "⚠️ Something went wrong with our conversation. Let's start over!"}

async def add_email_label(text: str, email: str) -> Dict[str, Any]:
    
    try:
        emailLabel = EmailLabel()
        status = emailLabel.add_label_to_message(email, text)

        if status:
            return {"status": "success", "message": "🏷️ Label added successfully to your email!"}
        else:
            return {"status": "failed", "message": "📎 I couldn't add that label. Want to try a different one?"}
    
    except Exception as e:
            print(f"Error in get_message_id: {str(e)}")
            return {"status": "failed", "message": "❌ There was an issue adding your label. Please try again."}

async def create_email_label(text: str, email: str) -> Dict[str, Any]:
    
    try:
        emailLabel = EmailLabel()
        status = emailLabel.create_label(email, text)

        if status:
            return {"status": "success", "message": "✨ Great! Your new label has been created."}
        else:
            return {"status": "failed", "message": "🚫 I couldn't create that label. Maybe try a different name?"}
    
    except Exception as e:
            print(f"Error in get_message_id: {str(e)}")
            return {"status": "failed", "message": "⚠️ Something went wrong while creating your label. Let's try again!"}

async def enable_follow_up_reminders(text: str, email: str) -> Dict[str, Any]:
    
    try:
        emailAutomationPreferences = EmailAutomationPreferences()
        status = emailAutomationPreferences.update_category_status(email, "follow_up_emails", True)
        if status:
            return {"status": "success", "message": "⏰ Follow-up reminders are now turned on! I'll help you stay on top of your emails."}
        else:
            return {"status": "failed", "message": "🔄 I couldn't enable follow-up reminders. Would you like to try again?"}
    
    except Exception as e:
            print(f"Error in get_message_id: {str(e)}")
            return {"status": "failed", "message": "❌ There was a problem enabling your reminders. Let's give it another shot!"}

async def disable_follow_up_reminders(text: str, email: str) -> Dict[str, Any]:
    
    try:
        emailAutomationPreferences = EmailAutomationPreferences()
        status = emailAutomationPreferences.update_category_status(email, "follow_up_emails", False)
        if status:
            return {"status": "success", "message": "🔕 Follow-up reminders have been turned off. You won't receive any more notifications."}
        else:
            return {"status": "failed", "message": "⚠️ I couldn't disable the reminders. Should we try again?"}
    
    except Exception as e:
            print(f"Error in get_message_id: {str(e)}")
            return {"status": "failed", "message": "🚫 Something went wrong while disabling your reminders. Please try again later."}

async def enable_important_email_highlighting(text: str, email: str) -> Dict[str, Any]:
    
    try:
        emailAutomationPreferences = EmailAutomationPreferences()
        status = emailAutomationPreferences.update_category_status(email, "important_emails", True)
        if status:
            return {"status": "success", "message": "🌟 Important email highlighting is now active! I'll help you spot the key messages."}
        else:
            return {"status": "failed", "message": "😕 I couldn't turn on email highlighting. Want to try again?"}
    
    except Exception as e:
            print(f"Error in get_message_id: {str(e)}")
            return {"status": "failed", "message": "⚠️ There was an issue enabling highlighting. Let's give it another try!"}

async def disable_important_email_highlighting(text: str, email: str) -> Dict[str, Any]:
    
    try:
        emailAutomationPreferences = EmailAutomationPreferences()
        status = emailAutomationPreferences.update_category_status(email, "important_emails", False)
        if status:
            return {"status": "success", "message": "💡 Email highlighting has been turned off. All emails will appear normal now."}
        else:
            return {"status": "failed", "message": "❌ I couldn't disable the highlighting. Should we try again?"}
    
    except Exception as e:
            print(f"Error in get_message_id: {str(e)}")
            return {"status": "failed", "message": "🚫 Something went wrong while disabling highlighting. Please try again later."}

async def enable_automated_responses(text: str, email: str) -> Dict[str, Any]:
    
    try:
        emailAutomationPreferences = EmailAutomationPreferences()
        status = emailAutomationPreferences.update_category_status(email, "automated_response", True)
        if status:
            return {"status": "success", "message": "🤖 Automated responses are now active! I'll help handle routine emails for you."}
        else:
            return {"status": "failed", "message": "😕 I couldn't enable automated responses. Would you like to try again?"}
    
    except Exception as e:
            print(f"Error in get_message_id: {str(e)}")
            return {"status": "failed", "message": "⚠️ There was a problem enabling automated responses. Let's try again!"}

async def disable_automated_responses(text: str, email: str) -> Dict[str, Any]:
    
    try:
        emailAutomationPreferences = EmailAutomationPreferences()
        status = emailAutomationPreferences.update_category_status(email, "automated_response", False)
        if status:
            return {"status": "success", "message": "📫 Automated responses have been turned off. You'll need to respond to emails manually now."}
        else:
            return {"status": "failed", "message": "❌ I couldn't disable automated responses. Should we try again?"}
    
    except Exception as e:
            print(f"Error in get_message_id: {str(e)}")
            return {"status": "failed", "message": "🚫 Something went wrong while disabling automated responses. Please try again later."}

async def add_important_contacts(text: str, email: str) -> Dict[str, Any]:
    
    try:
        important_contacts_manager = ImportantContactsManager()
        status = important_contacts_manager.add_important_contact(email, text)
        
        if status:
            return {"status": "success", "message": "👥 Contact added to your VIP list! Their emails will be highlighted."}
        else:
            return {"status": "failed", "message": "😕 I couldn't add this contact to your important list. Want to try again?"}
    
    except Exception as e:
            print(f"Error in get_message_id: {str(e)}")
            return {"status": "failed", "message": "⚠️ There was an issue adding your important contact. Let's try again!"}

async def remove_important_contacts(text: str, email: str) -> Dict[str, Any]:
    
    try:
        important_contacts_manager = ImportantContactsManager()
        status = important_contacts_manager.remove_important_contact(email, text)
        
        if status:
            return {"status": "success", "message": "✂️ Contact removed from your VIP list. Their emails won't be highlighted anymore."}
        else:
            return {"status": "failed", "message": "❌ I couldn't remove this contact from your list. Should we try again?"}
    
    except Exception as e:
            print(f"Error in get_message_id: {str(e)}")
            return {"status": "failed", "message": "🚫 Something went wrong while removing the contact. Please try again later."}

async def add_automated_response_categories(text: str, email: str) -> Dict[str, Any]:
    
    try:
        automated_response_category_manager = AutomatedResponseCategoryManager()
        status = automated_response_category_manager.add_categories_to_automated_responses(email, text)

        if status:
            return {"status": "success", "message": "📑 Great! New response category added. I'll use it to help manage your emails."}
        else:
            return {"status": "failed", "message": "😕 I couldn't add that response category. Want to try again?"}
    
    except Exception as e:
            print(f"Error in get_message_id: {str(e)}")
            return {"status": "failed", "message": "⚠️ There was a problem adding the response category. Let's give it another try!"}

async def remove_automated_response_categories(text: str, email: str) -> Dict[str, Any]:
    
    try:
        automated_response_category_manager = AutomatedResponseCategoryManager()
        status = automated_response_category_manager.remove_categories_from_automated_responses(email, text)

        if status:
            return {"status": "success", "message": "🗑️ Response category removed successfully! It won't be used for automated replies anymore."}
        else:
            return {"status": "failed", "message": "❌ I couldn't remove that response category. Should we try again?"}
    
    except Exception as e:
            print(f"Error in get_message_id: {str(e)}")
            return {"status": "failed", "message": "🚫 Something went wrong while removing the category. Please try again later."}
