output "staging_bucket_name" {
  description = "Name of the migration staging S3 bucket."
  value       = aws_s3_bucket.staging.id
}

output "staging_bucket_arn" {
  description = "ARN of the migration staging S3 bucket."
  value       = aws_s3_bucket.staging.arn
}

output "migration_agent_role_arn" {
  description = "ARN of the IAM role assumed by migration agents."
  value       = aws_iam_role.migration_agent.arn
}
