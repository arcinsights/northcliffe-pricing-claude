output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP Region"
  value       = var.region
}

output "raw_data_bucket" {
  description = "Cloud Storage bucket for raw data"
  value       = google_storage_bucket.raw_data.name
}

output "bigquery_dataset" {
  description = "BigQuery dataset ID"
  value       = google_bigquery_dataset.pricing.dataset_id
}

output "functions_service_account" {
  description = "Service account email for Cloud Functions"
  value       = google_service_account.functions.email
}

output "scheduler_service_account" {
  description = "Service account email for Cloud Scheduler"
  value       = google_service_account.scheduler.email
}

output "dashboard_service_account" {
  description = "Service account email for Cloud Run dashboard"
  value       = google_service_account.dashboard.email
}

output "artifact_registry" {
  description = "Artifact Registry repository"
  value       = google_artifact_registry_repository.pricing.name
}

output "apify_secret_id" {
  description = "Secret Manager secret ID for Apify token"
  value       = google_secret_manager_secret.apify_token.secret_id
}
