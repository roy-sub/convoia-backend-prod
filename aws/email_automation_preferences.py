import csv
import sys
import boto3
from pathlib import Path
from botocore.exceptions import ClientError
from typing import Dict, List, Optional

sys.path.append(str(Path(__file__).resolve().parent.parent))

class EmailAutomationPreferences:
    
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

    def initialize_automated_response_tracking_database(self, email_id: str) -> bool:

        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',  # Replace with your region
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )

            table = dynamodb.Table('Convoia_Tracking_Automated_Responses')
            
            # Default templates
            new_user = [
                { "email_id": email_id, "automated_response": False, "important_emails":False, "follow_up_emails": False } 
            ]
            
            # Use batch writer to add all items efficiently
            with table.batch_writer() as batch:
                for template in new_user:
                    batch.put_item(Item=template)
            
            print(f"Successfully initialized automated responses for {email_id}")
            return True
            
        except ClientError as e:
            print(f"Error initializing automated responses for {email_id}: {str(e)}")
            return False

    def get_automated_response_status(self, email_id: str) -> Optional[Dict]:
        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )
            
            table = dynamodb.Table('Convoia_Tracking_Automated_Responses')
            
            # Get the item for the email_id
            response = table.get_item(
                Key={
                    'email_id': email_id
                }
            )
            
            if 'Item' in response:
                print(f"Status for {email_id}:")
                print(f"Automated Response: {response['Item']['automated_response']}")
                print(f"Important Emails: {response['Item']['important_emails']}")
                print(f"Follow-up Emails: {response['Item']['follow_up_emails']}")
                return response['Item']
            else:
                print(f"No status found for {email_id}")
                return None
                
        except ClientError as e:
            print(f"Error retrieving status for {email_id}: {str(e)}")
            return None

    def update_category_status(self, email_id: str, category_name: str, value: bool) -> bool:
        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )
            
            table = dynamodb.Table('Convoia_Tracking_Automated_Responses')
            
            # Update the specific category
            response = table.update_item(
                Key={
                    'email_id': email_id
                },
                UpdateExpression=f"set {category_name} = :val",
                ExpressionAttributeValues={
                    ':val': value
                },
                ReturnValues="UPDATED_NEW"
            )
            
            print(f"Successfully updated {category_name} to {value} for {email_id}")
            return True
            
        except ClientError as e:
            print(f"Error updating {category_name} for {email_id}: {str(e)}")
            return False
        
    def get_email_ids_with_active_automated_response(self) -> List[str]:

            try:
                credentials = self.get_aws_credentials("credentials/credential_aws.csv")
                
                dynamodb = boto3.resource(
                    'dynamodb',
                    region_name='us-west-2',
                    aws_access_key_id=credentials['aws_access_key_id'],
                    aws_secret_access_key=credentials['aws_secret_access_key']
                )
                
                table = dynamodb.Table('Convoia_Tracking_Automated_Responses')
                
                # Scan the table for items where automated_response is True
                response = table.scan(
                    FilterExpression='automated_response = :val',
                    ExpressionAttributeValues={
                        ':val': True
                    }
                )
                
                # Extract email_ids from the response
                email_ids = [item['email_id'] for item in response.get('Items', [])]
                
                # Handle pagination if necessary
                while 'LastEvaluatedKey' in response:
                    response = table.scan(
                        FilterExpression='automated_response = :val',
                        ExpressionAttributeValues={
                            ':val': True
                        },
                        ExclusiveStartKey=response['LastEvaluatedKey']
                    )
                    email_ids.extend([item['email_id'] for item in response.get('Items', [])])
                
                print(f"Found {len(email_ids)} emails with automated responses enabled")
                return email_ids
                
            except ClientError as e:
                print(f"Error retrieving automated response emails: {str(e)}")
                return []

    def get_email_ids_with_active_important_flag(self) -> List[str]:

        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )
            
            table = dynamodb.Table('Convoia_Tracking_Automated_Responses')
            
            # Scan the table for items where important_emails is True
            response = table.scan(
                FilterExpression='important_emails = :val',
                ExpressionAttributeValues={
                    ':val': True
                }
            )
            
            # Extract email_ids from the response
            email_ids = [item['email_id'] for item in response.get('Items', [])]
            
            # Handle pagination if necessary
            while 'LastEvaluatedKey' in response:
                response = table.scan(
                    FilterExpression='important_emails = :val',
                    ExpressionAttributeValues={
                        ':val': True
                    },
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                email_ids.extend([item['email_id'] for item in response.get('Items', [])])
            
            print(f"Found {len(email_ids)} important emails")
            return email_ids
            
        except ClientError as e:
            print(f"Error retrieving important emails: {str(e)}")
            return []

    def get_email_ids_with_active_follow_up(self) -> List[str]:

        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )
            
            table = dynamodb.Table('Convoia_Tracking_Automated_Responses')
            
            # Scan the table for items where follow_up_emails is True
            response = table.scan(
                FilterExpression='follow_up_emails = :val',
                ExpressionAttributeValues={
                    ':val': True
                }
            )
            
            # Extract email_ids from the response
            email_ids = [item['email_id'] for item in response.get('Items', [])]
            
            # Handle pagination if necessary
            while 'LastEvaluatedKey' in response:
                response = table.scan(
                    FilterExpression='follow_up_emails = :val',
                    ExpressionAttributeValues={
                        ':val': True
                    },
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                email_ids.extend([item['email_id'] for item in response.get('Items', [])])
            
            print(f"Found {len(email_ids)} emails requiring follow-up")
            return email_ids
            
        except ClientError as e:
            print(f"Error retrieving follow-up emails: {str(e)}")
            return []
