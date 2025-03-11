# constants.py
from handlers import (
    send_email,
    send_reply_follow_up,
    summarize_emails,
    email_conversational_agent,
    enable_follow_up_reminders,
    disable_follow_up_reminders,
    add_email_label,
    create_email_label,
    enable_important_email_highlighting,
    disable_important_email_highlighting,
    add_important_contacts,
    remove_important_contacts,
    enable_automated_responses,
    disable_automated_responses,
    add_automated_response_categories,
    remove_automated_response_categories
)

FUNCTION_MAP = {
    "Send Reply or Follow Up": send_reply_follow_up,  # Function reference, not string
    "Send Email": send_email,
    "Summarization": summarize_emails,
    "Conversational Agent": email_conversational_agent,
    "Enable Follow Up Reminders": enable_follow_up_reminders,
    "Disable Follow Up Reminders": disable_follow_up_reminders,
    "Add Email Label": add_email_label,
    "Create Email Label": create_email_label,
    "Enable Important Email Highlighting": enable_important_email_highlighting,
    "Disable Important Email Highlighting": disable_important_email_highlighting,
    "Add Important Contacts": add_important_contacts,
    "Remove Important Contacts": remove_important_contacts,
    "Enable Automated Responses": enable_automated_responses,
    "Disable Automated Responses": disable_automated_responses,
    "Add Automated Response Categories": add_automated_response_categories,
    "Remove Automated Response Categories": remove_automated_response_categories,
}

FEATURES = {
    "Send Email": "Compose and send an email using the context provided in the input text.",

    "Send Reply or Follow Up": "Compose and send a reply or follow-up email based on the context of both the previous email and the input text.",

    "Summarization": "When asked to generate a summary of the last received emails",

    "Conversational Agent": "Assist in answering specific questions related to Email Account derived from received emails without performing any additional actions.",

    "Enable Follow Up Reminders": "Activate intelligent tracking of pending emails and generate reminders for follow-ups based on defined response timelines.",

    "Disable Follow Up Reminders": "Deactivate the tracking of pending emails and stop generating follow-up reminders.",

    "Add Email Label": "Apply a specific label or tag to a specific email based on the context provided.",

    "Create Email Label": "To Create a Specifc Email Label / Tag",

    "Enable Important Email Highlighting": "Turn on the feature that highlights important emails as specified by the user.",

    "Disable Important Email Highlighting": "Turn off the feature that highlights important emails.",

    "Add Important Contacts": "Include specific contacts or email IDs in the list of important email highlighting criteria.",

    "Remove Important Contacts": "Delete specific contacts or email IDs from the important email highlighting feature.",

    "Enable Automated Responses": "Activate the automated responses feature to handle routine or unimportant emails using AI-generated templates.",

    "Disable Automated Responses": "Deactivate the automated responses feature for routine or less important emails.",

    "Add Automated Response Categories": "Add specified categories for the automated response feature to handle emails more effectively.",

    "Remove Automated Response Categories": "Remove specific categories from the automated response feature.",

    "Others": "When the requested feature is not among the above options"
}
