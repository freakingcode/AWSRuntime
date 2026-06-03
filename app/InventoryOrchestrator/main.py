import json
import uuid
import boto3

from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model

app = BedrockAgentCoreApp()
log = app.logger

INVENTORY_RUNTIME_ARN = "arn:aws:bedrock-agentcore:eu-north-1:435627632308:runtime/InventoryManagementAI_InventoryAI-fQKKxSGtow"

PROCUREMENT_RUNTIME_ARN = "arn:aws:bedrock-agentcore:eu-north-1:435627632308:runtime/InventoryManagementAI_ProcurementAI-EI3zee9TUV"

runtime_client = boto3.client('bedrock-agentcore', region_name='eu-north-1')


DEFAULT_SYSTEM_PROMPT = """
You are an orchestration router.

Available tools:

1. invoke_inventory_agent(prompt: str)
   -get_product_stock
   - Record product sale
   - List all products

2. invoke_procurement_agent(prompt: str)
   - Get top selling products
   - Get low stock products
   - Get dead stock products
   - Generate restock recommendations based on current stock and sales data

   Call the appropriate tool based on the user's prompt. If the user's prompt is related to inventory management, call invoke_inventory_agent. If the user's prompt is related to procurement, call invoke_procurement_agent. And always show the tool response to the user without any modification.
"""


@tool
async def invoke_inventory_agent(prompt: str):

    response = runtime_client.invoke_agent_runtime(
        agentRuntimeArn=INVENTORY_RUNTIME_ARN,
        runtimeSessionId=str(uuid.uuid4()), # Must be 33+ char. Every new SessionId will create a new MicroVM
        payload=json.dumps({"prompt": prompt}),
        qualifier="DEFAULT" # This is Optional. When the field is not provided, Runtime will use DEFAULT endpoint
    )

    response_body = response['response'].read()
    print("Raw Response:", response_body)
    return response_body

@tool
async def invoke_procurement_agent(prompt: str):

    response = runtime_client.invoke_agent_runtime(
        agentRuntimeArn=PROCUREMENT_RUNTIME_ARN,
        runtimeSessionId=str(uuid.uuid4()), # Must be 33+ char. Every new SessionId will create a new MicroVM
        payload=json.dumps({"prompt": prompt}),
        qualifier="DEFAULT" # This is Optional. When the field is not provided, Runtime will use DEFAULT endpoint
    )

    response_body = response['response'].read()
    print("Raw Response:", response_body)
    return response_body

tools = []
tools.append(invoke_inventory_agent)
tools.append(invoke_procurement_agent)
_agent = None

def get_or_create_agent():
    global _agent
    if _agent is None:
        _agent = Agent(
            model=load_model(),
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            tools=tools
        )
    return _agent

@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking Agent.....")

    agent = get_or_create_agent()

    # Execute and format response
    stream = agent.stream_async(payload.get("prompt"))

    async for event in stream:
        # Handle Text parts of the response
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]

if __name__ == "__main__":
    app.run()