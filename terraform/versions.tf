terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.63"
    }
  }

  # Configure remote state per environment via `terraform init -backend-config`.
  # backend "s3" {
  #   bucket = "my-tf-state"
  #   key    = "vmware-migration-factory/terraform.tfstate"
  #   region = "us-east-1"
  # }
}
