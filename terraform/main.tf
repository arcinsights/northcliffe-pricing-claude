terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "REPLACE_WITH_YOUR_PROJECT_ID-terraform-state"
    prefix = "pricing/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "cloudfunctions.googleapis.com",
    "cloudscheduler.googleapis.com",
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "bigquery.googleapis.com",
    "storage.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "eventarc.googleapis.com",
  ])

  service            = each.value
  disable_on_destroy = false
}

# Cloud Storage bucket for raw scraping data
resource "google_storage_bucket" "raw_data" {
  name          = "${var.project_id}-pricing-raw-data"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 90 # Delete raw data after 90 days
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.required_apis]
}

# BigQuery dataset
resource "google_bigquery_dataset" "pricing" {
  dataset_id  = "pricing"
  description = "Smart pricing data warehouse"
  location    = var.region

  # Delete dataset if destroyed
  delete_contents_on_destroy = false

  depends_on = [google_project_service.required_apis]
}

# BigQuery tables
resource "google_bigquery_table" "competitor_listings" {
  dataset_id          = google_bigquery_dataset.pricing.dataset_id
  table_id            = "competitor_listings"
  deletion_protection = false

  schema = jsonencode([
    {
      name = "listing_id"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "source"
      type = "STRING"
      mode = "REQUIRED"
      description = "airbnb or booking"
    },
    {
      name = "name"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "url"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "property_type"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "room_type"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "bedrooms"
      type = "INTEGER"
      mode = "NULLABLE"
    },
    {
      name = "bathrooms"
      type = "FLOAT"
      mode = "NULLABLE"
    },
    {
      name = "max_guests"
      type = "INTEGER"
      mode = "NULLABLE"
    },
    {
      name = "latitude"
      type = "FLOAT"
      mode = "NULLABLE"
    },
    {
      name = "longitude"
      type = "FLOAT"
      mode = "NULLABLE"
    },
    {
      name = "rating"
      type = "FLOAT"
      mode = "NULLABLE"
    },
    {
      name = "review_count"
      type = "INTEGER"
      mode = "NULLABLE"
    },
    {
      name = "amenities"
      type = "STRING"
      mode = "REPEATED"
    },
    {
      name = "host_is_superhost"
      type = "BOOLEAN"
      mode = "NULLABLE"
    },
    {
      name = "instant_bookable"
      type = "BOOLEAN"
      mode = "NULLABLE"
    },
    {
      name = "first_seen_date"
      type = "DATE"
      mode = "REQUIRED"
    },
    {
      name = "last_seen_date"
      type = "DATE"
      mode = "REQUIRED"
    },
    {
      name = "is_active"
      type = "BOOLEAN"
      mode = "REQUIRED"
    }
  ])
}

resource "google_bigquery_table" "daily_prices" {
  dataset_id          = google_bigquery_dataset.pricing.dataset_id
  table_id            = "daily_prices"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "scrape_date"
  }

  clustering = ["listing_id", "check_in_date"]

  schema = jsonencode([
    {
      name = "scrape_date"
      type = "DATE"
      mode = "REQUIRED"
    },
    {
      name = "listing_id"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "check_in_date"
      type = "DATE"
      mode = "REQUIRED"
    },
    {
      name = "price_per_night"
      type = "FLOAT"
      mode = "NULLABLE"
    },
    {
      name = "cleaning_fee"
      type = "FLOAT"
      mode = "NULLABLE"
    },
    {
      name = "service_fee"
      type = "FLOAT"
      mode = "NULLABLE"
    },
    {
      name = "total_price"
      type = "FLOAT"
      mode = "NULLABLE"
    },
    {
      name = "nights"
      type = "INTEGER"
      mode = "NULLABLE"
    },
    {
      name = "is_available"
      type = "BOOLEAN"
      mode = "REQUIRED"
    },
    {
      name = "min_nights"
      type = "INTEGER"
      mode = "NULLABLE"
    },
    {
      name = "currency"
      type = "STRING"
      mode = "NULLABLE"
    }
  ])
}

