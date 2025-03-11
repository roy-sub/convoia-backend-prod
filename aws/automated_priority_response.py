import csv
import sys
import boto3
from pathlib import Path
from botocore.exceptions import ClientError
from typing import Dict, List, Optional

sys.path.append(str(Path(__file__).resolve().parent.parent))

class ImportantEmailManager:
    
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

    def write_to_dynamodb_table(self, dynamodb, table_name: str, items: list) -> bool:
        table = dynamodb.Table(table_name)
        try:
            with table.batch_writer() as batch:
                for item in items:
                    batch.put_item(Item=item)
            print(f"Successfully wrote to table {table_name}")
            return True
        except ClientError as e:
            print(f"Error writing to table {table_name}: {str(e)}")
            return False

    def initialize_important_emails_data_for_new_user(self, email_id: str) -> bool:
        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )

            # Initialize templates for each table
            important_keywords = [
                { "email_id": email_id, "keyword": "urgent" },
                { "email_id": email_id, "keyword": "immediate" },
                { "email_id": email_id, "keyword": "asap" },
                { "email_id": email_id, "keyword": "emergency" },
                { "email_id": email_id, "keyword": "critical" },
                { "email_id": email_id, "keyword": "deadline" },
                { "email_id": email_id, "keyword": "important" },
                { "email_id": email_id, "keyword": "priority" },
                { "email_id": email_id, "keyword": "action required" },
                { "email_id": email_id, "keyword": "essential" },
                { "email_id": email_id, "keyword": "high priority" },
                { "email_id": email_id, "keyword": "must do" },
                { "email_id": email_id, "keyword": "time-sensitive" },
                { "email_id": email_id, "keyword": "important task" },
                { "email_id": email_id, "keyword": "top priority" },
                { "email_id": email_id, "keyword": "high importance" },
                { "email_id": email_id, "keyword": "imminent" },
                { "email_id": email_id, "keyword": "vital" },
                { "email_id": email_id, "keyword": "pressing" },
                { "email_id": email_id, "keyword": "necessary" },
                { "email_id": email_id, "keyword": "mandatory" },
                { "email_id": email_id, "keyword": "pivotal" },
                { "email_id": email_id, "keyword": "significant" },
                { "email_id": email_id, "keyword": "imperative" },
                { "email_id": email_id, "keyword": "non-negotiable" },
                { "email_id": email_id, "keyword": "crucial" }
            ]
            
            important_senders = [
                { "email_id": email_id, "sender_email_id": "none@domain.com" }
            ]

            important_descriptions = [
                { "email_id": email_id, "description": "no description" }
            ]

            success = all([
                self.write_to_dynamodb_table(dynamodb, 'Conovia_Important_Emails_Keywords', important_keywords),
                self.write_to_dynamodb_table(dynamodb, 'Conovia_Important_Emails_Sender', important_senders),
                self.write_to_dynamodb_table(dynamodb, 'Conovia_Important_Emails_Description', important_descriptions)
            ])

            if success:
                print(f"Successfully initialized important emails data for {email_id}")
                return True
            else:
                print(f"Error initializing some data for {email_id}")
                return False

        except ClientError as e:
            print(f"Error initializing important emails data for {email_id}: {str(e)}")
            return False
        except Exception as e:
            print(f"Unexpected error initializing data for {email_id}: {str(e)}")
            return False

    # 1. Functions to delete all entries for an email_id from each table

    def delete_all_keywords_for_email(self, email_id: str) -> bool:
        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )
            table = dynamodb.Table('Conovia_Important_Emails_Keywords')
            
            # Query all keywords for this email_id
            response = table.query(
                KeyConditionExpression='email_id = :email',
                ExpressionAttributeValues={':email': email_id}
            )
            
            # Delete each item
            with table.batch_writer() as batch:
                for item in response['Items']:
                    batch.delete_item(
                        Key={
                            'email_id': email_id,
                            'keyword': item['keyword']
                        }
                    )
            
            print(f"Successfully deleted all keywords for {email_id}")
            return True
        except ClientError as e:
            print(f"Error deleting keywords for {email_id}: {str(e)}")
            return False

    def delete_all_senders_for_email(self, email_id: str) -> bool:
        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )
            table = dynamodb.Table('Conovia_Important_Emails_Sender')
            
            response = table.query(
                KeyConditionExpression='email_id = :email',
                ExpressionAttributeValues={':email': email_id}
            )
            
            with table.batch_writer() as batch:
                for item in response['Items']:
                    batch.delete_item(
                        Key={
                            'email_id': email_id,
                            'sender_email_id': item['sender_email_id']
                        }
                    )
            
            print(f"Successfully deleted all senders for {email_id}")
            return True
        except ClientError as e:
            print(f"Error deleting senders for {email_id}: {str(e)}")
            return False

    def delete_all_descriptions_for_email(self,email_id: str) -> bool:
        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )
            table = dynamodb.Table('Conovia_Important_Emails_Description')
            
            response = table.query(
                KeyConditionExpression='email_id = :email',
                ExpressionAttributeValues={':email': email_id}
            )
            
            with table.batch_writer() as batch:
                for item in response['Items']:
                    batch.delete_item(
                        Key={
                            'email_id': email_id,
                            'description': item['description']
                        }
                    )
            
            print(f"Successfully deleted all descriptions for {email_id}")
            return True
        except ClientError as e:
            print(f"Error deleting descriptions for {email_id}: {str(e)}")
            return False

    # 2. Functions to get entries based on email_id

    def get_keywords_for_email(self, email_id: str) -> Optional[List[str]]:
        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )
            table = dynamodb.Table('Conovia_Important_Emails_Keywords')
            
            response = table.query(
                KeyConditionExpression='email_id = :email',
                ExpressionAttributeValues={':email': email_id}
            )
            
            keywords = [item['keyword'] for item in response['Items']]
            print(f"Retrieved {len(keywords)} keywords for {email_id}")
            return keywords
        except ClientError as e:
            print(f"Error retrieving keywords for {email_id}: {str(e)}")
            return None

    def get_senders_for_email(self, email_id: str) -> Optional[List[str]]:
        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )
            table = dynamodb.Table('Conovia_Important_Emails_Sender')
            
            response = table.query(
                KeyConditionExpression='email_id = :email',
                ExpressionAttributeValues={':email': email_id}
            )
            
            senders = [item['sender_email_id'] for item in response['Items']]
            print(f"Retrieved {len(senders)} senders for {email_id}")
            return senders
        except ClientError as e:
            print(f"Error retrieving senders for {email_id}: {str(e)}")
            return None

    def get_descriptions_for_email(self, email_id: str) -> Optional[List[str]]:
        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )
            table = dynamodb.Table('Conovia_Important_Emails_Description')
            
            response = table.query(
                KeyConditionExpression='email_id = :email',
                ExpressionAttributeValues={':email': email_id}
            )
            
            descriptions = [item['description'] for item in response['Items']]
            print(f"Retrieved {len(descriptions)} descriptions for {email_id}")
            return descriptions
        except ClientError as e:
            print(f"Error retrieving descriptions for {email_id}: {str(e)}")
            return None

    # 3. Functions to delete specific entries

    def delete_specific_keyword(self, email_id: str, keyword: str) -> bool:
        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )
            table = dynamodb.Table('Conovia_Important_Emails_Keywords')
            
            table.delete_item(
                Key={
                    'email_id': email_id,
                    'keyword': keyword
                }
            )
            
            print(f"Successfully deleted keyword '{keyword}' for {email_id}")
            return True
        except ClientError as e:
            print(f"Error deleting keyword for {email_id}: {str(e)}")
            return False

    def delete_specific_sender(self, email_id: str, sender: str) -> bool:
        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )
            table = dynamodb.Table('Conovia_Important_Emails_Sender')
            
            table.delete_item(
                Key={
                    'email_id': email_id,
                    'sender_email_id': sender
                }
            )
            
            print(f"Successfully deleted sender '{sender}' for {email_id}")
            return True
        except ClientError as e:
            print(f"Error deleting sender for {email_id}: {str(e)}")
            return False

    def delete_specific_description(self, email_id: str, description: str) -> bool:
        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )
            table = dynamodb.Table('Conovia_Important_Emails_Description')
            
            table.delete_item(
                Key={
                    'email_id': email_id,
                    'description': description
                }
            )
            
            print(f"Successfully deleted description for {email_id}")
            return True
        except ClientError as e:
            print(f"Error deleting description for {email_id}: {str(e)}")
            return False

    # 4. Functions to add specific entries

    def add_keyword(self, email_id: str, keyword: str) -> bool:
        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )
            table = dynamodb.Table('Conovia_Important_Emails_Keywords')
            
            table.put_item(
                Item={
                    'email_id': email_id,
                    'keyword': keyword
                }
            )
            
            print(f"Successfully added keyword '{keyword}' for {email_id}")
            return True
        except ClientError as e:
            print(f"Error adding keyword for {email_id}: {str(e)}")
            return False

    def add_sender(self, email_id: str, sender: str) -> bool:
        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )
            table = dynamodb.Table('Conovia_Important_Emails_Sender')
            
            table.put_item(
                Item={
                    'email_id': email_id,
                    'sender_email_id': sender
                }
            )
            
            print(f"Successfully added sender '{sender}' for {email_id}")
            return True
        except ClientError as e:
            print(f"Error adding sender for {email_id}: {str(e)}")
            return False

    def add_description(self, email_id: str, description: str) -> bool:
        try:
            credentials = self.get_aws_credentials("credentials/credential_aws.csv")
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='us-west-2',
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )
            table = dynamodb.Table('Conovia_Important_Emails_Description')
            
            table.put_item(
                Item={
                    'email_id': email_id,
                    'description': description
                }
            )
            
            print(f"Successfully added description for {email_id}")
            return True
        except ClientError as e:
            print(f"Error adding description for {email_id}: {str(e)}")
            return False

# print(ImportantEmailManager().get_keywords_for_email("roysubhradip001@gmail.com"))
# print()
# print(ImportantEmailManager().get_senders_for_email("roysubhradip001@gmail.com"))
