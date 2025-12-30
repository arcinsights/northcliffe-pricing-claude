# Import existing resources that were created manually

import {
  to = google_service_account.functions
  id = "projects/northcliffe-claude/serviceAccounts/pricing-functions@northcliffe-claude.iam.gserviceaccount.com"
}

import {
  to = google_service_account.scheduler
  id = "projects/northcliffe-claude/serviceAccounts/pricing-scheduler@northcliffe-claude.iam.gserviceaccount.com"
}

import {
  to = google_service_account.dashboard
  id = "projects/northcliffe-claude/serviceAccounts/pricing-dashboard@northcliffe-claude.iam.gserviceaccount.com"
}

import {
  to = google_artifact_registry_repository.pricing
  id = "projects/northcliffe-claude/locations/us-east1/repositories/pricing"
}
