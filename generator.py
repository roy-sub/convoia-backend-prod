from userManagement.user_data_extraction import UserDataExtractor
from aws.email_automation_preferences import EmailAutomationPreferences
from aws.automated_priority_response import ImportantEmailManager
from aws.automated_response import AutomatedResponseManager

class UserInitializationManager:
    
    def __init__(self):
        self.user_data_extractor = UserDataExtractor()
        self.email_automation_preferences = EmailAutomationPreferences()
        self.important_email_manager = ImportantEmailManager()
        self.automated_response_manager = AutomatedResponseManager()

    def new_user_initialization(self, email_id, mode):
        
        success_status = {}
        
        user_data_success = self.user_data_extractor.new_user_data_extraction(email_id, mode)
        email_preferences_success = self.email_automation_preferences.initialize_automated_response_tracking_database(email_id)
        important_email_success = self.important_email_manager.initialize_important_emails_data_for_new_user(email_id)
        automated_response_success = self.automated_response_manager.initialize_automated_responses_for_new_user(email_id)

        success_status['user_data'] = user_data_success
        success_status['email_preferences'] = email_preferences_success 
        success_status['important_email'] = important_email_success
        success_status['automated_response'] = automated_response_success

        print(f"\nsuccess_status: {success_status}\n")

        return all([user_data_success, email_preferences_success, important_email_success, automated_response_success])

    async def existing_user_daily_maintenance(self, email_id, mode):
        
        user_data_success = self.user_data_extractor.existing_user_data_extraction(email_id, mode)
        
        print(f"\nDaily user_data_success: {user_data_success}\n")
        return user_data_success
