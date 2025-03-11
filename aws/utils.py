import os
import csv
import boto3
import codecs
from botocore.exceptions import ClientError

def fetch_tokens(email):
    
    try:
        # Read AWS credentials
        aws_credentials = {}
        with codecs.open('credentials/credential_aws.csv', 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                aws_credentials['aws_access_key_id'] = row.get('Access key ID', '').strip()
                aws_credentials['aws_secret_access_key'] = row.get('Secret access key', '').strip()
        
        # Initialize DynamoDB client
        dynamodb = boto3.resource(
            'dynamodb',
            aws_access_key_id=aws_credentials['aws_access_key_id'],
            aws_secret_access_key=aws_credentials['aws_secret_access_key'],
            region_name='us-west-2'
        )

        table = dynamodb.Table('ConvoiaUsers')
        
        # Use scan with correct filter expression syntax
        response = table.scan(
            FilterExpression='email = :email_val',
            ExpressionAttributeValues={
                ':email_val': email
            }
        )

        # Check if any items were found
        if not response.get('Items'):
            return None

        # Get the first matching item
        item = response['Items'][0]
        
        # Transform the response by removing the {'S': } wrapper
        transformed_item = {}
        
        for key, value in item.items():
            # Handling string values wrapped in {'S': value}
            if isinstance(value, dict) and 'S' in value:
                transformed_item[key] = value['S']
            else:
                transformed_item[key] = value

        return transformed_item

    except ClientError as e:
        print(f"An error occurred: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def get_all_email_ids():
    
    try:
        # Read AWS credentials
        aws_credentials = {}
        with codecs.open('credentials/credential_aws.csv', 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                aws_credentials['aws_access_key_id'] = row.get('Access key ID', '').strip()
                aws_credentials['aws_secret_access_key'] = row.get('Secret access key', '').strip()
        
        # Initialize DynamoDB client
        dynamodb = boto3.resource(
            'dynamodb',
            aws_access_key_id=aws_credentials['aws_access_key_id'],
            aws_secret_access_key=aws_credentials['aws_secret_access_key'],
            region_name='us-west-2'
        )

        table = dynamodb.Table('ConvoiaUsers')
        
        # Scan the entire table without any filter
        response = table.scan()
        
        # Extract email_ids from the response
        email_ids = [item['email'] for item in response.get('Items', [])]
        
        # Handle pagination if necessary
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            email_ids.extend([item['email'] for item in response.get('Items', [])])
        
        print(f"Found total of {len(email_ids)} emails")
        return email_ids
        
    except ClientError as e:
        print(f"Error retrieving emails: {str(e)}")
        return []

def get_all_email_ids_and_modes():
    
    try:
        # Read AWS credentials
        aws_credentials = {}
        with codecs.open('credentials/credential_aws.csv', 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                aws_credentials['aws_access_key_id'] = row.get('Access key ID', '').strip()
                aws_credentials['aws_secret_access_key'] = row.get('Secret access key', '').strip()
        
        # Initialize DynamoDB client
        dynamodb = boto3.resource(
            'dynamodb',
            aws_access_key_id=aws_credentials['aws_access_key_id'],
            aws_secret_access_key=aws_credentials['aws_secret_access_key'],
            region_name='us-west-2'
        )

        table = dynamodb.Table('ConvoiaUsers')
        
        # Scan the entire table without any filter
        response = table.scan()
        
        # Extract email_ids and modes from the response
        user_data = [{'email': item['email'], 'mode': item.get('mode', None)} for item in response.get('Items', [])]
        
        # Handle pagination if necessary
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            user_data.extend([{'email': item['email'], 'mode': item.get('mode', None)} for item in response.get('Items', [])])
        
        print(f"Found total of {len(user_data)} users")
        return user_data
        
    except ClientError as e:
        print(f"Error retrieving user data: {str(e)}")
        return []

def get_manual_email_password(email_id):
    try:
        # Read AWS credentials
        aws_credentials = {}
        with codecs.open('credentials/credential_aws.csv', 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                aws_credentials['aws_access_key_id'] = row.get('Access key ID', '').strip()
                aws_credentials['aws_secret_access_key'] = row.get('Secret access key', '').strip()
        
        # Initialize DynamoDB client
        dynamodb = boto3.resource(
            'dynamodb',
            aws_access_key_id=aws_credentials['aws_access_key_id'],
            aws_secret_access_key=aws_credentials['aws_secret_access_key'],
            region_name='us-west-2'
        )

        table = dynamodb.Table('ConvoiaUsers')
        
        # Use scan with filter expression for email and mode
        # Use ExpressionAttributeNames to handle reserved keyword 'mode'
        response = table.scan(
            FilterExpression='email = :email_val AND #user_mode = :mode_val',
            ExpressionAttributeNames={
                '#user_mode': 'mode'
            },
            ExpressionAttributeValues={
                ':email_val': email_id,
                ':mode_val': 'manual'
            }
        )
        
        # Check if any items were found
        items = response.get('Items', [])
        if not items:
            print(f"No manual account found for email: {email_id}")
            return None
            
        # Get the first matching item (should only be one)
        item = items[0]
        
        # Extract the password
        password = item.get('password')
        
        # Handle different response formats (nested dict vs direct value)
        if isinstance(password, dict) and 'S' in password:
            return password['S']
        else:
            return password
            
    except ClientError as e:
        print(f"DynamoDB error retrieving password: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error retrieving password: {str(e)}")
        return None

def get_user_credentials(email_id):

    try:
        # Read AWS credentials
        aws_credentials = {}
        with codecs.open('credentials/credential_aws.csv', 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                aws_credentials['aws_access_key_id'] = row.get('Access key ID', '').strip()
                aws_credentials['aws_secret_access_key'] = row.get('Secret access key', '').strip()
        
        # Initialize DynamoDB client
        dynamodb = boto3.resource(
            'dynamodb',
            aws_access_key_id=aws_credentials['aws_access_key_id'],
            aws_secret_access_key=aws_credentials['aws_secret_access_key'],
            region_name='us-west-2'
        )

        table = dynamodb.Table('ConvoiaUsers')
        
        # Use scan with filter expression for email
        response = table.scan(
            FilterExpression='email = :email_val',
            ExpressionAttributeValues={
                ':email_val': email_id
            }
        )
        
        # Check if any items were found
        items = response.get('Items', [])
        if not items:
            print(f"No account found for email: {email_id}")
            return ""
            
        # Get the first matching item
        item = items[0]
        
        # Extract the requested fields, using correct field names from the database
        password = item.get('password', '')
        mode = item.get('mode', '')
        smtp_server = item.get('emailServer', '')  # Changed from 'smtp_server' to 'emailServer'
        imap_server = item.get('imap_server', '')
        
        # Handle different response formats (nested dict vs direct value)
        # for each field
        if isinstance(password, dict) and 'S' in password:
            password = password['S']
            
        if isinstance(mode, dict) and 'S' in mode:
            mode = mode['S']
            
        if isinstance(smtp_server, dict) and 'S' in smtp_server:
            smtp_server = smtp_server['S']
            
        if isinstance(imap_server, dict) and 'S' in imap_server:
            imap_server = imap_server['S']
        
        # Return as separate values in a tuple
        return password, mode, smtp_server, imap_server
            
    except ClientError as e:
        print(f"DynamoDB error retrieving credentials: {str(e)}")
        return None, None, None, None
    except Exception as e:
        print(f"Unexpected error retrieving credentials: {str(e)}")
        return None, None, None, None

# # User Testing
# if __name__ == "__main__":

#     email = "subhraturning@gmail.com"
#     imap_server = "imap.gmail.com"

#     result = get_all_email_ids_and_modes()
#     print(f"\nresult: {result}\n")

#     result = get_manual_email_password(email)
#     print(f"\nresult: {result}\n")

#     password, mode, smtp_server, imap_server = get_user_credentials(email)
#     print(f"\npassword: {password}\nmode : {mode}\nsmtp_server: {smtp_server}\nimap_server: {imap_server}")

#     result = update_imap_server(email, imap_server)
#     print(f"\nresult: {result}\n")

#     email_id = 'test@gmail.com'
#     user_details = fetch_tokens(email_id)

#     refresh_token = user_details.get('refresh_token')
#     access_token = user_details.get('access_token')
#     password = user_details.get('password')
#     smtp_server = user_details.get('emailServer')
#     imap_server = user_details.get('imap_server')
    
#     print(f"\nrefresh_token: {refresh_token}\naccess_token: {access_token}\n")
#     print(f"\npassword: {password}\nsmtp_server: {smtp_server}\nimap_server: {imap_server}")
