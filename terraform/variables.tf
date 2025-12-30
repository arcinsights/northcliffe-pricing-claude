variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-east1"
}

variable "environment" {
  description = "Environment (dev/prod)"
  type        = string
  default     = "prod"
}

variable "apify_api_token" {
  description = "Apify API token (stored in Secret Manager)"
  type        = string
  sensitive   = true
  default     = ""
}
