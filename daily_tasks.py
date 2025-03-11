import asyncio
from aws.email_automation_preferences import EmailAutomationPreferences
from aws.utils import get_all_email_ids_and_modes
from services.followup_responses import EmailFollowUpService
from generator import UserInitializationManager

async def update_database(email_id: str, mode: str):

    print(f"Initiated daily database update for email: {email_id}")

    init_manager = UserInitializationManager()
    result = await init_manager.existing_user_daily_maintenance(email_id, mode)

    if result:
        print(f"Successfully executed database update for email: {email_id}")
    else:
        print(f"Failed to execute database update for email: {email_id}")

async def initiate_follow(email_id: str):

    print(f"Initiated follow up for email: {email_id}")
    
    email_follow_up = EmailFollowUpService()
    result = await email_follow_up.initiate_followup_email(email_id)
    
    if result:
        print(f"Successfully executed follow-up response for email: {email_id}")
    else:
        print(f"Failed to execute follow-up response for email: {email_id}")

async def daily_database_addition() -> None:

    # Fetch list of email IDs and modes
    user_data = get_all_email_ids_and_modes()
    
    # Create tasks for each user
    tasks = [update_database(user['email'], user['mode']) for user in user_data]
    
    # Run all database updates concurrently
    await asyncio.gather(*tasks)
    print("Completed all database updates")

async def automated_follow_up() -> None:

    # Fetch list of email IDs (replace with your actual fetching logic)
    email_ids = EmailAutomationPreferences().get_email_ids_with_active_follow_up()
    
    # Create tasks for each email ID
    tasks = [initiate_follow(email_id) for email_id in email_ids]
    
    # Run all follow-ups concurrently
    await asyncio.gather(*tasks)
    print("Completed all follow-ups")

async def daily():

    # Create tasks for both main functions
    database_task = asyncio.create_task(daily_database_addition())
    follow_up_task = asyncio.create_task(automated_follow_up())
    
    # Run both tasks concurrently
    await asyncio.gather(database_task, follow_up_task)
    print("Daily tasks completed")

# Run the daily function
if __name__ == "__main__":
    asyncio.run(daily())
