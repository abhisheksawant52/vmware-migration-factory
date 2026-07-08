variable "name_prefix" {
  description = "Prefix applied to created resource names."
  type        = string
}

variable "environment" {
  description = "Deployment environment (e.g. dev, prod)."
  type        = string
}

variable "artifact_retention_days" {
  description = "Number of days before staged migration artifacts expire."
  type        = number
  default     = 30
}

variable "tags" {
  description = "Tags applied to all resources."
  type        = map(string)
  default     = {}
}
