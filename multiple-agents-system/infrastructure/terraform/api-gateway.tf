# ============================================
# API GATEWAY
# ============================================

resource "aws_apigatewayv2_api" "webhook_api" {
  name          = "${var.project_name}-webhook-api"
  protocol_type = "HTTP"
  
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST", "GET", "OPTIONS"]
    allow_headers = ["*"]
    max_age       = 300
  }
  
  tags = {
    Name = "${var.project_name}-webhook-api"
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.webhook_api.id
  name        = "$default"
  auto_deploy = true
  
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
      integrationError = "$context.integrationErrorMessage"
    })
  }
  
  default_route_settings {
    throttling_burst_limit = 200
    throttling_rate_limit  = 100
  }
}

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${var.project_name}-webhook-api"
  retention_in_days = 30
}

# Routes
resource "aws_apigatewayv2_integration" "webhook_router" {
  api_id                 = aws_apigatewayv2_api.webhook_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.webhook_router.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "jira_webhook" {
  api_id    = aws_apigatewayv2_api.webhook_api.id
  route_key = "POST /webhooks/jira"
  target    = "integrations/${aws_apigatewayv2_integration.webhook_router.id}"
}

resource "aws_apigatewayv2_route" "github_webhook" {
  api_id    = aws_apigatewayv2_api.webhook_api.id
  route_key = "POST /webhooks/github"
  target    = "integrations/${aws_apigatewayv2_integration.webhook_router.id}"
}

resource "aws_apigatewayv2_route" "sentry_webhook" {
  api_id    = aws_apigatewayv2_api.webhook_api.id
  route_key = "POST /webhooks/sentry"
  target    = "integrations/${aws_apigatewayv2_integration.webhook_router.id}"
}
