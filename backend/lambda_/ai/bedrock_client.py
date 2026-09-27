"""
=============================================================
lambda/ai/bedrock_client.py
=============================================================
Purpose: AWS Bedrock LLM client for direct model invocation.

AWS Bedrock provides managed access to foundation models like:
  - Anthropic Claude (claude-3-5-sonnet, claude-3-haiku)
  - Amazon Titan
  - Meta Llama 3
  - Mistral AI

This client uses the Bedrock Runtime API to invoke models
directly for root cause analysis generation.

Two approaches are supported:
  1. Direct model invocation (bedrock_client.py) - Fast, good for
     single-turn analysis with structured prompts
  2. Bedrock Agents (bedrock_agent.py) - Multi-turn, can call
     custom Action Groups (Lambda functions) to fetch more data

Bedrock uses different request/response formats per model family:
  - Anthropic: {"messages": [...], "max_tokens": N}
  - Amazon Titan: {"inputText": "...", "textGenerationConfig": {...}}
=============================================================
"""

import json
import logging
import time
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError, BotoCoreError

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.config import config

# ---- Logging Setup ----
logger = logging.getLogger(__name__)


class BedrockLLMClient:
    """
    Client for direct AWS Bedrock model invocation.
    
    This is the lower-level client that sends a prompt to a Bedrock
    foundation model and receives a text completion response.
    The higher-level RCA analysis logic is in rca_analyzer.py.
    """

    def __init__(self, region: Optional[str] = None, model_id: Optional[str] = None):
        """
        Initialize the Bedrock runtime client.
        
        Args:
            region: AWS region (defaults to config)
            model_id: Bedrock model ID (defaults to config)
        """
        self.region = region or config.aws.region
        self.model_id = model_id or config.aws.bedrock_model_id

        # boto3 Bedrock Runtime client
        # This handles signing, retries, and connection pooling automatically
        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=self.region,
        )
        logger.info(
            f"BedrockLLMClient initialized: region={self.region} "
            f"model={self.model_id}"
        )

    def _build_request_body(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> Dict[str, Any]:
        """
        Build the request body for the Bedrock InvokeModel API.
        
        Different model families have different request formats.
        We detect the model family from the model_id prefix.
        
        Args:
            prompt: The user's message/question
            system_prompt: System instructions for the model
            max_tokens: Maximum tokens in the response
            temperature: Sampling temperature (0=deterministic, 1=creative)
                         For RCA we use low temperature for factual responses
        
        Returns:
            Dict ready to be JSON-serialized as the request body
        """
        # ---- Anthropic Claude models ----
        # Uses the Messages API format
        if "anthropic" in self.model_id:
            messages = [{"role": "user", "content": prompt}]
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }
            # System prompt goes at top level for Claude
            if system_prompt:
                body["system"] = system_prompt
            return body

        # ---- Amazon Titan models ----
        elif "amazon.titan" in self.model_id:
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            return {
                "inputText": full_prompt,
                "textGenerationConfig": {
                    "maxTokenCount": max_tokens,
                    "temperature": temperature,
                    "stopSequences": [],
                },
            }

        # ---- Meta Llama 3 models ----
        elif "meta.llama" in self.model_id:
            full_prompt = (
                f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
                f"{system_prompt or ''}<|eot_id|>"
                f"<|start_header_id|>user<|end_header_id|>\n"
                f"{prompt}<|eot_id|>"
                f"<|start_header_id|>assistant<|end_header_id|>"
            )
            return {
                "prompt": full_prompt,
                "max_gen_len": max_tokens,
                "temperature": temperature,
            }

        # ---- Mistral models ----
        elif "mistral" in self.model_id:
            full_prompt = (
                f"<s>[INST] {system_prompt or ''}\n\n{prompt} [/INST]"
            )
            return {
                "prompt": full_prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

        # ---- Fallback: Generic text format ----
        else:
            logger.warning(
                f"Unknown model family for {self.model_id}, using generic format"
            )
            full_prompt = f"{system_prompt or ''}\n\n{prompt}" if system_prompt else prompt
            return {"inputText": full_prompt}

    def _parse_response(self, response_body: Dict[str, Any]) -> str:
        """
        Extract the generated text from the Bedrock response.
        
        Each model family returns text in a different field:
          - Claude: response_body["content"][0]["text"]
          - Titan: response_body["results"][0]["outputText"]
          - Llama3: response_body["generation"]
          - Mistral: response_body["outputs"][0]["text"]
        
        Returns:
            The generated text string
        """
        # ---- Anthropic Claude ----
        if "content" in response_body:
            content = response_body["content"]
            if content and isinstance(content, list):
                return content[0].get("text", "")

        # ---- Amazon Titan ----
        if "results" in response_body:
            results = response_body["results"]
            if results:
                return results[0].get("outputText", "")

        # ---- Meta Llama 3 ----
        if "generation" in response_body:
            return response_body["generation"]

        # ---- Mistral ----
        if "outputs" in response_body:
            outputs = response_body["outputs"]
            if outputs:
                return outputs[0].get("text", "")

        # ---- Fallback ----
        logger.warning(f"Unknown response format: {list(response_body.keys())}")
        return str(response_body)

    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.1,
        retry_on_throttle: bool = True,
    ) -> Optional[str]:
        """
        Invoke the Bedrock LLM with a prompt and return the generated text.
        
        Args:
            prompt: The user message / analysis request
            system_prompt: System instructions for the model role
            max_tokens: Max tokens in the response
            temperature: 0.0=deterministic (best for RCA), 1.0=creative
            retry_on_throttle: Automatically retry on ThrottlingException
        
        Returns:
            Generated text string, or None if the invocation failed
        """
        # Build model-specific request body
        request_body = self._build_request_body(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # Retry loop for throttling (Bedrock has per-account rate limits)
        max_retries = 3 if retry_on_throttle else 1
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Invoking Bedrock model {self.model_id} "
                    f"(attempt {attempt + 1}/{max_retries})"
                )

                # Call the Bedrock InvokeModel API
                response = self.client.invoke_model(
                    modelId=self.model_id,
                    # The request body must be JSON-encoded bytes
                    body=json.dumps(request_body),
                    contentType="application/json",
                    accept="application/json",
                )

                # Decode the response body (streaming bytes)
                response_body = json.loads(response["body"].read())

                # Extract the generated text
                generated_text = self._parse_response(response_body)
                logger.info(
                    f"Bedrock response received: {len(generated_text)} characters"
                )
                return generated_text

            except ClientError as e:
                error_code = e.response["Error"]["Code"]

                # Throttling: wait and retry with exponential backoff
                if error_code == "ThrottlingException" and attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 2  # 2s, 4s, 8s
                    logger.warning(
                        f"Bedrock throttled. Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    continue

                # Validation errors (bad prompt format, unsupported model, etc.)
                elif error_code == "ValidationException":
                    logger.error(f"Bedrock validation error: {e}")
                    return None

                # Access denied (IAM permissions issue)
                elif error_code == "AccessDeniedException":
                    logger.error(
                        f"Access denied to Bedrock model {self.model_id}. "
                        f"Check IAM permissions for bedrock:InvokeModel."
                    )
                    return None

                else:
                    logger.error(f"Bedrock ClientError [{error_code}]: {e}")
                    return None

            except BotoCoreError as e:
                logger.error(f"BotoCoreError invoking Bedrock: {e}")
                return None

        logger.error(f"All {max_retries} Bedrock invocation attempts failed")
        return None

    def invoke_streaming(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
    ):
        """
        Stream the Bedrock response token by token (generator).
        
        Useful for the Streamlit UI to show progressive output
        instead of waiting for the full response.
        
        Yields:
            str chunks of the generated text as they arrive
        """
        request_body = self._build_request_body(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=0.1,
        )

        try:
            # Use InvokeModelWithResponseStream for streaming
            response = self.client.invoke_model_with_response_stream(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json",
            )

            # Iterate over the streaming events
            stream = response.get("body")
            if not stream:
                return

            for event in stream:
                chunk = event.get("chunk")
                if chunk:
                    chunk_data = json.loads(chunk.get("bytes", b"{}"))
                    # Claude streaming format
                    if chunk_data.get("type") == "content_block_delta":
                        delta = chunk_data.get("delta", {})
                        text = delta.get("text", "")
                        if text:
                            yield text
                    # Generic completion chunk
                    elif "outputText" in chunk_data:
                        yield chunk_data["outputText"]

        except ClientError as e:
            logger.error(f"Streaming Bedrock invocation failed: {e}")
            yield f"\n[ERROR: Bedrock streaming failed: {e}]"
