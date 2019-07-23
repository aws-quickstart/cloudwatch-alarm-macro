# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import logging

Monitoring_Topic = os.environ['SNSTopic']

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    alarm_dictionary = {}
    Input = event["fragment"]
    logger.info('Input Template: {}'.format(Input))
    resources = Input['Resources']
    for resource in resources:
        logger.info('Searching {} for resource type'.format(resource))
        properties = resources[resource]
        try:
            if properties['Type'] == 'AWS::EC2::Instance':
                ec2(resource, alarm_dictionary)
            elif properties['Type'] == 'AWS::ElasticLoadBalancingV2::LoadBalancer':
                load_balancer(resource, properties, alarm_dictionary)
            elif properties['Type'] == 'AWS::EC2::NatGateway':
                Nat_Gateway(resource, alarm_dictionary)
            elif properties['Type'] == 'AWS::Lambda::Function':
                AWS_lambda(resource, alarm_dictionary)
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
    logger.info('Final Template: {}'.format(Input))

    # Send Response to stack
    resp = {
        'requestId': event['requestId'],
        'status': 'success',
        'fragment': Input
    }
    return resp


def ec2(resource, alarm_dictionary):
    logger.info('Instance Found: {}'.format(resource))
    cpu_alarm = {f'{resource}CpuAlarm': {
        "Type": "AWS::CloudWatch::Alarm",
        "Properties": {
            "ActionsEnabled": "true",
            "AlarmActions": [f'{Monitoring_Topic}'],
            "AlarmDescription": {
                "Fn::Join": [
                    " - ", [
                        "CPU Utilization Alarm",
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
                        "CPU-Utilization"
                    ]
                ]
            },
            'EvaluationPeriods': '5',
            "ComparisonOperator": "GreaterThanOrEqualToThreshold",
            "Dimensions": [{
                "Name": "InstanceId",
                "Value": {"Ref": f'{resource}'}}],
            "InsufficientDataActions": [f'{Monitoring_Topic}'],
            "MetricName": "CPUUtilization",
            "Namespace": "AWS/EC2",
            "Period": "120",
            "Statistic": "Average",
            "Threshold": "85",
            "Unit": "Percent"
        }
    }}
    alarm_dictionary.update(cpu_alarm)
    status_check_failed = {f'{resource}StatusCheckFailed': {
        "Type": "AWS::CloudWatch::Alarm",
        "Properties": {
            "ActionsEnabled": "true",
            "AlarmActions": [f'{Monitoring_Topic}'],
            "AlarmDescription": {
                "Fn::Join": [
                    " - ", [
                        "StatusCheckFailed Alarm",
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
                        "StatusCheckFailed"
                    ]
                ]
            },
            'EvaluationPeriods': '3',
            "ComparisonOperator": "GreaterThanThreshold",
            "Dimensions": [{
                "Name": "InstanceId",
                "Value": {"Ref": f'{resource}'}}],
            "InsufficientDataActions": [f'{Monitoring_Topic}'],
            "MetricName": "StatusCheckFailed_Instance",
            "Namespace": "AWS/EC2",
            "Period": "60",
            "Statistic": "Average",
            "Threshold": "0"
        }
    }}
    alarm_dictionary.update(status_check_failed)


