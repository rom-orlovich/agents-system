# ============================================
# STEP FUNCTIONS
# ============================================

resource "aws_iam_role" "step_functions_role" {
  name = "${var.project_name}-step-functions-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "step_functions_policy" {
  name = "${var.project_name}-step-functions-policy"
  role = aws_iam_role.step_functions_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Resource = aws_dynamodb_table.tasks.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_sfn_state_machine" "agent_orchestrator" {
  name     = "${var.project_name}-orchestrator"
  role_arn = aws_iam_role.step_functions_role.arn
  
  definition = jsonencode({
    Comment = "Enterprise Agent System Orchestrator"
    StartAt = "DetermineWorkflowType"
    States = {
      DetermineWorkflowType = {
        Type = "Choice"
        Choices = [
          {
            Variable     = "$.source"
            StringEquals = "jira"
            Next         = "UpdateTaskStatus_Discovery"
          },
          {
            Variable     = "$.source"
            StringEquals = "sentry"
            Next         = "SentryErrorWorkflow"
          }
        ]
        Default = "UnknownSource"
      }
      
      UpdateTaskStatus_Discovery = {
        Type     = "Task"
        Resource = "arn:aws:states:::dynamodb:updateItem"
        Parameters = {
          TableName = aws_dynamodb_table.tasks.name
          Key = {
            pk = {"S.$" = "States.Format('TASK#{}', $.taskId)"}
            sk = {"S" = "METADATA"}
          }
          UpdateExpression = "SET #status = :status, current_agent = :agent"
          ExpressionAttributeNames = {
            "#status" = "status"
          }
          ExpressionAttributeValues = {
            ":status" = {"S" = "discovery"}
            ":agent"  = {"S" = "Discovery Agent"}
          }
        }
        ResultPath = null
        Next       = "RunDiscoveryAgent"
      }
      
      RunDiscoveryAgent = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = "${var.project_name}-discovery-agent"
          Payload = {
            "ticketId.$"    = "$.ticketId"
            "summary.$"     = "$.summary"
            "description.$" = "$.description"
            "labels.$"      = "$.labels"
            "priority.$"    = "$.priority"
          }
        }
        ResultPath     = "$.discoveryResult"
        ResultSelector = {
          "result.$" = "$.Payload"
        }
        TimeoutSeconds = 1800
        Next           = "UpdateTaskStatus_Planning"
      }
      
      UpdateTaskStatus_Planning = {
        Type     = "Task"
        Resource = "arn:aws:states:::dynamodb:updateItem"
        Parameters = {
          TableName = aws_dynamodb_table.tasks.name
          Key = {
            pk = {"S.$" = "States.Format('TASK#{}', $.taskId)"}
            sk = {"S" = "METADATA"}
          }
          UpdateExpression = "SET #status = :status, current_agent = :agent"
          ExpressionAttributeNames = {
            "#status" = "status"
          }
          ExpressionAttributeValues = {
            ":status" = {"S" = "planning"}
            ":agent"  = {"S" = "Planning Agent"}
          }
        }
        ResultPath = null
        Next       = "RunPlanningAgent"
      }
      
      RunPlanningAgent = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = "${var.project_name}-planning-agent"
          Payload = {
            "ticketId.$"        = "$.ticketId"
            "ticketDetails.$"   = "$.ticketDetails"
            "discoveryResults.$" = "$.discoveryResult.result"
          }
        }
        ResultPath     = "$.planResult"
        ResultSelector = {
          "result.$" = "$.Payload"
        }
        TimeoutSeconds = 3600
        Next           = "NotifyPlanReady"
      }
      
      NotifyPlanReady = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = "${var.project_name}-slack-mcp-adapter"
          Payload = {
            tool = "send_message"
            parameters = {
              channel = "#ai-agents"
              "text.$" = "States.Format('🤖 Plan ready for {} - awaiting approval', $.ticketId)"
            }
          }
        }
        ResultPath = null
        Next       = "WaitForApproval"
      }
      
      WaitForApproval = {
        Type           = "Wait"
        Seconds        = 60
        Next           = "CheckApprovalStatus"
      }
      
      CheckApprovalStatus = {
        Type     = "Task"
        Resource = "arn:aws:states:::dynamodb:getItem"
        Parameters = {
          TableName = aws_dynamodb_table.tasks.name
          Key = {
            pk = {"S.$" = "States.Format('TASK#{}', $.taskId)"}
            sk = {"S" = "METADATA"}
          }
        }
        ResultPath = "$.taskStatus"
        Next       = "EvaluateApproval"
      }
      
      EvaluateApproval = {
        Type = "Choice"
        Choices = [
          {
            Variable     = "$.taskStatus.Item.status.S"
            StringEquals = "approved"
            Next         = "ExecuteImplementation"
          },
          {
            Variable     = "$.taskStatus.Item.status.S"
            StringEquals = "rejected"
            Next         = "TaskRejected"
          }
        ]
        Default = "WaitForApproval"
      }
      
      ExecuteImplementation = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = "${var.project_name}-execution-agent"
          Payload = {
            "plan.$"   = "$.planResult.result.plan"
            "prInfo.$" = "$.planResult.result.prsCreated[0]"
          }
        }
        ResultPath     = "$.executionResult"
        TimeoutSeconds = 7200
        Next           = "TaskComplete"
      }
      
      TaskComplete = {
        Type = "Succeed"
      }
      
      TaskRejected = {
        Type = "Succeed"
      }
      
      SentryErrorWorkflow = {
        Type    = "Pass"
        Comment = "Handled by Sentry Agent EventBridge rule"
        End     = true
      }
      
      UnknownSource = {
        Type  = "Fail"
        Error = "UnknownSource"
        Cause = "Unknown webhook source"
      }
    }
  })
  
  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }
  
  tags = {
    Name = "${var.project_name}-orchestrator"
  }
}

resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/states/${var.project_name}-orchestrator"
  retention_in_days = 30
}
