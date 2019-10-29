# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import logging

Monitoring_Topic = os.environ['SNSTopic']

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cpu = {'AlarmName':'CPUUtilization','MetricName':'CPUUtilization','EvaluationPeriods':'5','ComparisonOperator':'GreaterThanOrEqualToThreshold','DimensionName':'InstanceId',
       'Namespace':'AWS/EC2','Period': '120','Statistic':'Average','Threshold':'85','Unit':'Percent'}

statuscheck = {'AlarmName':'StatusCheck','MetricName':'StatusCheckFailed_Instance', 'EvaluationPeriods': '5', 'ComparisonOperator': 'GreaterThanOrEqualToThreshold', 'DimensionName': 'InstanceId',
              'Namespace': 'AWS/EC2', 'Period': '120', 'Statistic': 'Average', 'Threshold': '85', 'Unit': 'Percent'}

alb_5xx_count = {'AlarmName':'5xxErrors','MetricName':'HTTPCode_ELB_5XX_Count', 'EvaluationPeriods': '5', 'ComparisonOperator': 'GreaterThanOrEqualToThreshold', 'DimensionName': 'LoadBalancer',
              'Namespace': 'AWS/ApplicationELB', 'Period': '60', 'Statistic': 'Sum', 'Threshold': '0', 'Unit': 'Count'}

alb_rejected_request_count = {'AlarmName':'RejectedRequests','MetricName':'RejectedConnectionCount', 'EvaluationPeriods': '5', 'ComparisonOperator': 'GreaterThanOrEqualToThreshold', 'DimensionName': 'LoadBalancer',
              'Namespace': 'AWS/ApplicationELB', 'Period': '120', 'Statistic': 'Sum', 'Threshold': '1', 'Unit': 'Count'}

nlb_UnHealthyHostCount = {'AlarmName':'UnHealthyHostCount','MetricName':'UnHealthyHostCount', 'EvaluationPeriods': '1', 'ComparisonOperator': 'GreaterThanOrEqualToThreshold', 'DimensionName': 'LoadBalancer',
              'Namespace': 'AWS/NetworkELB', 'Period': '120', 'Statistic': 'Minimum', 'Threshold': '0', 'Unit': 'Count'}

nlb_HealthyHostCount = {'AlarmName':'HealthyHostCount','MetricName':'HealthyHostCount', 'EvaluationPeriods': '1', 'ComparisonOperator': 'LessThanThreshold', 'DimensionName': 'LoadBalancer',
              'Namespace': 'AWS/NetworkELB', 'Period': '120', 'Statistic': 'Minimum', 'Threshold': '1', 'Unit': 'Count'}

lambda_4xx_count = {'AlarmName':'4xxErrors','MetricName':'Errors', 'EvaluationPeriods': '1', 'ComparisonOperator': 'GreaterThanOrEqualToThreshold', 'DimensionName': 'FunctionName',
                    'Namespace': 'AWS/Lambda', 'Period': '60', 'Statistic': 'Sum', 'Threshold': '5', 'Unit': 'Count'}

lambda_invocations_count = {'AlarmName':'Invocations','MetricName':'Invocations', 'EvaluationPeriods': '1', 'ComparisonOperator': 'GreaterThanOrEqualToThreshold', 'DimensionName': 'FunctionName',
                    'Namespace': 'AWS/Lambda', 'Period': '300', 'Statistic': 'Sum', 'Threshold': '20', 'Unit': 'Count'}

nat_ErrorPortAllocation = {'AlarmName':'ErrorPortAllocations','MetricName':'ErrorPortAllocation', 'EvaluationPeriods': '1', 'ComparisonOperator': 'GreaterThanThreshold', 'DimensionName': 'NatGatewayId',
                    'Namespace': 'AWS/NATGateway', 'Period': '300', 'Statistic': 'Sum', 'Threshold': '0', 'Unit': 'Count'}

nat_ActiveConnectionCount = {'AlarmName':'ActiveConnections','MetricName':'ActiveConnectionCount', 'EvaluationPeriods': '1', 'ComparisonOperator': 'GreaterThanThreshold', 'DimensionName': 'NatGatewayId',
                    'Namespace': 'AWS/NATGateway', 'Period': '300', 'Statistic': 'Maximum', 'Threshold': '100', 'Unit': 'Count'}



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
                logger.info('Resource {} is an EC2'.format(resource))
                condition = condition_checker(resource,resource_json)
                alarms = [cpu, statuscheck]
                generate_alarm(resource,Monitoring_Topic,alarms,alarm_dictionary,condition)
            elif resource_json['Type'] == 'AWS::ElasticLoadBalancingV2::LoadBalancer':
                condition = condition_checker(resource, resource_json)
                lb_type = resource_json['Properties']['Type'].lower()
                if lb_type == 'application':
                    logger.info('Resource {} is an ALB'.format(resource))
                    alarms = [alb_rejected_request_count, alb_5xx_count]
                elif lb_type == 'network':
                    logger.info('Resource {} is an NLB'.format(resource))
                    alarms = [nlb_HealthyHostCount, nlb_UnHealthyHostCount]
                generate_alarm(resource, Monitoring_Topic, alarms, alarm_dictionary, condition)
            elif resource_json['Type'] == 'AWS::EC2::NatGateway':
                logger.info('Resource {} is a NAT Gateway'.format(resource))
                condition = condition_checker(resource, resource_json)
                alarms = [nat_ErrorPortAllocation, nat_ActiveConnectionCount]
                generate_alarm(resource, Monitoring_Topic, alarms, alarm_dictionary, condition)
            elif resource_json['Type'] == 'AWS::Lambda::Function':
                logger.info('Resource {} is a lambda function'.format(resource))
                condition = condition_checker(resource, resource_json)
                alarms = [lambda_4xx_count, lambda_invocations_count]
                generate_alarm(resource, Monitoring_Topic, alarms, alarm_dictionary, condition)
            else:
                logger.info('Resource {} is not of a supported resource type'.format(resource))
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
        logger.info(f'{resource} condition is {condition}')
    else:
        print('No Condition Statement found for {}..'.format(resource))
        condition = 'none'
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