import boto3
import json

client = boto3.client('bedrock-agentcore', region_name='eu-north-1')
payload = json.dumps({"prompt": "List all products."})

response = client.invoke_agent_runtime(
    agentRuntimeArn='arn:aws:bedrock-agentcore:eu-north-1:435627632308:runtime/InventoryManagementAI_InventoryAI-fQKKxSGtow',
    runtimeSessionId='550e8400-e29b-41d4-a716-446655440001', # Must be 33+ char. Every new SessionId will create a new MicroVM
    payload=payload,
    qualifier="DEFAULT" # This is Optional. When the field is not provided, Runtime will use DEFAULT endpoint
)
response_body = response['response'].read()
print("Raw Response:", response_body)
# response_data = json.loads(response_body)
# print("Agent Response:", response_data)