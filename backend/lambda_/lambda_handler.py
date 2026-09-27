"""
=============================================================
lambda/lambda_handler.py - AWS Lambda Entry Point
=============================================================
Purpose: Main Lambda function handler that AWS invokes when
         a trigger fires (API Gateway, EventBridge, SNS, etc.)

AWS Lambda execution model:
  - Lambda receives an "event" dict from the trigger source
  - Lambda calls this handler function with (event, context)
  - The handler must return within the configured timeout
  - Response is returned to the caller or sent to the destination

Supported event sources:
  1. API Gateway / ALB: HTTP requests from the Streamlit UI
  2. EventBridge: Scheduled checks (e.g., every 5 minutes)
  3. SNS: CloudWatch Alarms forwarded via SNS
  4. Direct Invocation: boto3.client('lambda').invoke(...)
  5. Bedrock Agent Action Group: Tool calls from the AI agent

This Lambda function supports BOTH modes:
  Mode 1 - Analysis: User asks a question → RCA is performed
  Mode 2 - Action Group: Bedrock Agent calls a specific tool

The handler detects which mode based on the event structure.

IMPORTANT COMMENTS ABOUT EACH STEP:
  Every step in this file is commented to explain WHY it's needed,
  not just what it does, as requested.
=============================================================
"""

import json
import logging
import os
import sys
import time
import traceback
from typing import Any, Dict

# ============================================================
# Step 1: Configure logging BEFORE importing other modules
# ============================================================
# Lambda runs in a managed environment where print() works but
# structured logging via logging module is preferred because:
#   - CloudWatch Logs captures the entire log stream
#   - We can use log levels (DEBUG, INFO, ERROR) for filtering
#   - Structured JSON logging enables CloudWatch Insights queries
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# Step 2: Add parent directory to sys.path for module imports
# ============================================================
# Lambda packages everything in /var/task/ but our modules
# are in subdirectories. We add the project root to sys.path
# so "from shared.config import config" works correctly.
# This is equivalent to running the script from the project root.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# ============================================================
# Step 3: Import our project modules after path setup
# ============================================================
# These imports happen at module load time (Lambda cold start).
# Keep expensive imports here so they're cached across warm invocations.
try:
    from shared.models import AnalysisRequest, AnalysisResponse, AnalysisStatus
    from lambda_.ai.rca_analyzer import RCAAnalyzer
    from lambda_.ai.bedrock_agent import handle_action_group_request
    from agent.agent_workflow import AgentWorkflow

    # ============================================================
    # Step 4: Initialize the RCAAnalyzer and AgentWorkflow at module level (warm start optimization)
    # ============================================================
    # Lambda reuses the execution environment for warm starts.
    # By initializing the engines here (outside the handler),
    # subsequent invocations skip the initialization overhead.
    # This includes creating HTTP session pools, loading configs, etc.
    logger.info("Lambda cold start: Initializing RCAAnalyzer and AgentWorkflow...")
    _analyzer = RCAAnalyzer()
    _agent = AgentWorkflow()
    logger.info("RCAAnalyzer and AgentWorkflow ready. Lambda is warm.")

except Exception as e:
    # ============================================================
    # Step 5: Handle import/initialization failures gracefully
    # ============================================================
    # If initialization fails (e.g., missing AWS credentials),
    # we log the error but don't crash the module load.
    # This allows the handler to return a proper error response
    # instead of an unhandled exception.
    logger.critical(f"Failed to initialize RCAAnalyzer and AgentWorkflow: {e}")
    logger.critical(traceback.format_exc())
    _analyzer = None
    _agent = None


# ============================================================
# Step 6: Determine the trigger type from the event structure
# ============================================================

def _detect_event_type(event: Dict[str, Any]) -> str:
    """
    Detect the type of event that triggered this Lambda.
    
    Different AWS services structure events differently:
    - API Gateway: has "httpMethod", "path", "body" keys
    - EventBridge: has "source", "detail-type" keys
    - SNS: has "Records" with "EventSource": "aws:sns"
    - Direct invocation: has "query" key (our custom format)
    - Bedrock Agent: has "actionGroup", "function" keys
    
    Returns:
        String identifying the event source type
    """
    # ---- Bedrock Agent Action Group ----
    # Agent sends events with actionGroup and function fields
    if "actionGroup" in event and "function" in event:
        return "bedrock_agent"

    # ---- API Gateway or ALB ----
    # API Gateway wraps the request in httpMethod, path, body
    if "httpMethod" in event or "requestContext" in event:
        return "api_gateway"

    # ---- EventBridge / CloudWatch Events ----
    # Scheduled events for periodic health checks
    if "source" in event and "detail-type" in event:
        return "eventbridge"

    # ---- SNS (CloudWatch Alarm → SNS → Lambda) ----
    # SNS wraps the message in Records[].Sns.Message
    records = event.get("Records", [])
    if records and records[0].get("EventSource") == "aws:sns":
        return "sns"

    # ---- Direct invocation ----
    # Our Streamlit app and tests call Lambda directly with a "query" field
    if "query" in event:
        return "direct"

    # Unknown format - log for debugging
    logger.warning(f"Unknown event type. Event keys: {list(event.keys())}")
    return "unknown"