def load_balancer(resource, properties, alarm_dictionary):
    lb_type = properties['Properties']['Type']
    try:
        if lb_type == 'application':
            logger.info('Application Load Balancer Found: {}'.format(resource))
            alb_5XX_count_alarm = {f'{resource}5xx': {
                "Type": "AWS::CloudWatch::Alarm",
                "Properties": {
                    "ActionsEnabled": "true",
                    "AlarmActions": [f'{Monitoring_Topic}'],
                    "AlarmDescription": {
                        "Fn::Join": [
                            " - ", [
                                "ALB 5XX Alarm",
                                "The number of HTTP 5XX server error codes that originate from the load balancer."
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
                                "5XX"
                            ]
                        ]
                    },
                    'EvaluationPeriods': '5',
                    "ComparisonOperator": "GreaterThanOrEqualToThreshold",
                    "Dimensions": [{
                        "Name": "LoadBalancer",
                        "Value": {"Ref": f'{resource}'}}],
                    "InsufficientDataActions": [f'{Monitoring_Topic}'],
                    "MetricName": "HTTPCode_ELB_5XX_Count",
                    "Namespace": "AWS/ApplicationELB",
                    "Period": "60",
                    "Statistic": "Sum",
                    "Threshold": "0",
                    "Unit": "Count"
                }
            }}
            alarm_dictionary.update(alb_5XX_count_alarm)
            alb_rejected_request_count = {f'{resource}RejectedCount': {
                "Type": "AWS::CloudWatch::Alarm",
                "Properties": {
                    "ActionsEnabled": "true",
                    "AlarmActions": [f'{Monitoring_Topic}'],
                    "AlarmDescription": {
                        "Fn::Join": [
                            " - ", [
                                "ALB Rejected Request Count Alarm",
                                "Rejected Connections due to the load balancer reaching its maximum number of connections."
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
                                "RejectedRequestCount"
                            ]
                        ]
                    },
                    'EvaluationPeriods': '5',
                    "ComparisonOperator": "GreaterThanOrEqualToThreshold",
                    "Dimensions": [{
                        "Name": "LoadBalancer",
                        "Value": {"Ref": f'{resource}'}}],
                    "InsufficientDataActions": [f'{Monitoring_Topic}'],
                    "MetricName": "RejectedConnectionCount",
                    "Namespace": "AWS/ApplicationELB",
                    "Period": "120",
                    "Statistic": "Sum",
                    "Threshold": "1",
                    "Unit": "Count"
                }
            }}
            alarm_dictionary.update(alb_rejected_request_count)
        elif lb_type == 'network':
            logger.info('Network Load Balancer Found: {}'.format(resource))
            NLB_UnHealthyHostCount = {f'{resource}UnHealthyHostCount': {
                "Type": "AWS::CloudWatch::Alarm",
                "Properties": {
                    "ActionsEnabled": "true",
                    "AlarmActions": [f'{Monitoring_Topic}'],
                    "AlarmDescription": {
                        "Fn::Join": [
                            " - ", [
                                "NLB-UnHealthyHostCount",
                                "The number of targets that are considered unhealthy."
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
                                "UnHealthyHostCount"
                            ]
                        ]
                    },
                    'EvaluationPeriods': '1',
                    "ComparisonOperator": "GreaterThanOrEqualToThreshold",
                    "Dimensions": [{
                        "Name": "LoadBalancer",
                        "Value": {"Ref": f'{resource}'}}],
                    "InsufficientDataActions": [f'{Monitoring_Topic}'],
                    "MetricName": "UnHealthyHostCount",
                    "Namespace": "AWS/NetworkELB",
                    "Period": "120",
                    "Statistic": "Minimum",
                    "Threshold": "0",
                    "Unit": "Count"
                }
            }}
            alarm_dictionary.update(NLB_UnHealthyHostCount)
            NLB_HealthyHostCount = {f'{resource}HealthyHostCount': {
                "Type": "AWS::CloudWatch::Alarm",
                "Properties": {
                    "ActionsEnabled": "true",
                    "AlarmActions": [f'{Monitoring_Topic}'],
                    "AlarmDescription": {
                        "Fn::Join": [
                            " - ", [
                                "NLB-HealthyHostCount",
                                "The number of targets that are considered healthy."
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
                                "HealthyHostCount"
                            ]
                        ]
                    },
                    'EvaluationPeriods': '1',
                    "ComparisonOperator": "LessThanThreshold",
                    "Dimensions": [{
                        "Name": "LoadBalancer",
                        "Value": {"Ref": f'{resource}'}}],
                    "InsufficientDataActions": [f'{Monitoring_Topic}'],
                    "MetricName": "HealthyHostCount",
                    "Namespace": "AWS/NetworkELB",
                    "Period": "120",
                    "Statistic": "Maximum",
                    "Threshold": "1",
                    "Unit": "Count"
                }
            }}
            alarm_dictionary.update(NLB_HealthyHostCount)
    except Exception as e:
        logger.error('Unknown Load Balancer Type'.format(e))
        raise

