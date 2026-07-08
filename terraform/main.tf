module "migration_staging" {
  source = "./modules/migration_staging"

  name_prefix             = var.name_prefix
  environment             = var.environment
  artifact_retention_days = var.artifact_retention_days
  tags                    = var.tags
}