# ============================================================
# Step 7: Request parsing functions for each event type
# ============================================================

def _parse_api_gateway_event(event: Dict) -> AnalysisRequest:
    """
    Extract the analysis request from an API Gateway event.
    
    API Gateway sends the HTTP request body as a JSON string
    in event["body"]. We decode it and build an AnalysisRequest.
    """
    # The HTTP body is a JSON string that we need to parse
    body_str = event.get("body", "{}")
    try:
        body = json.loads(body_str) if isinstance(body_str, str) else body_str
    except json.JSONDecodeError:
        body = {}

    return AnalysisRequest(
        query=body.get("query", "What is the current cluster status?"),
        target_service=body.get("target_service"),
        target_namespace=body.get("target_namespace"),
        lookback_minutes=body.get("lookback_minutes"),
        trace_id=body.get("trace_id"),
        request_id=event.get("requestContext", {}).get("requestId", ""),
        source="api_gateway",
    )


def _parse_eventbridge_event(event: Dict) -> AnalysisRequest:
    """
    Extract analysis request from an EventBridge scheduled event.
    
    EventBridge is used for periodic cluster health checks.
    The event detail can optionally specify a focus area.
    """
    detail = event.get("detail", {})
    return AnalysisRequest(
        query=detail.get(
            "query",
            "Perform a comprehensive health check of the EKS cluster. "
            "Check for any errors, warnings, or performance issues."
        ),
        target_service=detail.get("service"),
        target_namespace=detail.get("namespace"),
        lookback_minutes=detail.get("lookback_minutes", 30),
        source="eventbridge",
    )


def _parse_sns_event(event: Dict) -> AnalysisRequest:
    """
    Extract analysis request from an SNS event (CloudWatch Alarm).
    
    When a CloudWatch Alarm fires (e.g., high CPU), it can trigger
    SNS which forwards to this Lambda. The alarm message becomes
    the analysis query so the LLM knows what alert was triggered.
    """
    # SNS wraps the message in Records[0].Sns.Message
    record = event.get("Records", [{}])[0]
    sns_data = record.get("Sns", {})
    message_str = sns_data.get("Message", "{}")

    try:
        # CloudWatch Alarm messages are JSON strings
        alarm_data = json.loads(message_str)
        alarm_name = alarm_data.get("AlarmName", "Unknown Alarm")
        alarm_desc = alarm_data.get("AlarmDescription", "")
        reason = alarm_data.get("NewStateReason", "")

        query = (
            f"CloudWatch Alarm '{alarm_name}' triggered. "
            f"Description: {alarm_desc}. "
            f"Reason: {reason}. "
            f"Please analyze the root cause of this alert."
        )
    except json.JSONDecodeError:
        # If the SNS message is not JSON, use it as-is
        query = f"Alert triggered: {message_str[:500]}"

    return AnalysisRequest(
        query=query,
        source="sns",
    )


def _parse_direct_event(event: Dict) -> AnalysisRequest:
    """
    Extract analysis request from a direct Lambda invocation.
    
    This is used by:
      - Our Streamlit UI (via boto3 Lambda.invoke)
      - Integration tests
      - CLI debugging
    
    The event is the raw AnalysisRequest JSON.
    """
    return AnalysisRequest(
        query=event.get("query", "What is wrong with the cluster?"),
        target_service=event.get("target_service"),
        target_namespace=event.get("target_namespace"),
        lookback_minutes=event.get("lookback_minutes"),
        trace_id=event.get("trace_id"),
        request_id=event.get("request_id", ""),
        source=event.get("source", "direct"),
    )


# ============================================================
# Step 8: Response formatting for API Gateway
# ============================================================

def _format_api_response(response: AnalysisResponse, status_code: int = 200) -> Dict:
    """
    Format the analysis response for API Gateway.
    
    API Gateway requires responses in a specific structure:
    {
      "statusCode": 200,
      "headers": {...},
      "body": "JSON string"  ← Note: must be a STRING, not a dict
    }
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",  # CORS for browser access
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
        },
        "body": response.model_dump_json(),
    }


def _format_error_response(error_msg: str, status_code: int = 500) -> Dict:
    """Format an error response for API Gateway."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": error_msg}),
    }


