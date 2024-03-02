import json
import boto3
import base64
import urllib.parse as urlparse

# returning request without modifications
# https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-event-structure.html

CONTENT = """
<\!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Lambda@Edge Static Content Response</title>
</head>
<body>
    <p>Something went wrong!</p>
</body>
</html>
"""

client = boto3.client('dynamodb', region_name = 'us-east-1')

def lambda_handler(event, context):
    ### some boto actions ###
    client_ip = event['Records'][0]['cf']['request']['clientIp']
    method = event['Records'][0]['cf']['request']['method']
    request_id = event['Records'][0]['cf']['config']['requestId']

    if method == "GET":
        try:
            response = client.put_item(
                Item={
                    'customer-id': {
                        'S': "Fake",
                    },
                    'method': {
                        'S': method,
                    },
                    'client-ip': {
                        'S': client_ip
                    },
                    'request-id': {
                        'S': request_id
                    },
                },
                ReturnConsumedCapacity='TOTAL',
                TableName='awsmp',
            )
        except Exception as e: 
            response = {
                    'status': '200',
                    'statusDescription': 'OK',
                    'headers': {
                        'cache-control': [
                            {
                                'key': 'Cache-Control',
                                'value': 'max-age=100'
                            }
                        ],
                        "content-type": [
                            {
                                'key': 'Content-Type',
                                'value': 'text/html'
                            }
                        ]
                    },
                    'body': CONTENT
                }
            return response

    if method == "POST":    
        try:
            formFields = urlparse.parse_qs(PostBody)
            regToken = formFields["x-amzn-marketplace-token"]
            if (regToken):
                marketplaceClient = boto3.client("meteringmarketplace")
                customerData = marketplaceClient.resolve_customer(regToken)
                productCode = customerData["ProductCode"]
                customerID = cusdtomerData["CustomerIdentifier"]
                try:
                    response = client.put_item(
                        Item={
                            'customer-id': {
                                'S': customerID,
                            },
                            'product-code': {
                                'S': productCode,
                            },
                            'Entitlement': {
                                'S': 'Not in use',
                            },
                        },
                        ReturnConsumedCapacity='TOTAL',
                        TableName='awsmp',
                    )
                except Exception as e: 
                    response = {
                            'status': '200',
                            'statusDescription': 'OK',
                            'headers': {
                                'cache-control': [
                                    {
                                        'key': 'Cache-Control',
                                        'value': 'max-age=100'
                                    }
                                ],
                                "content-type": [
                                    {
                                        'key': 'Content-Type',
                                        'value': 'text/html'
                                    }
                                ]
                            },
                            'body': CONTENT
                        }
                    return response
        except:
            response = {
                'status': '200',
                'statusDescription': 'OK',
                'headers': {
                    'cache-control': [
                        {
                            'key': 'Cache-Control',
                            'value': 'max-age=100'
                        }
                    ],
                    "content-type": [
                        {
                            'key': 'Content-Type',
                            'value': 'text/html'
                        }
                    ]
                },
                'body': CONTENT
            }
        return response    

    ### returning the unchanged request  ###    
    request = event['Records'][0]['cf']['request']
    return request