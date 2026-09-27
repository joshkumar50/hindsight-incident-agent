# ============================================================
# Terraform: Lambda function + API Gateway + SNS + EventBridge
# File: infrastructure/terraform/main.tf
# ============================================================

terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region"       { default = "us-east-1" }
variable "prometheus_url"   { default = "" }
variable "elasticsearch_url"{ default = "" }
variable "jaeger_url"       { default = "" }
variable "bedrock_model_id" { default = "anthropic.claude-3-5-sonnet-20241022-v2:0" }

# --- Lambda deployment package (zip of the backend/ directory) ---
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../../backend"
  output_path = "${path.root}/lambda_package.zip"
}

# --- Lambda Function ---
resource "aws_lambda_function" "rca_analyzer" {
  function_name = "ai-rca-analyzer"
  description   = "AI-powered Root Cause Analysis for EKS cluster"
  runtime       = "python3.12"
  handler       = "lambda_.lambda_handler.handler"   # file.function
  role          = aws_iam_role.rca_lambda_role.arn
  filename      = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  # Generous timeout: telemetry collection + LLM takes ~30-90s
  timeout     = 300   # 5 minutes max
  memory_size = 512   # MB

  environment {
    variables = {
      PROMETHEUS_URL      = var.prometheus_url
      ELASTICSEARCH_URL   = var.elasticsearch_url
      JAEGER_URL          = var.jaeger_url
      BEDROCK_MODEL_ID    = var.bedrock_model_id
      SNS_ALERT_TOPIC_ARN = aws_sns_topic.rca_alerts.arn
    }
  }

  tags = { Project = "AI-RCA", ManagedBy = "Terraform" }
}

# --- API Gateway (HTTP API v2) for REST access ---
resource "aws_apigatewayv2_api" "rca_api" {
  name          = "ai-rca-api"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
  }
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id             = aws_apigatewayv2_api.rca_api.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.rca_analyzer.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "analyze_route" {
  api_id    = aws_apigatewayv2_api.rca_api.id
  route_key = "POST /analyze"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_stage" "default_stage" {
  api_id      = aws_apigatewayv2_api.rca_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "api_gw_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.rca_analyzer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.rca_api.execution_arn}/*/*"
}

# --- SNS Topic for critical alert notifications ---
resource "aws_sns_topic" "rca_alerts" {
  name = "ai-rca-alerts"
  tags = { Project = "AI-RCA" }
}

# Optional: subscribe your email to the SNS topic
# resource "aws_sns_topic_subscription" "email_sub" {
#   topic_arn = aws_sns_topic.rca_alerts.arn
#   protocol  = "email"
#   endpoint  = "your-team@company.com"
# }

# --- EventBridge Rule: periodic health check every 30 minutes ---
resource "aws_cloudwatch_event_rule" "periodic_check" {
  name                = "ai-rca-periodic-check"
  description         = "Trigger RCA health check every 30 minutes"
  schedule_expression = "rate(30 minutes)"
  is_enabled          = true
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.periodic_check.name
  target_id = "RCALambdaTarget"
  arn       = aws_lambda_function.rca_analyzer.arn
  input     = jsonencode({
    source      = "eventbridge"
    detail-type = "ScheduledHealthCheck"
    detail      = {
      query            = "Perform a comprehensive EKS cluster health check."
      lookback_minutes = 30
    }
  })
}

resource "aws_lambda_permission" "eventbridge_permission" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.rca_analyzer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.periodic_check.arn
}

# --- Outputs ---
output "api_endpoint"    { value = aws_apigatewayv2_api.rca_api.api_endpoint }
output "lambda_arn"      { value = aws_lambda_function.rca_analyzer.arn }
output "sns_topic_arn"   { value = aws_sns_topic.rca_alerts.arn }
output "lambda_role_arn" { value = aws_iam_role.rca_lambda_role.arn }
