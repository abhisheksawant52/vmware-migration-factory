provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "vmware-migration-factory"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
