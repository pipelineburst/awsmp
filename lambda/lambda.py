import json
import boto3
import base64
import urllib.parse as urlparse

#### notes ####
# the code extracts details from the viewer request, hits some aws apis, and retungs the viewer request without modifications
# https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-event-structure.html
#### notes ####
# the stack needs to run in us-east-1 and in the same account from which the marketplace product has been defined
# The marketplace api needs to called from the seller account id used to publish the SaaS application to successfully resolve the token.
# enable cloudfront allowed-methods to all, as otherwise POSTS are being dropped (cf access logs: InvalidRequestMethod)
# on subscription, marketplace sends a application/x-www-form-urlencoded POST request to the fulfillment URL 
# when backing cloudfront with a static s3 webhosting endpoint then POST is not supported - replace POST with GET after extracting marketplace fields
# the lamda function needs aws-marketplace:ResolveCustomer permissions with an identity-based policy that allows the aws-marketplace:ResolveCustomer action. otherwise: permission denied !


CONTENT_DDB = """
<\!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Message from MYCOM OSI - Your Marketplace Registation</title>
</head>
<body>
    <p>Ooops, something went wrong! Cannot write to DDB !</p>
</body>
</html>
"""

CONTENT_MP = """
<\!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Message from MYCOM OSI - Your Marketplace Registation</title>
</head>
<body>
    <p>You are not a subscribed customer!</p>
</body>
</html>
"""

CONTENT_AWSMP_NO_TOKEN = """
<\!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Message from MYCOM OSI - Your Marketplace Registation</title>
</head>
<body>
    <p>You dont have a AWS Marketplace TOKEN! Please contact MYCOM OSI at info@mycom-osi.com</p>
</body>
</html>
"""

CONTENT_AWSMP_TOKEN_NOT_VALID = """
<\!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Message from MYCOM OSI - Your Marketplace Registation</title>
</head>
<body>
    <p>AWS Marketplace responded with a REGISTRATION TOKEN INVALID OR EXPIRED response! Please contact MYCOM OSI at info@mycom-osi.com</p>
</body>
</html>
"""

CONTENT_AWSMP_NO_ENTITLEMENT = """
<\!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Message from MYCOM OSI - Your Marketplace Registation</title>
</head>
<body>
    <p>AWS Marketplace responded with a NO ENTITLEMENT response! Please contact MYCOM OSI at info@mycom-osi.com</p>
</body>
</html>
"""

client = boto3.client('dynamodb', region_name = 'us-east-1')

def lambda_handler(event, context):

    config = event['Records'][0]['cf']['config']
    request = event['Records'][0]['cf']['request']
    
    headers = request['headers']
    host = headers["host"][0]["value"]
    
    method = request["method"]
    client_ip = request["clientIp"]
    request_id = config["requestId"]
    uri = request["uri"]
    
    ### START: test block ###

    if method == "GET":
        
        try:
            response = client.put_item(
                Item={
                    'customer-id': {
                        'S': "Fake_GET",
                    },
                    'method': {
                        'S': method,
                    },
                    'client-ip': {
                        'S': client_ip,
                    },
                    'request-id': {
                        'S': request_id,
                    },
                    'uri': {
                        'S': uri,
                    },
                    'host': {
                        'S': host,
                    },
                },
                ReturnConsumedCapacity='TOTAL',
                TableName='awsmp',
            )
            print("GET TEST LOG:", method, request_id, client_ip, uri)
            print
            
        except Exception as e: 
            print("LOG: Cannt write to DDB")
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
        return request

    ### END: test block ###

    if method == "POST":

        try:        
            print("LOG FULL_REQUEST_OBJECT:", request)
            data = request['body']['data']
            print("LOG DATA:", data)
            PostBody = base64.b64decode(data)
            print("LOG POST_BODY:", PostBody)
            kv = PostBody.decode('ascii')
            print("LOG KV:", kv)
            kvp = urlparse.parse_qs(kv)
            print("LOG KVP:", kvp)
            regToken = kvp['x-amzn-marketplace-token'][0]
            print("LOG TOKEN:", regToken)
        except Exception as e: 
            print("FAIL: No POST body found!")
            print("FAIL: Exception:", e)
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
                    'body': CONTENT_AWSMP_NO_TOKEN
                }
            return response              

        if regToken:
            try:
                # calling the meteringmarketplace api to exchange the token with a customer id
                print("LOG CALLING_AWSMP_WITH_TOKEN: ", regToken)
                marketplaceClient = boto3.client("meteringmarketplace", region_name = 'us-east-1')
                customerData = marketplaceClient.resolve_customer(
                    RegistrationToken=regToken
                )
                print("FULL_RESOLVE_CUSTOMER_RESPONSE: ", customerData)
                
                customer_id = customerData["CustomerIdentifier"]
                print("LOG CUSTOMER_ID: ", customer_id)
                product_code = customerData["ProductCode"]
                print("LOG PRODUCT_CODE: ", product_code)
                customer_account_id = customerData["CustomerAWSAccountId"]
                print("LOG CUSTOMER_ACCOUNT_ID: ", customer_account_id)

            except Exception as e: 
                print("FAIL: Registration token invalid or expired!")
                print("FAIL: Exception:", e)
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
                        'body': CONTENT_AWSMP_TOKEN_NOT_VALID
                    }
                return response                 
            
            try:
                # calling the marketplace-entitlement api to obtain entitlements for the resolved customer id
                marketplaceClient = boto3.client('marketplace-entitlement', region_name='us-east-1')
                productCode = product_code
                customerID = customer_id
                
                entitlement = marketplaceClient.get_entitlements(
                    ProductCode=productCode,
                    Filter={
                        'CUSTOMER_IDENTIFIER': [
                            customerID,
                        ]
                    }
                )
                print("ENTITLEMENT_API_RESPONSE: ", entitlement)
                # entitlement response to processed for now. no requirement. TODO when needed.

            except Exception as e: 
                print("FAIL: No valid entitlements recieved for customer id!")
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
                        'body': CONTENT_AWSMP_NO_ENTITLEMENT
                    }
                return response 

            try:
                # persisting successful customer subscription data (resolved customer id and entitements) into ddb (not writing entitlements to ddb; TODO)
                response = client.put_item(
                    Item={
                        'customer-id': {
                            'S': customer_id,
                        },
                        'account-id': {
                            'S': customer_account_id,
                        },
                        'product-code': {
                            'S': product_code,
                        },
                        'method': {
                            'S': method,
                        },
                        'client-ip': {
                            'S': client_ip,
                        },
                        'request-id': {
                            'S': request_id,
                        },
                        'uri': {
                            'S': uri,
                        },
                        'host': {
                            'S': host,
                        },
                    },
                    ReturnConsumedCapacity='TOTAL',
                    TableName='awsmp',
                )
                print("LOG DATA_WRITTEN_TO_DDB:", customer_id, customer_account_id, product_code, method, client_ip, request_id, uri, host)

            except Exception as e: 
                print("FAIL: Cannot write to DDB!")
                print("FAIL: Exception:", e)
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
                        'body': CONTENT_DDB
                    }
                return response              
    
            response = {
                'status': '302',
                'statusDescription': 'Found',
                'headers': {
                    'location': [{
                        'key': 'Location',
                        'value': 'https://ainsights.acs.saas.mycom-osi.com/'
                    }]
                }
            }
            return response

        else:
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
                    'body': CONTENT_AWSMP_NO_TOKEN
                }
            return response 
