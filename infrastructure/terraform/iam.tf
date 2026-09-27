# ============================================================
# Terraform: IAM Role for the Lambda function
# File: infrastructure/terraform/iam.tf
# ============================================================
# This role is assumed by the Lambda function.
# It grants the minimum permissions needed to:
#   - Write logs to CloudWatch
#   - Invoke Bedrock models
#   - Publish to SNS
# ============================================================

# --- Trust policy: allow Lambda service to assume this role ---
data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "rca_lambda_role" {
  name               = "ai-rca-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = { Project = "AI-RCA" }
}

# --- CloudWatch Logs: Lambda must write its own execution logs ---
resource "aws_iam_role_policy_attachment" "lambda_basic_exec" {
  role       = aws_iam_role.rca_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# --- Bedrock: invoke foundation models and agents ---
data "aws_iam_policy_document" "bedrock_access" {
  statement {
    sid     = "InvokeBedrockModels"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
    ]
    resources = ["arn:aws:bedrock:*::foundation-model/*"]
  }

  statement {
    sid     = "InvokeBedrockAgent"
    actions = [
      "bedrock:InvokeAgent",
    ]
    resources = ["arn:aws:bedrock:*:*:agent-alias/*/*"]
  }
}

resource "aws_iam_policy" "bedrock_policy" {
  name   = "ai-rca-bedrock-policy"
  policy = data.aws_iam_policy_document.bedrock_access.json
}

resource "aws_iam_role_policy_attachment" "bedrock_attach" {
  role       = aws_iam_role.rca_lambda_role.name
  policy_arn = aws_iam_policy.bedrock_policy.arn
}

# --- SNS: publish alert notifications ---
data "aws_iam_policy_document" "sns_publish" {
  statement {
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.rca_alerts.arn]
  }
}

resource "aws_iam_policy" "sns_policy" {
  name   = "ai-rca-sns-policy"
  policy = data.aws_iam_policy_document.sns_publish.json
}

resource "aws_iam_role_policy_attachment" "sns_attach" {
  role       = aws_iam_role.rca_lambda_role.name
  policy_arn = aws_iam_policy.sns_policy.arn
}
