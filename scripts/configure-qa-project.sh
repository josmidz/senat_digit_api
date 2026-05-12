#!/usr/bin/env bash
# =============================================================================
# configure-qa-project.sh
#
# Idempotent script to configure GitHub Organization Project #33
# (digipublic243) as a manual QA / test-tracking board.
#
# Requirements:
#   - gh CLI authenticated with a token that has the "project" scope
#     (classic PAT with admin:org + project, or fine-grained with
#      Organization projects: Read and write)
#   - jq
#
# Usage:
#   export GH_TOKEN="ghp_..."   # or use gh auth login
#   bash scripts/configure-qa-project.sh
# =============================================================================
set -euo pipefail

ORG="digipublic243"
PROJECT_NUMBER=33

echo "============================================"
echo " QA Project Configuration"
echo " Org: $ORG  |  Project: #$PROJECT_NUMBER"
echo "============================================"
echo ""

# -----------------------------------------------------------------
# Step 1 — Resolve the project node ID
# -----------------------------------------------------------------
echo "🔍 Querying project node ID …"
PROJECT_QUERY='
query($org: String!, $number: Int!) {
  organization(login: $org) {
    projectV2(number: $number) {
      id
      title
    }
  }
}'

PROJECT_RESPONSE=$(gh api graphql -f query="$PROJECT_QUERY" \
  -F org="$ORG" -F number="$PROJECT_NUMBER" 2>&1) || {
  echo "❌ Failed to query project. Response:"
  echo "$PROJECT_RESPONSE"
  echo ""
  echo "Make sure your token has the 'project' scope."
  exit 1
}

PROJECT_ID=$(echo "$PROJECT_RESPONSE" | jq -r '.data.organization.projectV2.id')
PROJECT_TITLE=$(echo "$PROJECT_RESPONSE" | jq -r '.data.organization.projectV2.title')

if [[ "$PROJECT_ID" == "null" || -z "$PROJECT_ID" ]]; then
  echo "❌ Could not resolve project. Check that project #$PROJECT_NUMBER exists in $ORG."
  echo "$PROJECT_RESPONSE"
  exit 1
fi

echo "✅ Project: \"$PROJECT_TITLE\""
echo "   ID: $PROJECT_ID"
echo ""

# -----------------------------------------------------------------
# Step 2 — Fetch all existing fields
# -----------------------------------------------------------------
echo "🔍 Fetching existing project fields …"
FIELDS_QUERY='
query($projectId: ID!) {
  node(id: $projectId) {
    ... on ProjectV2 {
      fields(first: 50) {
        nodes {
          ... on ProjectV2Field {
            id
            name
            dataType
          }
          ... on ProjectV2IterationField {
            id
            name
            dataType
          }
          ... on ProjectV2SingleSelectField {
            id
            name
            dataType
            options {
              id
              name
            }
          }
        }
      }
    }
  }
}'

FIELDS_RESPONSE=$(gh api graphql -f query="$FIELDS_QUERY" -F projectId="$PROJECT_ID")
FIELDS_JSON=$(echo "$FIELDS_RESPONSE" | jq '.data.node.fields.nodes')

echo ""
echo "📋 Existing fields:"
echo "$FIELDS_JSON" | jq -r '.[] | "   - \(.name) (\(.dataType))"'
echo ""

# -----------------------------------------------------------------
# Helper: check if a field with a given name already exists
# Returns the field ID or empty string
# -----------------------------------------------------------------
field_id_by_name() {
  local name="$1"
  echo "$FIELDS_JSON" | jq -r --arg n "$name" '.[] | select(.name == $n) | .id' | head -1
}

