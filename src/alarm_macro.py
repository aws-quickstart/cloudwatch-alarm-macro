# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import logging

Monitoring_Topic = os.environ['Monitoring_Topic']

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cpu = {'AlarmName':'CPUUtilization','MetricName':'CPUUtilization','EvaluationPeriods':'5','ComparisonOperator':'GreaterThanOrEqualToThreshold','DimensionName':'InstanceId',
       'Namespace':'AWS/EC2','Period': '120','Statistic':'Average','Threshold':'85','Unit':'Percent'}

statuscheck = {'AlarmName':'StatusCheck','MetricName':'StatusCheckFailed_Instance', 'EvaluationPeriods': '5', 'ComparisonOperator': 'GreaterThanOrEqualToThreshold', 'DimensionName': 'InstanceId',
              'Namespace': 'AWS/EC2', 'Period': '120', 'Statistic': 'Average', 'Threshold': '85', 'Unit': 'Percent'}

def handler(event, context):
    alarm_dictionary = {}
    Input = event["fragment"]
    logger.info('Input Template: {}'.format(Input))
    resources = Input['Resources']
    for resource in resources:
        logger.info('Searching {} for resource type'.format(resource))
        resource_json = resources[resource]
        try:
            if resource_json['Type'] == 'AWS::EC2::Instance':
                condition = condition_checker(resource,resource_json)
                alarms = [cpu, statuscheck]
                generate_alarm(resource,Monitoring_Topic,alarms,alarm_dictionary,condition)
            else:
                logger.info('Resource {} is not a supported type'.format(resource))
        except Exception as e:
            logger.error('ERROR {}'.format(e))
            resp = {
                'requestId': event['requestId'],
                'status': 'failure',
                'fragment': Input
            }

            return resp

    resources.update(alarm_dictionary)
    print(Input)
    logger.info('Final Template: {}'.format(Input))

    # Send Response to stack
    resp = {
        'requestId': event['requestId'],
        'status': 'success',
        'fragment': Input
    }
    return resp


def condition_checker(resource, resource_json):
    if 'Condition' in resource_json:
        print('Condition found for {}'.format(resource))
        condition = resource_json['Condition']
    else:
        print('No Condition Statement found for {}..'.format(resource))
        condition = 'none'
    logger.info(f'{resource} condition is {condition}')
    return condition

def generate_alarm(resource,Monitoring_Topic,alarms,alarm_dictionary,condition):

    for alarm in alarms:
        alarm_json = {f'{resource}{alarm["AlarmName"]}':{
                    "Type": "AWS::CloudWatch::Alarm",
                    "Properties": {
                        "ActionsEnabled": "true",
                        "AlarmActions": [f'{Monitoring_Topic}'],
                        "AlarmDescription": {
                            "Fn::Join": [
                                " - ", [
                                    f'{alarm["MetricName"]}',
                                    {
                                        "Ref": f'{resource}'
                                    }
                                ]
                            ]
                        },
                        "AlarmName": {
                            "Fn::Join": [
                                "-", [
                                    {
                                        "Ref": "AWS::StackName"
                                    },
                                    f'{resource}',
                                    f'{alarm["MetricName"]}'
                                ]
                            ]
                        },
                        'EvaluationPeriods': f'{alarm["EvaluationPeriods"]}',
                        "ComparisonOperator": f'{alarm["ComparisonOperator"]}',
                        "Dimensions": [{
                            "Name": f'{alarm["DimensionName"]}',
                            "Value": {"Ref": f'{resource}'}}],
                        "InsufficientDataActions": [f'{Monitoring_Topic}'],
                        "MetricName": f'{alarm["MetricName"]}',
                        "Namespace": f'{alarm["Namespace"]}',
                        "Period": f'{alarm["Period"]}',
                        "Statistic": f'{alarm["Statistic"]}',
                        "Threshold": f'{alarm["Threshold"]}',
                        "Unit": f'{alarm["Unit"]}'
                    }
                }}
        if condition != 'none':
            alarm_json[f'{resource}{alarm["AlarmName"]}']["Condition"]= condition
            alarm_dictionary.update(alarm_json)
        else:
            alarm_dictionary.update(alarm_json)