def AWS_lambda(resource, alarm_dictionary):
    logger.info('Lambda Found: {}'.format(resource))
    lambda_4XX_errors = {f'{resource}4xx': {
        "Type": "AWS::CloudWatch::Alarm",
        "Properties": {
            "ActionsEnabled": "true",
            "AlarmActions": [f'{Monitoring_Topic}'],
            "AlarmDescription": {
                "Fn::Join": [
                    " - ", [
                        "Errors",
                        "Measures the number of invocations that failed due to errors in the function (response code 4XX)."
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
                        "4XX"
                    ]
                ]
            },
            'EvaluationPeriods': '5',
            "ComparisonOperator": "GreaterThanOrEqualToThreshold",
            "Dimensions": [{
                "Name": "FunctionName",
                "Value": {"Ref": f'{resource}'}}],
            "InsufficientDataActions": [f'{Monitoring_Topic}'],
            "MetricName": "Errors",
            "Namespace": "AWS/Lambda",
            "Period": "60",
            "Statistic": "Sum",
            "Threshold": "5",
            "Unit": "Count"
        }
    }}
    alarm_dictionary.update(lambda_4XX_errors)
    lambda_Invocations = {f'{resource}Invocations': {
        "Type": "AWS::CloudWatch::Alarm",
        "Properties": {
            "ActionsEnabled": "true",
            "AlarmActions": [f'{Monitoring_Topic}'],
            "AlarmDescription": {
                "Fn::Join": [
                    " - ", [
                        "Invocations",
                        "Measures the number of times a function is invoked in response to an event or invocation API call."
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
                        "Invocations"
                    ]
                ]
            },
            'EvaluationPeriods': '1',
            "ComparisonOperator": "GreaterThanOrEqualToThreshold",
            "Dimensions": [{
                "Name": "FunctionName",
                "Value": {"Ref": f'{resource}'}}],
            "InsufficientDataActions": [f'{Monitoring_Topic}'],
            "MetricName": "Invocations",
            "Namespace": "AWS/Lambda",
            "Period": "300",
            "Statistic": "Sum",
            "Threshold": "20",
            "Unit": "Count"
        }
    }}
    alarm_dictionary.update(lambda_Invocations)

def Nat_Gateway(resource, alarm_dictionary):
    logger.info('NAT Gateway Found: {}'.format(resource))
    Nat_ErrorPortAllocation = {f'{resource}ErrorPortAllocation': {
        "Type": "AWS::CloudWatch::Alarm",
        "Properties": {
            "ActionsEnabled": "true",
            "AlarmActions": [f'{Monitoring_Topic}'],
            "AlarmDescription": {
                "Fn::Join": [
                    " - ", [
                        "NatGateway ErrorPortAllocation Alarm",
                        "The number of times the NAT gateway could not allocate a source port."
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
                        "ErrorPortAllocation"
                    ]
                ]
            },
            'EvaluationPeriods': '1',
            "ComparisonOperator": "GreaterThanThreshold",
            "Dimensions": [{
                "Name": "NatGatewayId",
                "Value": {"Ref": f'{resource}'}}],
            "InsufficientDataActions": [f'{Monitoring_Topic}'],
            "MetricName": "ErrorPortAllocation",
            "Namespace": "AWS/NATGateway",
            "Period": "300",
            "Statistic": "Sum",
            "Threshold": "0"
        }
    }}
    alarm_dictionary.update(Nat_ErrorPortAllocation)
    Nat_ActiveConnectionCount = {f'{resource}ActiveConnectionCount': {
        "Type": "AWS::CloudWatch::Alarm",
        "Properties": {
            "ActionsEnabled": "true",
            "AlarmActions": [f'{Monitoring_Topic}'],
            "AlarmDescription": {
                "Fn::Join": [
                    " - ", [
                        "NatGateway ActiveConnectionCount Alarm",
                        "The total number of concurrent active TCP connections through the NAT gateway"
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
                        "ActiveConnectionCount"
                    ]
                ]
            },
            'EvaluationPeriods': '1',
            "ComparisonOperator": "GreaterThanThreshold",
            "Dimensions": [{
                "Name": "NatGatewayId",
                "Value": {"Ref": f'{resource}'}}],
            "InsufficientDataActions": [f'{Monitoring_Topic}'],
            "MetricName": "ActiveConnectionCount",
            "Namespace": "AWS/NATGateway",
            "Period": "300",
            "Statistic": "Maximum",
            "Threshold": "100",
            "Unit": "Count"
        }
    }}
    alarm_dictionary.update(Nat_ActiveConnectionCount)


