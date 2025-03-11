import asyncio
from typing import List
from aws.email_automation_preferences import EmailAutomationPreferences
from services.automated_response import AutomatedResponseMonitor
from services.priority_response import EmailImportanceAnalyzer

async def execute_automated_response(email_id: str):

    print(f"\n\nSTARTING TO EXECUTE AUTOMATED RESPONSES FOR: {email_id}\n\n")

    automated_response_monitor = AutomatedResponseMonitor()
    await automated_response_monitor.automated_emails_responses(email_id)

    print(f"Executed automated response for email: {email_id}")

async def execute_priority_response(email_id: str):
    print(f"\n\nexecute_priority_response: {email_id}\n\n")
    
    email_importance_analyzer = EmailImportanceAnalyzer()
    result = await email_importance_analyzer.automated_priority_response_emails(email_id)
    
    if result:
        print(f"Successfully executed priority response for email: {email_id}")
    else:
        print(f"Failed to execute priority response for email: {email_id}")

async def automated_response() -> None:

    # Fetch list of email IDs for automated responses
    email_ids = EmailAutomationPreferences().get_email_ids_with_active_automated_response()
    
    # Create tasks for each email ID
    tasks = [execute_automated_response(email_id) for email_id in email_ids]
    
    # Run all automated responses concurrently
    await asyncio.gather(*tasks)
    print("Completed all automated responses")

async def priority_response() -> None:

    # Fetch list of email IDs for priority handling
    email_ids = EmailAutomationPreferences().get_email_ids_with_active_important_flag()
    
    # Create tasks for each email ID
    tasks = [execute_priority_response(email_id) for email_id in email_ids]
    
    # Run all priority responses concurrently
    await asyncio.gather(*tasks)
    print("Completed all priority responses")

async def hourly():

    # Create tasks for both main functions
    automated_task = asyncio.create_task(automated_response())
    priority_task = asyncio.create_task(priority_response())
    
    # Run both tasks concurrently
    await asyncio.gather(automated_task, priority_task)
    print("Hourly tasks completed")

# Run the hourly function
if __name__ == "__main__":
    asyncio.run(hourly())
