# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    alarm_dictionary = {}
    fragment = event["fragment"]
    monitoring_topic = os.environ['SNSTopic']
    logger.info('Input Template: {}'.format(fragment))
    resources = fragment['Resources']
    for resource in resources:
        logger.info('Searching {} for resource type'.format(resource))
        resource_json = resources[resource]
        try:
            if resource_json['Type'] == 'AWS::EC2::Instance':
                logger.info('Resource {} is an EC2'.format(resource))
                ec2_alarms = ec2(resource,monitoring_topic,resource_json)
                alarm_dictionary.update(ec2_alarms)
            elif resource_json['Type'] == 'AWS::ElasticLoadBalancingV2::LoadBalancer':
                lb_alarms = loadbalancer(resource,monitoring_topic,resource_json)
                alarm_dictionary.update(lb_alarms)
            elif resource_json['Type'] == 'AWS::EC2::NatGateway':
                logger.info('Resource {} is a NAT Gateway'.format(resource))
                natgateway_alarms = natgateway(resource,monitoring_topic,resource_json)
                alarm_dictionary.update(natgateway_alarms)
            elif resource_json['Type'] == 'AWS::Lambda::Function':
                logger.info('Resource {} is a lambda function'.format(resource))
                lambda_alarms = aws_lambda(resource,monitoring_topic,resource_json)
                alarm_dictionary.update(lambda_alarms)
            else:
                logger.info('Resource {} is not of a supported resource type'.format(resource))
        except Exception as e:
            logger.error('ERROR {}'.format(e))
            resp = {
                'requestId': event['requestId'],
                'status': 'failure',
                'fragment': fragment
            }
            return resp
    resources.update(alarm_dictionary)
    logger.info('Final Template: {}'.format(fragment))

    # Send Response to stack
    resp = {
        'requestId': event['requestId'],
        'status': 'success',
        'fragment': fragment
    }
    return resp

def ec2(resource,monitoring_topic,resource_json):
    ec2_dict = {}
    logger.info('Instance Found: {}'.format(resource))
    cpu_alarm = generate_alarm(resource,monitoring_topic,{'AlarmName': 'CPUUtilization', 'MetricName': 'CPUUtilization', 'EvaluationPeriods': '5',
     'ComparisonOperator': 'GreaterThanOrEqualToThreshold', "Dimensions": [{"Name": 'InstanceId',"Value": {"Ref": f'{resource}'}}],
     'Namespace': 'AWS/EC2', 'Period': '120', 'Statistic': 'Average', 'Threshold': '85', 'Unit': 'Percent'},resource_json)
    ec2_dict.update(cpu_alarm)
    statuscheck_failed_alarm = generate_alarm(resource, monitoring_topic, {'AlarmName':'StatusCheck','MetricName':'StatusCheckFailed_Instance', 'EvaluationPeriods': '5', 'ComparisonOperator': 'GreaterThanOrEqualToThreshold',
                                                                           "Dimensions": [{"Name": 'InstanceId',"Value": {"Ref": f'{resource}'}}],
                                                                           'Namespace': 'AWS/EC2', 'Period': '120', 'Statistic': 'Average',
                                                                           'Threshold': '85', 'Unit': 'Percent'},resource_json)
    ec2_dict.update(statuscheck_failed_alarm)
    return ec2_dict


def loadbalancer(resource,monitoring_topic,resource_json):
    lb_dict = {}
    logger.info('Attempting to determine loadbalancer type')
    lb_type = resource_json['Properties']['Type']
    try:
        if lb_type == 'application':
          logger.info('Application Load Balancer Found: {}'.format(resource))
          alb_5xx_count_alarm = generate_alarm(resource, monitoring_topic,
                                               {'AlarmName': '5xx', 'MetricName': 'HTTPCode_ELB_5XX_Count',
                                                'EvaluationPeriods': '5','ComparisonOperator': 'GreaterThanThreshold',
                                                 "Dimensions": [{"Name": "LoadBalancer","Value": {"Fn::GetAtt": [f'{resource}',"LoadBalancerFullName"]}}],
                                                 'Namespace': 'AWS/ApplicationELB', 'Period': '60',
                                                 'Statistic': 'Sum', 'Threshold': '1','Unit': 'Count'},resource_json)
          lb_dict.update(alb_5xx_count_alarm)
          alb_5xx_target_alarm = generate_alarm(resource, monitoring_topic,
                                                {'AlarmName': 'Target5xx', 'MetricName': 'HTTPCode_Target_5XX_Count',
                                                 'EvaluationPeriods': '1',
                                                 'ComparisonOperator': 'GreaterThanThreshold',
                                                 "Dimensions": [{"Name": "LoadBalancer", "Value": {
                                                     "Fn::GetAtt": [f'{resource}',
                                                                    "LoadBalancerFullName"]}}],
                                                 'Namespace': 'AWS/ApplicationELB', 'Period': '60',
                                                 'Statistic': 'Sum', 'Threshold': '1', 'Unit': 'Count'},resource_json)
          lb_dict.update(alb_5xx_target_alarm)
          alb_rejected_request_count = generate_alarm(resource, monitoring_topic,
                                                      {'AlarmName': 'RejectedRequest',
                                                       'MetricName': 'RejectedConnectionCount',
                                                       'EvaluationPeriods': '5',
                                                       'ComparisonOperator': 'GreaterThanThreshold',
                                                       "Dimensions": [{"Name": "LoadBalancer", "Value": {
                                                        "Fn::GetAtt": [f'{resource}',
                                                        "LoadBalancerFullName"]}}],
                                                       'Namespace': 'AWS/ApplicationELB', 'Period': '120',
                                                       'Statistic': 'Sum', 'Threshold': '1',
                                                       'Unit': 'Count'},resource_json)
          lb_dict.update(alb_rejected_request_count)
          return lb_dict
        elif lb_type == 'network':
            logger.info('Network Load Balancer Found: {}'.format(resource))
            nlb_UnHealthyHostCount = generate_alarm(resource, monitoring_topic,
                                           {'AlarmName': 'UnHealthyHostCount', 'MetricName': 'UnHealthyHostCount',
                                            'EvaluationPeriods': '1',
                                            'ComparisonOperator': 'GreaterThanThreshold',
                                            "Dimensions": [{"Name": "LoadBalancer", "Value": {
                                                "Fn::GetAtt": [f'{resource}',
                                                               "LoadBalancerFullName"]}}],
                                            'Namespace': 'AWS/NetworkELB', 'Period': '60',
                                            'Statistic': 'Sum', 'Threshold': '1', 'Unit': 'Count'},resource_json)
            lb_dict.update(nlb_UnHealthyHostCount)
            nlb_HealthyHostCount = generate_alarm(resource, monitoring_topic,
                                                 {'AlarmName': 'HealthyHostCount',
                                                  'MetricName': 'nlb_HealthyHostCount',
                                                  'EvaluationPeriods': '5',
                                                  'ComparisonOperator': 'GreaterThanThreshold',
                                                  "Dimensions": [{"Name": "LoadBalancer", "Value": {
                                                      "Fn::GetAtt": [f'{resource}',
                                                                     "LoadBalancerFullName"]}}],
                                                  'Namespace': 'AWS/NetworkELB', 'Period': '120',
                                                  'Statistic': 'Sum', 'Threshold': '1',
                                                  'Unit': 'Count'},resource_json)
            lb_dict.update(nlb_HealthyHostCount)
            return lb_dict
        else:
          logger.error('Cannot find LB_TYPE Tag for {}'.format(resource))
          raise
    except Exception as e:
        logger.error('Cannot Handle {}'.format(e))
        raise e

