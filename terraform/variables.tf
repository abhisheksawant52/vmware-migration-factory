variable "aws_region" {
  description = "AWS region for the migration landing zone."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (e.g. dev, prod)."
  type        = string
}

variable "name_prefix" {
  description = "Prefix applied to created resource names."
  type        = string
  default     = "vmf"
}

variable "artifact_retention_days" {
  description = "Number of days before staged migration artifacts expire."
  type        = number
  default     = 30
}

variable "tags" {
  description = "Additional tags applied to all resources."
  type        = map(string)
  default     = {}
}