# -----------------------------------------------------------------
# Helper: create a single-select field
# -----------------------------------------------------------------
create_single_select() {
  local field_name="$1"
  shift
  local options=("$@")

  local existing_id
  existing_id=$(field_id_by_name "$field_name")

  if [[ -n "$existing_id" ]]; then
    echo "⏭️  Field \"$field_name\" already exists (ID: $existing_id). Skipping."
    return
  fi

  echo "➕ Creating single-select field: \"$field_name\" …"

  # Build the options JSON array
  local opts_json="["
  for i in "${!options[@]}"; do
    if [[ $i -gt 0 ]]; then opts_json+=","; fi
    opts_json+="{\"name\":\"${options[$i]}\",\"description\":\"\",\"color\":\"GRAY\"}"
  done
  opts_json+="]"

  local mutation='
  mutation($projectId: ID!, $name: String!, $options: [ProjectV2SingleSelectFieldOptionInput!]!) {
    createProjectV2Field(input: {
      projectId: $projectId
      dataType: SINGLE_SELECT
      name: $name
      singleSelectOptions: $options
    }) {
      projectV2Field {
        ... on ProjectV2SingleSelectField {
          id
          name
          options { id name }
        }
      }
    }
  }'

  local result
  result=$(jq -n \
    --arg query "$mutation" \
    --arg projectId "$PROJECT_ID" \
    --arg name "$field_name" \
    --argjson options "$opts_json" \
    '{query: $query, variables: {projectId: $projectId, name: $name, options: $options}}' \
  | gh api graphql --input - 2>&1) || {
    echo "   ❌ Failed to create \"$field_name\":"
    echo "   $result"
    MANUAL_STEPS+=("Create single-select field \"$field_name\" manually in project settings.")
    return
  }

  local new_id
  new_id=$(echo "$result" | jq -r '.data.createProjectV2Field.projectV2Field.id // empty')
  if [[ -n "$new_id" ]]; then
    echo "   ✅ Created \"$field_name\" (ID: $new_id)"
    CREATED_FIELDS+=("$field_name")
  else
    echo "   ⚠️  Unexpected response for \"$field_name\":"
    echo "   $result"
    MANUAL_STEPS+=("Verify field \"$field_name\" was created correctly.")
  fi
}

# -----------------------------------------------------------------
# Helper: create a text field
# -----------------------------------------------------------------
create_text_field() {
  local field_name="$1"

  local existing_id
  existing_id=$(field_id_by_name "$field_name")

  if [[ -n "$existing_id" ]]; then
    echo "⏭️  Field \"$field_name\" already exists (ID: $existing_id). Skipping."
    return
  fi

  echo "➕ Creating text field: \"$field_name\" …"

  local mutation='
  mutation($projectId: ID!, $name: String!) {
    createProjectV2Field(input: {
      projectId: $projectId
      dataType: TEXT
      name: $name
    }) {
      projectV2Field {
        ... on ProjectV2Field {
          id
          name
        }
      }
    }
  }'

  local result
  result=$(gh api graphql \
    -f query="$mutation" \
    -F projectId="$PROJECT_ID" \
    -F name="$field_name" 2>&1) || {
    echo "   ❌ Failed to create \"$field_name\":"
    echo "   $result"
    MANUAL_STEPS+=("Create text field \"$field_name\" manually in project settings.")
    return
  }

  local new_id
  new_id=$(echo "$result" | jq -r '.data.createProjectV2Field.projectV2Field.id // empty')
  if [[ -n "$new_id" ]]; then
    echo "   ✅ Created \"$field_name\" (ID: $new_id)"
    CREATED_FIELDS+=("$field_name")
  else
    echo "   ⚠️  Unexpected response for \"$field_name\":"
    echo "   $result"
    MANUAL_STEPS+=("Verify field \"$field_name\" was created correctly.")
  fi
}

# -----------------------------------------------------------------
# Helper: create a date field
# -----------------------------------------------------------------
create_date_field() {
  local field_name="$1"

  local existing_id
  existing_id=$(field_id_by_name "$field_name")

  if [[ -n "$existing_id" ]]; then
    echo "⏭️  Field \"$field_name\" already exists (ID: $existing_id). Skipping."
    return
  fi

  echo "➕ Creating date field: \"$field_name\" …"

  local mutation='
  mutation($projectId: ID!, $name: String!) {
    createProjectV2Field(input: {
      projectId: $projectId
      dataType: DATE
      name: $name
    }) {
      projectV2Field {
        ... on ProjectV2Field {
          id
          name
        }
      }
    }
  }'

  local result
  result=$(gh api graphql \
    -f query="$mutation" \
    -F projectId="$PROJECT_ID" \
    -F name="$field_name" 2>&1) || {
    echo "   ❌ Failed to create \"$field_name\":"
    echo "   $result"
    MANUAL_STEPS+=("Create date field \"$field_name\" manually in project settings.")
    return
  }

  local new_id
  new_id=$(echo "$result" | jq -r '.data.createProjectV2Field.projectV2Field.id // empty')
  if [[ -n "$new_id" ]]; then
    echo "   ✅ Created \"$field_name\" (ID: $new_id)"
    CREATED_FIELDS+=("$field_name")
  else
    echo "   ⚠️  Unexpected response for \"$field_name\":"
    echo "   $result"
    MANUAL_STEPS+=("Verify field \"$field_name\" was created correctly.")
  fi
}

