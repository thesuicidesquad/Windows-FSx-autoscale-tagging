import json
import boto3
import math
import os
import codecs
from datetime import datetime, timedelta


def lambda_handler(event, context):
    avail_capacity = get_avail_capacity()
    max_capacity = get_current_max_capacity()
    free_percentage = compute_free_percentage(avail_capacity, max_capacity)
    if free_percentage <= 10:
        increase_capacity(max_capacity)
        print(r"Added FSx storage capacity by {}%".format(os.environ['IncreasePercentage']))
        return {
            'statusCode': 200,
            'body': json.dumps(r"Added FSx storage capacity by {}%".format(os.environ['IncreasePercentage']))
        }
    else:
        print(r"Current available capacity percentage is {}%".format(free_percentage))
        return {
            'statusCode': 200,
            'body': json.dumps(r"Current available capacity percentage is {}%".format(free_percentage))
        }


def get_avail_capacity():
    cloudwatch_client = boto3.client('cloudwatch', region_name='ap-east-1')
    cloudwatch_response = cloudwatch_client.get_metric_statistics(
        Namespace='AWS/FSx',
        MetricName='FreeStorageCapacity',
        Dimensions=[
            {
                'Name': 'FileSystemId',
                'Value': os.environ['FileSystemId']
            },
        ],
        StartTime=datetime.utcnow() - timedelta(minutes=15),
        EndTime=datetime.utcnow(),
        Period=60,
        Statistics=[
            'Minimum'
        ],
        Unit='Bytes'
    )
    datapoint_list = []
    for datapoint in cloudwatch_response["Datapoints"]:
        datapoint_list.append(datapoint["Minimum"])
    min_capacity = min(datapoint_list)
    return min_capacity

def get_current_max_capacity():
    get_fsx_capacity_client = boto3.client('fsx', region_name='ap-east-1')
    get_fsx_capacity_response = get_fsx_capacity_client.describe_file_systems(
        FileSystemIds=[
            os.environ['FileSystemId']
        ]
    )
    max_capacity = (get_fsx_capacity_response["FileSystems"][0]["StorageCapacity"])*1024*1024*1024
    return max_capacity

def compute_free_percentage(current_capacity, max_capacity):
    free_percentage = (current_capacity/max_capacity)*100
    return free_percentage

def increase_capacity(max_capacity):
    target_size = int(round_up((max_capacity/1073741824)*(1 + int(os.environ['IncreasePercentage'])/100)))
    add_fsx_capacity_client = boto3.client('fsx', region_name='ap-east-1')
    add_fsx_capacity_response = add_fsx_capacity_client.update_file_system(
        FileSystemId=os.environ['FileSystemId'],
        StorageCapacity=target_size,
    )
    send_sns_topic_increase_capacity()

def round_up(n, decimals=0): 
    multiplier = 10 ** decimals 
    return math.ceil(n * multiplier) / multiplier

def send_sns_topic_increase_capacity():
    sns_client = boto3.client('sns')
    sns_message = r'FSX file system id {} has reached 90% of available capacity, and the max capacity was increased by {}%'.format(os.environ['FileSystemId'], os.environ['IncreasePercentage'])
    response = sns_client.publish(
        TargetArn=os.environ['SNSId'],
        Message=json.dumps({"Event": sns_message}),
        Subject='FSXCapacityIncrease'
        )
    print('SNS topic was sent')