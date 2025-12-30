#!/bin/bash

# Smart Pricing - GCP Setup Script
# This script sets up the initial GCP infrastructure and GitHub integration

set -e

echo "🚀 Smart Pricing - GCP Setup"
echo "============================"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get project ID
read -p "Enter your GCP Project ID: " PROJECT_ID
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Project ID cannot be empty"
    exit 1
fi

# Set project
echo "📍 Setting GCP project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo ""
echo "🔌 Enabling required APIs (this may take a few minutes)..."
gcloud services enable \
    cloudfunctions.googleapis.com \
    cloudscheduler.googleapis.com \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    bigquery.googleapis.com \
    storage.googleapis.com \
    secretmanager.googleapis.com \
    artifactregistry.googleapis.com \
    eventarc.googleapis.com \
    iam.googleapis.com \
    iamcredentials.googleapis.com

echo "✅ APIs enabled successfully"

# Create Terraform state bucket
echo ""
echo "📦 Creating Terraform state bucket..."
STATE_BUCKET="${PROJECT_ID}-terraform-state"
gsutil mb -p $PROJECT_ID -l europe-west2 gs://$STATE_BUCKET/ || echo "Bucket already exists"
gsutil versioning set on gs://$STATE_BUCKET/
echo "✅ State bucket created: gs://$STATE_BUCKET"

# Create service accounts
echo ""
echo "👤 Creating service accounts..."

# Terraform SA
gcloud iam service-accounts create terraform \
    --display-name="Terraform Service Account" \
    --description="Used by GitHub Actions to manage infrastructure" \
    2>/dev/null || echo "  terraform SA already exists"

# Functions SA
gcloud iam service-accounts create pricing-functions \
    --display-name="Pricing Functions Service Account" \
    2>/dev/null || echo "  pricing-functions SA already exists"

# Scheduler SA
gcloud iam service-accounts create pricing-scheduler \
    --display-name="Pricing Scheduler Service Account" \
    2>/dev/null || echo "  pricing-scheduler SA already exists"

# Dashboard SA
gcloud iam service-accounts create pricing-dashboard \
    --display-name="Pricing Dashboard Service Account" \
    2>/dev/null || echo "  pricing-dashboard SA already exists"

echo "✅ Service accounts created"

# Grant IAM roles
echo ""
echo "🔐 Granting IAM permissions..."

# Terraform SA needs to manage everything
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:terraform@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/editor" \
    --condition=None

# Scheduler SA needs to invoke functions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:pricing-scheduler@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/cloudfunctions.invoker" \
    --condition=None

echo "✅ IAM permissions granted"

# Set up Workload Identity Federation for GitHub Actions
echo ""
echo "🔗 Setting up Workload Identity Federation for GitHub Actions..."

POOL_NAME="github"
PROVIDER_NAME="github"

# Create workload identity pool
gcloud iam workload-identity-pools create $POOL_NAME \
    --location="global" \
    --display-name="GitHub Actions Pool" \
    2>/dev/null || echo "  Pool already exists"

# Get pool full name
POOL_FULL_NAME=$(gcloud iam workload-identity-pools describe $POOL_NAME \
    --location=global \
    --format="value(name)")

# Get GitHub repo first (needed for attribute condition)
read -p "Enter your GitHub repository owner (e.g., arcinsights): " GITHUB_OWNER
if [ -z "$GITHUB_OWNER" ]; then
    echo "❌ GitHub repository owner cannot be empty"
    exit 1
fi

# Create OIDC provider with attribute condition
gcloud iam workload-identity-pools providers create-oidc $PROVIDER_NAME \
    --location="global" \
    --workload-identity-pool="$POOL_NAME" \
    --display-name="GitHub provider" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
    --attribute-condition="assertion.repository_owner == '${GITHUB_OWNER}'" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    2>/dev/null || echo "  Provider already exists"

# Wait a moment for provider to be fully created
sleep 2

# Get provider full name with error handling
PROVIDER_FULL_NAME=$(gcloud iam workload-identity-pools providers describe $PROVIDER_NAME \
    --location=global \
    --workload-identity-pool=$POOL_NAME \
    --format="value(name)" 2>/dev/null || true)

# If describe fails, construct the name manually
if [ -z "$PROVIDER_FULL_NAME" ]; then
    PROVIDER_FULL_NAME="${POOL_FULL_NAME}/providers/${PROVIDER_NAME}"
    echo "  Using constructed provider name: $PROVIDER_FULL_NAME"
fi

echo "✅ Workload Identity Federation configured"

# Get GitHub repo name
read -p "Enter your GitHub repository name (e.g., northcliffe-pricing-claude): " GITHUB_REPO_NAME
if [ -z "$GITHUB_REPO_NAME" ]; then
    echo "❌ GitHub repository name cannot be empty"
    exit 1
fi

GITHUB_REPO="${GITHUB_OWNER}/${GITHUB_REPO_NAME}"

# Grant GitHub Actions permission to impersonate service account
echo ""
echo "🔑 Granting GitHub Actions permission to impersonate service account..."

gcloud iam service-accounts add-iam-policy-binding \
    "terraform@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/${POOL_FULL_NAME}/attribute.repository/${GITHUB_REPO}"

echo "✅ GitHub Actions configured"

# Create initial config file
echo ""
echo "📝 Creating configuration files..."

cat > terraform/environments/prod.tfvars <<EOF
project_id = "$PROJECT_ID"
region     = "europe-west2"
environment = "prod"
EOF

echo "✅ Configuration files created"

# Summary
echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Add these secrets to your GitHub repository:"
echo "   Go to: https://github.com/${GITHUB_REPO}/settings/secrets/actions"
echo ""
echo "   GCP_PROJECT_ID:"
echo "   $PROJECT_ID"
echo ""
echo "   GCP_WORKLOAD_IDENTITY_PROVIDER:"
echo "   $PROVIDER_FULL_NAME"
echo ""
echo "   GCP_SERVICE_ACCOUNT:"
echo "   terraform@${PROJECT_ID}.iam.gserviceaccount.com"
echo ""
echo "   GCP_FUNCTIONS_SA:"
echo "   pricing-functions@${PROJECT_ID}.iam.gserviceaccount.com"
echo ""
echo "   GCP_SCHEDULER_SA:"
echo "   pricing-scheduler@${PROJECT_ID}.iam.gserviceaccount.com"
echo ""
echo "   GCP_DASHBOARD_SA:"
echo "   pricing-dashboard@${PROJECT_ID}.iam.gserviceaccount.com"
echo ""
echo "   GCP_REGION:"
echo "   europe-west2"
echo ""
echo "   APIFY_API_TOKEN:"
echo "   (Get from https://console.apify.com/account/integrations)"
echo ""
echo "2. Update config.yaml with your property details"
echo ""
echo "3. Commit and push to trigger deployment:"
echo "   git add ."
echo "   git commit -m 'Initial deployment'"
echo "   git push origin main"
echo ""
echo "📚 For detailed instructions, see README.md"
echo ""