# ============================================================
# Step 9: SNS notification for critical findings
# ============================================================

def _notify_via_sns(response: AnalysisResponse) -> None:
    """
    Send a notification via SNS if the RCA finds a critical issue.
    
    This allows teams to receive alerts via email, SMS, or Slack
    (through SNS → Chatbot integration) when the AI detects
    critical problems.
    
    Only fires for CRITICAL or HIGH severity findings.
    """
    import boto3
    from botocore.exceptions import ClientError

    sns_topic = os.environ.get("SNS_ALERT_TOPIC_ARN", "")
    if not sns_topic:
        # SNS notifications are optional - skip if not configured
        return

    rca = response.rca
    # Only notify for critical/high severity issues
    from shared.models import Severity
    if rca.severity not in [Severity.CRITICAL, Severity.HIGH]:
        return

    try:
        sns_client = boto3.client("sns", region_name=config.aws.region)

        # Format the notification message
        message = (
            f"🚨 AI-RCA Alert: {rca.severity.upper()} severity issue detected\n\n"
            f"Summary: {rca.root_cause_summary}\n\n"
            f"Affected Components: {', '.join(rca.affected_components)}\n\n"
            f"Confidence: {rca.confidence_score * 100:.0f}%\n\n"
            f"Immediate Actions:\n"
            + "\n".join(f"  - {a}" for a in rca.recommended_actions[:3])
            + f"\n\nAnalysis ID: {rca.analysis_id}"
        )

        sns_client.publish(
            TopicArn=sns_topic,
            Subject=f"AI-RCA: {rca.severity.upper()} - {rca.root_cause_summary[:100]}",
            Message=message,
        )
        logger.info(f"SNS notification sent for {rca.severity} severity issue")

    except ClientError as e:
        # Don't fail the Lambda if SNS notification fails
        logger.warning(f"Failed to send SNS notification: {e}")


