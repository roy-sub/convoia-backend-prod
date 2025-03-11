import csv
import sys
import boto3
from pathlib import Path
from botocore.exceptions import ClientError
from typing import Dict, List, Optional

sys.path.append(str(Path(__file__).resolve().parent.parent))

class AutomatedResponseManager:
    def __init__(self):
        pass

    def get_aws_credentials(self, credentials_path: str) -> Dict[str, str]:

        with open(credentials_path, 'r') as file:
            csv_reader = csv.DictReader(file)
            credentials = next(csv_reader)
            return {
                'aws_access_key_id': credentials['Access key ID'],
                'aws_secret_access_key': credentials['Secret access key']
            }

    def initialize_automated_responses_for_new_user(self, email_id: str) -> bool:

        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',  # Replace with your region
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )

            table = dynamodb.Table('Convoia_Automated_Responses')
            
            # Default templates
            templates = [
                {
                    "email_id": email_id,
                    "category": "Meeting Confirmation",
                    "description": "Meeting confirmation or details of a scheduled meeting.",
                    "response_directive": "Thank you for confirming the meeting. We look forward to connecting on <meeting_date>. Please let us know if you need further details."
                },
                {
                    "email_id": email_id,
                    "category": "Order Updates",
                    "description": "Updates about the status of an order or a shipment.",
                    "response_directive": "Thank you for your update regarding your order. We are glad to assist you further with any questions or issues related to < relevant order details >"
                },
                {
                    "email_id": email_id,
                    "category": "Promotional Emails",
                    "description": "Marketing emails about sales, discounts, or promotions.",
                    "response_directive": "Thank you for the offer! Could you please share more details about the discount and any applicable terms and conditions?"
                },
                {
                    "email_id": email_id,
                    "category": "Subscription or Account Notifications",
                    "description": "Updates related to any account or subscription status.",
                    "response_directive": "Thank you for notifying us about the subscription update. Please let us know if there's any additional action required on our end."
                },
                {
                    "email_id": email_id,
                    "category": "Event Invitations or RSVPs",
                    "description": "Invitations to events or confirmations of attendance.",
                    "response_directive": "Thank you for the invitation! I'm pleased to confirm my attendance for the event on < relevant event information >. Looking forward to it!"
                },
                {
                    "email_id": email_id,
                    "category": "Delivery Updates",
                    "description": "Delivery status updates for shipments or parcels.",
                    "response_directive": "Thank you for the update regarding the delivery of < relevant item details >. Please let us know if we can track or expedite this process further."
                },
                {
                    "email_id": email_id,
                    "category": "Surveys or Feedback Requests",
                    "description": "Requests for feedback or participation in surveys.",
                    "response_directive": "Thank you for reaching out for feedback. We are happy to provide our thoughts on < relevant details >."
                }
            ]
            
            # Use batch writer to add all items efficiently
            with table.batch_writer() as batch:
                for template in templates:
                    batch.put_item(Item=template)
            
            print(f"Successfully initialized automated responses for {email_id}")
            return True
            
        except ClientError as e:
            print(f"Error initializing automated responses for {email_id}: {str(e)}")
            return False

    def get_categories_for_email(self, email_id: str) -> Optional[List[str]]:

        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',  # Replace with your region
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )

            table = dynamodb.Table('Convoia_Automated_Responses')
            
            response = table.query(
                KeyConditionExpression='email_id = :email',
                ExpressionAttributeValues={
                    ':email': email_id
                },
                ProjectionExpression='category'
            )
            
            categories = [item['category'] for item in response['Items']]
            print(f"Retrieved {len(categories)} categories for {email_id}")
            return categories
            
        except ClientError as e:
            print(f"Error retrieving categories for {email_id}: {str(e)}")
            return None

    def delete_all_entries_for_email(self, email_id: str) -> bool:

        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',  # Replace with your region
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )

            table = dynamodb.Table('Convoia_Automated_Responses')
            
            # First, query all items for this email_id
            response = table.query(
                KeyConditionExpression='email_id = :email',
                ExpressionAttributeValues={
                    ':email': email_id
                }
            )
            
            # Delete each item
            with table.batch_writer() as batch:
                for item in response['Items']:
                    batch.delete_item(
                        Key={
                            'email_id': email_id,
                            'category': item['category']
                        }
                    )
            
            print(f"Successfully deleted all entries for {email_id}")
            return True
            
        except ClientError as e:
            print(f"Error deleting entries for {email_id}: {str(e)}")
            return False

    def delete_specific_category(self, email_id: str, category: str) -> bool:

        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',  # Replace with your region
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )

            table = dynamodb.Table('Convoia_Automated_Responses')
            
            table.delete_item(
                Key={
                    'email_id': email_id,
                    'category': category
                }
            )
            
            print(f"Successfully deleted category '{category}' for {email_id}")
            return True
            
        except ClientError as e:
            print(f"Error deleting category '{category}' for {email_id}: {str(e)}")
            return False

    def add_category_to_automated_response(
        self,
        email_id: str,
        category: str,
        description: str,
        response_directive: str
    ) -> bool:

        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',  # Replace with your region
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )

            table = dynamodb.Table('Convoia_Automated_Responses')
            
            item = {
                'email_id': email_id,
                'category': category,
                'description': description,
                'response_directive': response_directive
            }
            
            table.put_item(Item=item)
            
            print(f"Successfully added new response for {email_id} in category '{category}'")
            return True
            
        except ClientError as e:
            print(f"Error adding response for {email_id}: {str(e)}")
            return False

    def get_categories_with_descriptions(self, email_id: str) -> Optional[Dict[str, str]]:

        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',  # Replace with your region
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )

            table = dynamodb.Table('Convoia_Automated_Responses')
            
            # Query all items for this email_id, projecting only category and description
            response = table.query(
                KeyConditionExpression='email_id = :email',
                ExpressionAttributeValues={
                    ':email': email_id
                },
                ProjectionExpression='category, description'
            )
            
            # Create dictionary mapping categories to descriptions
            categories_dict = {
                item['category']: item['description'] 
                for item in response['Items']
            }
            
            print(f"Retrieved {len(categories_dict)} category-description pairs for {email_id}")
            return categories_dict
            
        except ClientError as e:
            print(f"Error retrieving categories and descriptions for {email_id}: {str(e)}")
            return None

    def get_categories_with_response_directive(self, email_id: str) -> Optional[Dict[str, str]]:

        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',  # Replace with your region
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )

            table = dynamodb.Table('Convoia_Automated_Responses')
            
            # Query all items for this email_id, projecting only category and response_directive
            response = table.query(
                KeyConditionExpression='email_id = :email',
                ExpressionAttributeValues={
                    ':email': email_id
                },
                ProjectionExpression='category, response_directive'
            )
            
            # Create dictionary mapping categories to response directives
            response_dict = {
                item['category']: item['response_directive'] 
                for item in response['Items']
            }
            
            print(f"Retrieved {len(response_dict)} category-response directive pairs for {email_id}")
            return response_dict
            
        except ClientError as e:
            print(f"Error retrieving categories and response directives for {email_id}: {str(e)}")
            return None

# if __name__ == "__main__":
    
#     email_id = "subhraturning@gmail.com"
#     automatedResponseManager = AutomatedResponseManager()
#     automatedResponseManager.delete_all_entries_for_email(email_id)
#     result = automatedResponseManager.get_categories_with_descriptions(email_id)
#     print(f"\nresult: {result}\n")
#     automatedResponseManager.get_categories_with_response_directive(email_id)
#     print(f"\nresult: {result}\n")
