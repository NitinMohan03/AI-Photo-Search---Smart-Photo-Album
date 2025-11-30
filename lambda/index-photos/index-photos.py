import json
import boto3
import os
from datetime import datetime
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

# Initialize AWS clients
s3_client = boto3.client('s3')
rekognition_client = boto3.client('rekognition')

# OpenSearch configuration
OPENSEARCH_HOST = os.environ.get('OPENSEARCH_HOST')
OPENSEARCH_REGION = os.environ.get('AWS_REGION', 'us-east-1')
INDEX_NAME = 'photos'

def get_opensearch_client():
    """Create and return OpenSearch client with AWS IAM Authentication"""
    
    # Get AWS credentials from Lambda execution role
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        OPENSEARCH_REGION,
        'es',
        session_token=credentials.token
    )
    
    opensearch_client = OpenSearch(
        hosts=[{'host': OPENSEARCH_HOST, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=30
    )
    return opensearch_client

def lambda_handler(event, context):
    """
    Lambda function to index photos in OpenSearch when uploaded to S3.
    
    Steps:
    1. Extract S3 bucket and object key from event
    2. Use Rekognition to detect labels
    3. Retrieve custom labels from S3 object metadata
    4. Create JSON object with metadata
    5. Index in OpenSearch
    """
    
    print(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract bucket and object key from S3 event
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            
            print(f"Processing file: {key} from bucket: {bucket}")
            
            # Step 1: Detect labels using Rekognition
            labels = detect_labels(bucket, key)
            print(f"Rekognition detected labels: {labels}")
            
            # Step 2: Retrieve custom labels from S3 metadata
            custom_labels = get_custom_labels(bucket, key)
            print(f"Custom labels from metadata: {custom_labels}")
            
            # Step 3: Combine all labels
            all_labels = labels + custom_labels
            print(f"All labels combined: {all_labels}")
            
            # Step 4: Create JSON object for OpenSearch
            created_timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            photo_document = {
                'objectKey': key,
                'bucket': bucket,
                'createdTimestamp': created_timestamp,
                'labels': all_labels
            }
            
            print(f"Photo document to index: {json.dumps(photo_document)}")
            
            # Step 5: Index in OpenSearch
            index_photo(photo_document)
            
            print(f"Successfully indexed {key}")
            
        return {
            'statusCode': 200,
            'body': json.dumps('Photo indexed successfully')
        }
        
    except Exception as e:
        print(f"Error processing photo: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

def detect_labels(bucket, key):
    """
    Use Rekognition to detect labels in the image.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        
    Returns:
        List of detected label names
    """
    try:
        response = rekognition_client.detect_labels(
            Image={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': key
                }
            },
            MaxLabels=10,
            MinConfidence=70
        )
        
        labels = [label['Name'].lower() for label in response['Labels']]
        return labels
        
    except Exception as e:
        print(f"Error detecting labels: {str(e)}")
        return []

def get_custom_labels(bucket, key):
    """
    Retrieve custom labels from S3 object metadata.
    
    Note: The IAM permission s3:GetObject authorizes both GetObject and HeadObject API calls.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        
    Returns:
        List of custom labels
    """
    try:
        response = s3_client.head_object(Bucket=bucket, Key=key)
        metadata = response.get('Metadata', {})
        
        # Get custom labels from metadata
        custom_labels_str = metadata.get('customlabels', '')
        
        if custom_labels_str:
            # Split comma-separated labels and clean them
            custom_labels = [label.strip().lower() for label in custom_labels_str.split(',') if label.strip()]
            return custom_labels
        
        return []
        
    except Exception as e:
        print(f"Error retrieving custom labels: {str(e)}")
        return []

def index_photo(photo_document):
    """
    Index photo document in OpenSearch.
    
    Args:
        photo_document: Dictionary containing photo metadata and labels
    """
    try:
        opensearch_client = get_opensearch_client()
        
        # Use objectKey as document ID for idempotency
        doc_id = photo_document['objectKey']
        
        response = opensearch_client.index(
            index=INDEX_NAME,
            id=doc_id,
            body=photo_document,
            refresh=True
        )
        
        print(f"OpenSearch indexing response: {response}")
        
    except Exception as e:
        print(f"Error indexing photo in OpenSearch: {str(e)}")
        raise
