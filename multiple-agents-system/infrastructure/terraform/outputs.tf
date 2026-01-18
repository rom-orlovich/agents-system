# ============================================
# TERRAFORM OUTPUTS
# ============================================

output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = aws_apigatewayv2_api.webhook_api.api_endpoint
}

output "tasks_table_name" {
  description = "DynamoDB tasks table name"
  value       = aws_dynamodb_table.tasks.name
}

output "error_tracking_table_name" {
  description = "DynamoDB error tracking table name"
  value       = aws_dynamodb_table.error_tracking.name
}

output "webhook_router_function_name" {
  description = "Webhook router Lambda function name"
  value       = aws_lambda_function.webhook_router.function_name
}

output "state_machine_arn" {
  description = "Step Functions state machine ARN"
  value       = aws_sfn_state_machine.agent_orchestrator.arn
}
