import json
import boto3
import os
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
# Initialize AWS clients
lex_client = boto3.client('lexv2-runtime')

# OpenSearch configuration
OPENSEARCH_HOST = os.environ.get('OPENSEARCH_HOST')
OPENSEARCH_REGION = os.environ.get('AWS_REGION', 'us-east-1')
INDEX_NAME = 'photos'

# Lex configuration
LEX_BOT_ID = os.environ.get('LEX_BOT_ID')
LEX_BOT_ALIAS_ID = os.environ.get('LEX_BOT_ALIAS_ID')
LEX_LOCALE_ID = os.environ.get('LEX_LOCALE_ID', 'en_US')

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
    Lambda function to search photos using Amazon Lex and OpenSearch.
    
    Steps:
    1. Extract search query from API Gateway event
    2. Disambiguate query using Amazon Lex
    3. Extract keywords from Lex response
    4. Search OpenSearch for matching photos
    5. Return results
    """
    
    print(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract query parameter from API Gateway event
        # Handle case where queryStringParameters might be None
        query_params = event.get('queryStringParameters') or {}
        query = query_params.get('q', '')
        
        if not query:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET,OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'results': [],
                    'message': 'Query parameter "q" is required'
                })
            }
        
        print(f"Search query: {query}")
        
        # Step 1: Disambiguate query using Amazon Lex
        keywords = disambiguate_query(query)
        print(f"Extracted keywords: {keywords}")
        
        # Step 2: Search OpenSearch if keywords found
        if keywords:
            results = search_opensearch(keywords)
            print(f"Search results: {results}")
            
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET,OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'results': results
                })
            }
        else:
            # No keywords found, return empty results
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET,OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'results': []
                })
            }
    
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'results': [],
                'error': str(e)
            })
        }

def disambiguate_query(query):
    """
    Use Amazon Lex to disambiguate search query and extract keywords.
    
    Args:
        query: Search query string
        
    Returns:
        List of keyword strings
    """
    try:
        # Generate a unique session ID for this request
        import uuid
        session_id = str(uuid.uuid4())
        
        response = lex_client.recognize_text(
            botId=LEX_BOT_ID,
            botAliasId=LEX_BOT_ALIAS_ID,
            localeId=LEX_LOCALE_ID,
            sessionId=session_id,
            text=query
        )
        
        print(f"Lex response: {json.dumps(response, default=str)}")
        
        # Extract slots from the response
        slots = response.get('sessionState', {}).get('intent', {}).get('slots', {})
        
        keywords = []
        
        # Extract keyword slots (K1, K2, etc.)
        # Adjust based on your Lex bot slot names
        for slot_name, slot_value in slots.items():
            if slot_value and 'value' in slot_value:
                resolved_value = slot_value['value'].get('resolvedValues', [])
                if resolved_value:
                    keywords.extend([kw.lower() for kw in resolved_value])
                else:
                    original_value = slot_value['value'].get('originalValue', '')
                    if original_value:
                        keywords.append(original_value.lower())
        
        # Remove duplicates while preserving order
        keywords = list(dict.fromkeys(keywords))
        
        return keywords
        
    except Exception as e:
        print(f"Error disambiguating query with Lex: {str(e)}")
        # Fallback: split query by spaces if Lex fails
        return [word.strip().lower() for word in query.split() if word.strip()]

def search_opensearch(keywords):
    """
    Search OpenSearch index for photos matching the keywords.
    
    Args:
        keywords: List of keyword strings
        
    Returns:
        List of photo objects with url and labels
    """
    try:
        opensearch_client = get_opensearch_client()
        
        # Build query to match any of the keywords in labels array
        query = {
            "query": {
                "bool": {
                    "should": [
                        {"match": {"labels": keyword}} for keyword in keywords
                    ],
                    "minimum_should_match": 1
                }
            },
            "size": 100
        }
        
        print(f"OpenSearch query: {json.dumps(query)}")
        
        response = opensearch_client.search(
            index=INDEX_NAME,
            body=query
        )
        
        # Extract results
        hits = response.get('hits', {}).get('hits', [])
        
        results = []
        for hit in hits:
            source = hit['_source']
            bucket = source.get('bucket')
            object_key = source.get('objectKey')
            labels = source.get('labels', [])
            
            # Generate S3 URL
            photo_url = f"https://{bucket}.s3.amazonaws.com/{object_key}"
            
            results.append({
                'url': photo_url,
                'labels': labels
            })
        
        return results
        
    except Exception as e:
        print(f"Error searching OpenSearch: {str(e)}")
        return []