resource "google_bigquery_table" "events" {
  dataset_id          = google_bigquery_dataset.pricing.dataset_id
  table_id            = "events"
  deletion_protection = false

  schema = jsonencode([
    {
      name = "event_date"
      type = "DATE"
      mode = "REQUIRED"
    },
    {
      name = "event_name"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "event_type"
      type = "STRING"
      mode = "REQUIRED"
      description = "concert, sports, conference, holiday, etc"
    },
    {
      name = "expected_impact"
      type = "STRING"
      mode = "REQUIRED"
      description = "low, medium, high"
    },
    {
      name = "source"
      type = "STRING"
      mode = "NULLABLE"
    }
  ])
}

resource "google_bigquery_table" "price_recommendations" {
  dataset_id          = google_bigquery_dataset.pricing.dataset_id
  table_id            = "price_recommendations"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "recommendation_date"
  }

  schema = jsonencode([
    {
      name = "recommendation_date"
      type = "DATE"
      mode = "REQUIRED"
    },
    {
      name = "target_date"
      type = "DATE"
      mode = "REQUIRED"
    },
    {
      name = "recommended_price"
      type = "FLOAT"
      mode = "REQUIRED"
    },
    {
      name = "min_price"
      type = "FLOAT"
      mode = "REQUIRED"
    },
    {
      name = "max_price"
      type = "FLOAT"
      mode = "REQUIRED"
    },
    {
      name = "comp_set_median"
      type = "FLOAT"
      mode = "NULLABLE"
    },
    {
      name = "comp_set_min"
      type = "FLOAT"
      mode = "NULLABLE"
    },
    {
      name = "comp_set_max"
      type = "FLOAT"
      mode = "NULLABLE"
    },
    {
      name = "comp_set_count"
      type = "INTEGER"
      mode = "NULLABLE"
    },
    {
      name = "factors"
      type = "JSON"
      mode = "NULLABLE"
      description = "Pricing factors applied as JSON"
    },
    {
      name = "confidence"
      type = "STRING"
      mode = "REQUIRED"
    }
  ])
}

# Service account for Cloud Functions
resource "google_service_account" "functions" {
  account_id   = "pricing-functions"
  display_name = "Pricing Functions Service Account"
  description  = "Used by Cloud Functions for scraping and analysis"
}

# Grant BigQuery permissions to functions SA
resource "google_bigquery_dataset_iam_member" "functions_bq" {
  dataset_id = google_bigquery_dataset.pricing.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.functions.email}"
}

resource "google_project_iam_member" "functions_bq_job" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.functions.email}"
}

# Grant Storage permissions
resource "google_storage_bucket_iam_member" "functions_storage" {
  bucket = google_storage_bucket.raw_data.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.functions.email}"
}

# Secret Manager for Apify token
resource "google_secret_manager_secret" "apify_token" {
  secret_id = "apify-api-token"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "apify_token" {
  count = var.apify_api_token != "" ? 1 : 0

  secret      = google_secret_manager_secret.apify_token.id
  secret_data = var.apify_api_token
}

resource "google_secret_manager_secret_iam_member" "functions_secret" {
  secret_id = google_secret_manager_secret.apify_token.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.functions.email}"
}

# Artifact Registry for Docker images
resource "google_artifact_registry_repository" "pricing" {
  location      = var.region
  repository_id = "pricing"
  description   = "Pricing dashboard container images"
  format        = "DOCKER"

  depends_on = [google_project_service.required_apis]
}

# Service account for Cloud Scheduler
resource "google_service_account" "scheduler" {
  account_id   = "pricing-scheduler"
  display_name = "Pricing Scheduler Service Account"
}

# Allow scheduler to invoke functions
resource "google_project_iam_member" "scheduler_invoker" {
  project = var.project_id
  role    = "roles/cloudfunctions.invoker"
  member  = "serviceAccount:${google_service_account.scheduler.email}"
}

# Service account for Cloud Run dashboard
resource "google_service_account" "dashboard" {
  account_id   = "pricing-dashboard"
  display_name = "Pricing Dashboard Service Account"
}

# Grant dashboard read-only BigQuery access
resource "google_bigquery_dataset_iam_member" "dashboard_bq" {
  dataset_id = google_bigquery_dataset.pricing.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.dashboard.email}"
}

resource "google_project_iam_member" "dashboard_bq_job" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.dashboard.email}"
}

# Cloud Scheduler job (will be created but needs function URL)
# This is managed in scheduler.tf after functions are deployed
