# cloudwatch-alert-macro

CloudFormation Macro that will append a set of CloudWatch alarms for supported resources.

## Included alarms
Amazon Elastic Compute Cloud (Amazon EC2), load balancers, Lambda, and Network address translation (NAT) gateways

|Service | Alarm   | Description  |
|---|---|---|
|Amazon EC2  | CPUUtilization  | CPU utilization percentage  |
|Amazon EC2  |  StatusCheckFailed_Instance |  Health check for the instance |
|Application Load Balancer  | HTTPCode_ELB_5XX_Count  |   The number of HTTP 5XX server error codes that originate from the load balancer|
|Application Load Balancer | RejectedConnectionCount  |  Rejected connections due to the load balancer reaching its maximum number of connections |
|Network Load Balancer |  UnHealthyHostCount |  The number of targets that are considered unhealthy |
|Network Load Balancer  | HealthyHostCount  |  The number of targets that are considered healthy |
|Lambda  |  Errors | The number of invocations that failed due to errors in the function (response code 4XX)  |
|Lambda  |  Invocations |  The number of times a function is invoked in response to an event or invocation API call |
|NAT Gateway |  ErrorPortAllocation | The number of times the NAT gateway could not allocate a source port  |
|NAT Gateway  | ActiveConnectionCount  |  The total number of concurrent active TCP connections through the NAT gateway |

## usage

To use the macro, add the following line to the top of your templates:

Transform: AlarmMacro


## macro order for serverless templates

If you are deploying a serverless template please ensure you list this macro after the serverless transform

Transform: ["AWS::Serverless-2016-10-31", "AlarmMacro"]
