# ============================================
# LAMBDA FUNCTIONS
# ============================================

# IAM Role for Lambda Functions
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.project_name}-lambda-policy"
  role = aws_iam_role.lambda_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.tasks.arn,
          "${aws_dynamodb_table.tasks.arn}/index/*",
          aws_dynamodb_table.error_tracking.arn,
          aws_dynamodb_table.sessions.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution"
        ]
        Resource = aws_sfn_state_machine.agent_orchestrator.arn
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/*"
      }
    ]
  })
}

# Webhook Router Lambda
resource "aws_lambda_function" "webhook_router" {
  function_name = "${var.project_name}-webhook-router"
  role          = aws_iam_role.lambda_role.arn
  handler       = "handler.handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 256
  
  filename         = data.archive_file.webhook_router.output_path
  source_code_hash = data.archive_file.webhook_router.output_base64sha256
  
  environment {
    variables = {
      TASKS_TABLE        = aws_dynamodb_table.tasks.name
      STATE_MACHINE_ARN  = aws_sfn_state_machine.agent_orchestrator.arn
      JIRA_AI_LABEL      = "AI"
      ENVIRONMENT        = var.environment
    }
  }
  
  tags = {
    Name = "${var.project_name}-webhook-router"
  }
}

data "archive_file" "webhook_router" {
  type        = "zip"
  source_dir  = "${path.module}/../../lambda/webhook-router"
  output_path = "${path.module}/../../.build/webhook-router.zip"
}

# Slack MCP Adapter Lambda
resource "aws_lambda_function" "slack_mcp_adapter" {
  function_name = "${var.project_name}-slack-mcp-adapter"
  role          = aws_iam_role.lambda_role.arn
  handler       = "handler.handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 256
  
  filename         = data.archive_file.slack_mcp_adapter.output_path
  source_code_hash = data.archive_file.slack_mcp_adapter.output_base64sha256
  
  environment {
    variables = {
      SLACK_BOT_TOKEN = "placeholder"
      ENVIRONMENT     = var.environment
    }
  }
  
  tags = {
    Name = "${var.project_name}-slack-mcp-adapter"
  }
}

data "archive_file" "slack_mcp_adapter" {
  type        = "zip"
  source_dir  = "${path.module}/../../lambda/slack-mcp-adapter"
  output_path = "${path.module}/../../.build/slack-mcp-adapter.zip"
}

# Lambda permissions for API Gateway
resource "aws_lambda_permission" "webhook_router_api_gateway" {
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.webhook_router.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.webhook_api.execution_arn}/*/*"
}