def aws_lambda(resource,monitoring_topic,resource_json):
    lambda_dict = {}
    lambda_4xx_count = generate_alarm(resource, monitoring_topic,
                                          {'AlarmName': '4xxErrors', 'MetricName': 'Errors',
                                           'EvaluationPeriods': '1',
                                           'ComparisonOperator': 'GreaterThanThreshold',
                                           "Dimensions": [{"Name": 'FunctionName',"Value": {"Ref": f'{resource}'}}],
                                           'Namespace': 'AWS/Lambda', 'Period': '60',
                                           'Statistic': 'Sum', 'Threshold': 0, 'Unit': 'Count'},resource_json)
    lambda_dict.update(lambda_4xx_count)
    lambda_invocations_count = generate_alarm(resource, monitoring_topic,
                                       {'AlarmName': 'Invocations', 'MetricName': 'Invocations',
                                        'EvaluationPeriods': '1',
                                        'ComparisonOperator': 'GreaterThanThreshold',
                                        "Dimensions": [{"Name": 'FunctionName',"Value": {"Ref": f'{resource}'}}],
                                        'Namespace': 'AWS/Lambda', 'Period': '60',
                                        'Statistic': 'Sum', 'Threshold': 0,
                                        'Unit': 'Count'},resource_json)
    lambda_dict.update(lambda_invocations_count)
    return lambda_dict



def natgateway(resource,monitoring_topic,resource_json):
    natgateway_dict = {}
    nat_ErrorPortAllocation = generate_alarm(resource, monitoring_topic,
                                      {'AlarmName': 'ErrorPortAllocations', 'MetricName': 'ErrorPortAllocation',
                                       'EvaluationPeriods': '1',
                                       'ComparisonOperator': 'GreaterThanThreshold',
                                       "Dimensions": [{"Name": 'NatGatewayId',"Value": {"Ref": f'{resource}'}}],
                                       'Namespace': 'AWS/NATGateway', 'Period': '300',
                                       'Statistic': 'Sum', 'Threshold': 0, 'Unit': 'Count'},resource_json)
    natgateway_dict.update(nat_ErrorPortAllocation)
    nat_ActiveConnectionCount = generate_alarm(resource, monitoring_topic,
                                              {'AlarmName': 'ActiveConnections', 'MetricName': 'ActiveConnectionCount',
                                               'EvaluationPeriods': '1',
                                               'ComparisonOperator': 'GreaterThanThreshold',
                                               "Dimensions": [{"Name": 'NatGatewayId',"Value": {"Ref": f'{resource}'}}],
                                               'Namespace': 'AWS/NATGateway', 'Period': '300',
                                               'Statistic': 'Maximum', 'Threshold': 20,
                                               'Unit': 'Count'},resource_json)
    natgateway_dict.update(nat_ActiveConnectionCount)
    return natgateway_dict




def generate_alarm(resource,monitoring_topic,alarm,resource_json):
    alarm_template = {f'{resource}{alarm["AlarmName"]}': {
        "Type": "AWS::CloudWatch::Alarm",
        "Properties": {
            "ActionsEnabled": "true",
            "AlarmActions": [monitoring_topic],
            "InsufficientDataActions": [monitoring_topic],
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
            "Dimensions": alarm["Dimensions"],
            "MetricName": f'{alarm["MetricName"]}',
            "Namespace": f'{alarm["Namespace"]}',
            "Period": f'{alarm["Period"]}',
            "Statistic": f'{alarm["Statistic"]}',
            "Threshold": f'{alarm["Threshold"]}',
            "Unit": f'{alarm["Unit"]}'
        }
    }}
    condition = resource_json.get('Condition')
    if condition != None:
        alarm_template[f'{resource}{alarm["AlarmName"]}']["Condition"] = condition
        return alarm_template
    else:
        return alarm_template
