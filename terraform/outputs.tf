output "staging_bucket_name" {
  description = "Name of the migration staging S3 bucket."
  value       = module.migration_staging.staging_bucket_name
}

output "staging_bucket_arn" {
  description = "ARN of the migration staging S3 bucket."
  value       = module.migration_staging.staging_bucket_arn
}

output "migration_agent_role_arn" {
  description = "ARN of the IAM role assumed by migration agents."
  value       = module.migration_staging.migration_agent_role_arn
}
