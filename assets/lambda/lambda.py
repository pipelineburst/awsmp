import json
import boto3
from time import sleep
import urllib
import os

client = boto3.client('dynamodb')

def lambda_handler(event, context):
    print(event)