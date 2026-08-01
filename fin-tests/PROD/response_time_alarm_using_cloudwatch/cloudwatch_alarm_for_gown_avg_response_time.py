import boto3
import time
import os

# ---------- CONFIGURATION ----------
REGION = os.getenv('AWS_REGION', 'us-east-2')
LOG_GROUP = 'apache-error-log-prod'  # PROD log group
NAMESPACE = 'Custom/ResponseTime'
METRIC_NAME = 'AverageResponseTime'

# Specific client to monitor
CLIENT = 'gown'

# Alarm name prefix (we'll suffix with the client name)
ALARM_NAME_PREFIX = 'PROD-HighAverageResponseTimeAlarmWithNotification'

# Trigger alarm when avg response time for this client > 200 ms
THRESHOLD_MS = 300.0

# SNS topic used by Dev Team (must have SMS/email subscriptions configured in AWS)
SNS_TOPIC_ARN = 'arn:aws:sns:us-east-2:342120782706:Dev-Team-Alarms'
# ----------------------------------

# Initialize clients
logs = boto3.client('logs', region_name=REGION)
cloudwatch = boto3.client('cloudwatch', region_name=REGION)

# Step 0: Validate log group existence
print("Validating log group existence...")
log_groups = logs.describe_log_groups(logGroupNamePrefix=LOG_GROUP)
if not any(group['logGroupName'] == LOG_GROUP for group in log_groups.get('logGroups', [])):
    print(f"[ERROR] Log group '{LOG_GROUP}' does not exist in region '{REGION}'.")
    exit(1)

# Step 1: Run CloudWatch Logs Insights query (scoped to gocu client)
print(f"Starting CloudWatch Logs Insights query for client '{CLIENT}'...")

query_string = f"""
fields @timestamp, @message
| filter @message like "total response time:"
| parse @message "[*] [*] [pid *:tid *] [remote *:*] total response time: * * * * *"
    as log_date, error_type, pid, tid, client_ip, client_port, env, client, url, init_response_time, total_response_time
| filter url == "/" and total_response_time != "" and total_response_time < 60000 and client == "{CLIENT}"
| stats avg(total_response_time) as avg_total_response_time,
        max(total_response_time) as max_total_response_time,
        min(total_response_time) as min_total_response_time,
        count() as total_samples,
        sum(if(total_response_time > 30000, 1, 0)) as count_high_response_over_30s
| sort client asc
"""

# Time range: last 24 hours
start_query_response = logs.start_query(
    logGroupName=LOG_GROUP,
    startTime=int(time.time() - 86400),  # last 24 hours
    endTime=int(time.time()),
    queryString=query_string,
)

query_id = start_query_response['queryId']

# Wait for query to complete
print("Waiting for query to complete...")
while True:
    query_results = logs.get_query_results(queryId=query_id)
    if query_results['status'] == 'Complete':
        break
    time.sleep(2)

# Step 2: Extract the average response time for this client
avg_response_time = None
for result in query_results['results']:
    for field in result:
        if field['field'] == 'avg_total_response_time':
            avg_response_time = float(field['value'])
            break

if avg_response_time is None:
    print(f"No response time data found for client '{CLIENT}'.")
    print("Query results:", query_results)
    exit(1)

print(f"Average Response Time for client '{CLIENT}' = {avg_response_time} ms")

# Step 3: Send the result to a custom CloudWatch metric (dimensioned by client)
print("Publishing custom metric to CloudWatch...")
cloudwatch.put_metric_data(
    Namespace=NAMESPACE,
    MetricData=[
        {
            'MetricName': METRIC_NAME,
            'Dimensions': [
                {
                    'Name': 'Client',
                    'Value': CLIENT,
                },
            ],
            'Value': avg_response_time,
            'Unit': 'Milliseconds',
        },
    ],
)

# Step 4: Create or update the alarm for this specific client
alarm_name = f"{ALARM_NAME_PREFIX}-{CLIENT}"
print(f"Creating/updating alarm '{alarm_name}' with SNS action to Dev Team topic...")

cloudwatch.put_metric_alarm(
    AlarmName=alarm_name,
    MetricName=METRIC_NAME,
    Namespace=NAMESPACE,
    Dimensions=[
        {
            'Name': 'Client',
            'Value': CLIENT,
        },
    ],
    Statistic='Average',
    Period=60,
    EvaluationPeriods=1,
    Threshold=THRESHOLD_MS,
    ComparisonOperator='GreaterThanThreshold',
    ActionsEnabled=True,
    AlarmActions=[SNS_TOPIC_ARN],
    AlarmDescription=(
        f"Triggers if average response time for client {CLIENT} exceeds {THRESHOLD_MS} ms"
    ),
    TreatMissingData='notBreaching',
)

print("Script completed: client-specific metric + alarm configured.")