# -----------------------------------------------------------------
# Step 3 — Create missing fields
# -----------------------------------------------------------------
CREATED_FIELDS=()
MANUAL_STEPS=()

echo "──────────────────────────────────────────"
echo " Creating missing custom fields"
echo "──────────────────────────────────────────"
echo ""

# Module (single select)
create_single_select "Module" \
  "Authentification" "Utilisateurs" "Rôles & Permissions" \
  "Tableau de bord" "Notifications" "API" "Base de données" "Autre"

# Environment (single select)
create_single_select "Environment" \
  "Local" "Dev" "Staging" "Production"

# Result (single select)
create_single_select "Result" \
  "Réussi" "Échoué"

# Version / Build (text)
create_text_field "Version / Build"

# Tester (text)
create_text_field "Tester"

# Test Date (date)
create_date_field "Test Date"

echo ""

# -----------------------------------------------------------------
# Step 4 — Check for Status field
# -----------------------------------------------------------------
echo "──────────────────────────────────────────"
echo " Checking built-in Status field"
echo "──────────────────────────────────────────"
echo ""

STATUS_ID=$(field_id_by_name "Status")
if [[ -n "$STATUS_ID" ]]; then
  STATUS_OPTIONS=$(echo "$FIELDS_JSON" | jq -r '.[] | select(.name == "Status") | .options[]?.name' 2>/dev/null || true)
  echo "✅ Built-in Status field found (ID: $STATUS_ID)"
  if [[ -n "$STATUS_OPTIONS" ]]; then
    echo "   Current options:"
    echo "$STATUS_OPTIONS" | while read -r opt; do echo "     - $opt"; done
  fi
  echo ""
  echo "   ℹ️  The Status field is built-in. To use it for QA tracking,"
  echo "      configure its options in the project settings to include:"
  echo "        • À tester"
  echo "        • En cours"
  echo "        • Réussi"
  echo "        • Échoué"
  echo "        • Corrigé"
  echo ""
  echo "   Note: The GitHub API does not support modifying built-in Status"
  echo "   field options. This must be done manually in the project board UI:"
  echo "   https://github.com/orgs/$ORG/projects/$PROJECT_NUMBER/settings"
  MANUAL_STEPS+=("Configure Status field options (À tester, En cours, Réussi, Échoué, Corrigé) in the project board UI.")
else
  echo "⚠️  No Status field found. It should exist by default in GitHub Projects V2."
  MANUAL_STEPS+=("Verify Status field exists in the project.")
fi

echo ""

# -----------------------------------------------------------------
# Step 5 — Print summary
# -----------------------------------------------------------------
echo "============================================"
echo " SUMMARY"
echo "============================================"
echo ""
echo "📌 Project ID:    $PROJECT_ID"
echo "📌 Project Title: $PROJECT_TITLE"
echo ""

echo "📋 Existing fields found:"
echo "$FIELDS_JSON" | jq -r '.[] | "   - \(.name) (\(.dataType))"'
echo ""

if [[ ${#CREATED_FIELDS[@]} -gt 0 ]]; then
  echo "✅ New fields created:"
  for f in "${CREATED_FIELDS[@]}"; do
    echo "   - $f"
  done
else
  echo "✅ No new fields needed — all fields already exist."
fi
echo ""

if [[ ${#MANUAL_STEPS[@]} -gt 0 ]]; then
  echo "⚠️  Manual steps required:"
  for step in "${MANUAL_STEPS[@]}"; do
    echo "   - $step"
  done
else
  echo "✅ No manual steps required."
fi
echo ""
echo "============================================"
echo " Done!"
echo "============================================"