"""CDK app for the hello demo: Lambda + HTTP API + timeout alarm wired to the AIF topic."""

from __future__ import annotations

import os
from pathlib import Path

import aws_cdk as cdk
from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as integrations,
    aws_cloudwatch as cw,
    aws_cloudwatch_actions as cw_actions,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_sns as sns,
)
from constructs import Construct

ROOT = Path(__file__).resolve().parent.parent


class HelloStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, alarm_topic_arn: str | None, **kwargs: object) -> None:
        super().__init__(scope, construct_id, **kwargs)  # type: ignore[arg-type]
        log_group = logs.LogGroup(
            self, "ApiLogs", log_group_name="/aws/lambda/aif-hello-api",
            retention=logs.RetentionDays.ONE_MONTH, removal_policy=RemovalPolicy.DESTROY,
        )
        fn = lambda_.Function(
            self, "Api", function_name="aif-hello-api",
            runtime=lambda_.Runtime.PYTHON_3_12, handler="api.handler",
            code=lambda_.Code.from_asset(str(ROOT / "app")),
            timeout=Duration.seconds(5), memory_size=256, log_group=log_group,
        )
        api = apigwv2.HttpApi(self, "HttpApi", api_name="aif-hello")
        integration = integrations.HttpLambdaIntegration("ApiIntegration", fn)
        api.add_routes(path="/", methods=[apigwv2.HttpMethod.GET], integration=integration)
        api.add_routes(path="/hello", methods=[apigwv2.HttpMethod.GET], integration=integration)

        # Every `ERROR TimeoutError` log line counts one; the alarm is the AIF trigger.
        metric_filter = logs.MetricFilter(
            self, "TimeoutErrors", log_group=log_group,
            filter_pattern=logs.FilterPattern.all_terms("ERROR", "TimeoutError"),
            metric_namespace="AifHello", metric_name="TimeoutErrors", metric_value="1",
        )
        alarm = cw.Alarm(
            self, "TimeoutAlarm", alarm_name="hello-api-timeouts",
            metric=metric_filter.metric(statistic="Sum", period=Duration.minutes(1)),
            threshold=3, evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            alarm_description="hello-api: helloWorld(id) exceeded the 200 ms budget 3+ times in a minute",
        )
        if alarm_topic_arn:
            topic = sns.Topic.from_topic_arn(self, "AifTopic", alarm_topic_arn)
            alarm.add_alarm_action(cw_actions.SnsAction(topic))
        CfnOutput(self, "ApiUrl", value=api.api_endpoint)
        CfnOutput(self, "LogGroup", value=log_group.log_group_name)
        CfnOutput(self, "AlarmName", value=alarm.alarm_name)


app = cdk.App()
HelloStack(
    app, "AifHello",
    env=cdk.Environment(account=os.environ.get("CDK_DEFAULT_ACCOUNT"), region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1")),
    alarm_topic_arn=os.environ.get("AIF_ALARM_TOPIC_ARN"),
)
app.synth()