# ============================================================
# Step 10: Main Lambda Handler Function
# ============================================================

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler - entry point for all invocations.
    
    AWS invokes this function with:
      event: The trigger payload (varies by source)
      context: Lambda runtime metadata (function name, timeout remaining, etc.)
    
    This handler:
      1. Detects the trigger type
      2. Routes to Bedrock Agent action handler OR RCA analyzer
      3. Returns the appropriate response format
    
    Args:
        event: Dict containing the trigger payload
        context: LambdaContext object with runtime metadata
    
    Returns:
        Dict response (format depends on trigger type)
    """
    # ============================================================
    # Step 10a: Log the invocation for observability
    # ============================================================
    # We log the function name and remaining time so we can detect
    # if we're getting close to the Lambda timeout (important for
    # the CloudWatch Logs / RCA feedback loop!)
    remaining_ms = getattr(context, 'get_remaining_time_in_millis', lambda: 0)()
    logger.info(
        f"Lambda invoked. "
        f"Function: {getattr(context, 'function_name', 'unknown')} | "
        f"Request ID: {getattr(context, 'aws_request_id', 'unknown')} | "
        f"Remaining time: {remaining_ms}ms"
    )

    # ============================================================
    # Step 10b: Check if the analyzer/agent initialized successfully
    # ============================================================
    if _agent is None and _analyzer is None:
        logger.error("Both AgentWorkflow and RCAAnalyzer are not initialized. Check startup logs.")
        error_body = {
            "error": "Internal initialization failure",
            "message": "The RCA analyzer and agent workflow failed to initialize. Check CloudWatch Logs.",
        }
        return {
            "statusCode": 500,
            "body": json.dumps(error_body),
        }

    # ============================================================
    # Step 10c: Detect event type and route accordingly
    # ============================================================
    event_type = _detect_event_type(event)
    logger.info(f"Event type detected: {event_type}")

    # ============================================================
    # Step 10d: Bedrock Agent Action Group mode
    # ============================================================
    # When the Bedrock Agent calls one of our tools, it invokes
    # this same Lambda but with a different event structure.
    # We detect this and route to the action group handler instead.
    if event_type == "bedrock_agent":
        logger.info("Routing to Bedrock Agent Action Group handler")
        try:
            result = handle_action_group_request(event)
            logger.info(f"Action Group response ready for: {event.get('function')}")
            return result
        except Exception as e:
            logger.error(f"Action Group handler failed: {e}")
            return {
                "actionGroup": event.get("actionGroup", ""),
                "function": event.get("function", ""),
                "functionResponse": {
                    "responseBody": {
                        "TEXT": {
                            "body": json.dumps({"error": str(e)})
                        }
                    }
                },
            }

    # ============================================================
    # Step 10e: Parse the analysis request based on event type
    # ============================================================
    try:
        if event_type == "api_gateway":
            # HTTP request from API Gateway (Streamlit UI via REST)
            request = _parse_api_gateway_event(event)
        elif event_type == "eventbridge":
            # Scheduled health check from EventBridge
            request = _parse_eventbridge_event(event)
        elif event_type == "sns":
            # CloudWatch Alarm forwarded via SNS
            request = _parse_sns_event(event)
        else:
            # Direct invocation (Streamlit UI via boto3, tests, CLI)
            request = _parse_direct_event(event)

        logger.info(
            f"Analysis request parsed: query='{request.query[:100]}' "
            f"service={request.target_service} ns={request.target_namespace}"
        )

    except Exception as e:
        # ============================================================
        # Step 10f: Handle request parsing failures
        # ============================================================
        # If we can't parse the request, return an error immediately
        # without attempting expensive telemetry collection
        logger.error(f"Failed to parse event: {e}")
        error_response = _format_error_response(f"Invalid request format: {str(e)}", 400)
        return error_response

    # ============================================================
    # Step 10g: Perform the Root Cause Analysis
    # ============================================================
    # This is the main work: collect telemetry + invoke the SRE agent workflow
    analysis_start = time.time()

    try:
        logger.info(f"Starting RCA analysis for request: {request.request_id}")

        # Call the new ReAct agent workflow, or fallback to the direct analyzer
        if _agent:
            logger.info("Executing troubleshooting using the custom ReAct Agent Workflow...")
            response = _agent.run(request)
        else:
            logger.info("AgentWorkflow not available. Falling back to direct RCAAnalyzer...")
            response = _analyzer.analyze(request)

        analysis_duration = time.time() - analysis_start
        logger.info(
            f"RCA completed in {analysis_duration:.1f}s. "
            f"Severity: {response.rca.severity}. "
            f"Summary: {response.rca.root_cause_summary[:100]}"
        )

    except Exception as e:
        # ============================================================
        # Step 10h: Handle analysis failures gracefully
        # ============================================================
        # If analysis fails, log the full traceback but return a
        # structured error response to the caller (not an exception)
        logger.error(f"RCA analysis failed: {e}")
        logger.error(traceback.format_exc())

        error_response = _format_error_response(
            f"Analysis failed: {str(e)}", 500
        )
        return error_response if event_type == "api_gateway" else {"error": str(e)}

    # ============================================================
    # Step 10i: Optionally send critical findings via SNS
    # ============================================================
    # For EventBridge scheduled checks and SNS alarm triggers,
    # automatically notify the team if critical issues are found
    if event_type in ["eventbridge", "sns"]:
        _notify_via_sns(response)

    # ============================================================
    # Step 10j: Format and return the response
    # ============================================================
    if event_type == "api_gateway":
        # API Gateway needs the specific HTTP response format
        return _format_api_response(response)
    else:
        # For direct invocations, return the response as a dict
        # boto3 Lambda.invoke() will serialize this automatically
        return response.model_dump()


# ============================================================
# Step 11: Local testing entry point
# ============================================================
# Running this file directly allows testing without deploying to AWS.
# Set environment variables (or use .env file) before running.
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test the Lambda handler locally")
    parser.add_argument("--query", default="Why is the cluster unhealthy?")
    parser.add_argument("--service", default=None)
    parser.add_argument("--namespace", default=None)
    parser.add_argument("--lookback", type=int, default=30)
    args = parser.parse_args()

    # Simulate the Lambda event payload
    test_event = {
        "query": args.query,
        "target_service": args.service,
        "target_namespace": args.namespace,
        "lookback_minutes": args.lookback,
        "source": "local_test",
    }

    # Simulate the Lambda context object
    class MockContext:
        function_name = "ai-rca-local-test"
        aws_request_id = "local-test-001"
        def get_remaining_time_in_millis(self):
            return 300000  # 5 minutes

    print(f"\nTesting Lambda handler with query: {args.query}")
    result = handler(test_event, MockContext())

    print("\n========== LAMBDA RESPONSE ==========")
    if isinstance(result, dict) and "rca" in result:
        rca = result["rca"]
        print(f"Severity: {rca.get('severity')}")
        print(f"Summary: {rca.get('root_cause_summary')}")
        print(f"\nDetailed Analysis:\n{rca.get('detailed_analysis', '')[:1000]}")
        print(f"\nRecommended Actions:")
        for action in rca.get("recommended_actions", []):
            print(f"  {action}")
    else:
        print(json.dumps(result, indent=2, default=str))
