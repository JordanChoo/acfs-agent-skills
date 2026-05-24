# cloud-build — Extended Recipes

Long-form recipes referenced by SKILL.md. Open only when the short-form recipe isn't enough.

## R1. Cloud Run Service + Cloud Run Job deploy from one pipeline

Pattern: build once, push tagged image, deploy to both a long-running service and a batch job that share the image.

```yaml
substitutions:
  _REGION: us-central1
  _AR_REPO: app-images
  _SERVICE: my-service
  _JOB: my-job

steps:
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_AR_REPO}/app:${SHORT_SHA}'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_AR_REPO}/app:latest'
      - '.'
    id: 'build-image'

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '--all-tags', '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_AR_REPO}/app']
    id: 'push-image'
    waitFor: ['build-image']

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk:slim'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        set -euo pipefail
        gcloud run deploy "${_SERVICE}" \
          --image="${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_AR_REPO}/app:${SHORT_SHA}" \
          --region="${_REGION}" --quiet
    id: 'deploy-service'
    waitFor: ['push-image']

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk:slim'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        set -euo pipefail
        if gcloud run jobs describe "${_JOB}" --region="${_REGION}" --quiet >/dev/null 2>&1; then
          gcloud run jobs update "${_JOB}" \
            --image="${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_AR_REPO}/app:${SHORT_SHA}" \
            --region="${_REGION}" --quiet
        else
          gcloud run jobs create "${_JOB}" \
            --image="${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_AR_REPO}/app:${SHORT_SHA}" \
            --region="${_REGION}" --quiet
        fi
    id: 'deploy-job'
    waitFor: ['push-image']

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk:slim'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        set -euo pipefail
        URL=$(gcloud run services describe "${_SERVICE}" --region="${_REGION}" --format='value(status.url)')
        curl --fail --silent --show-error "${URL}/healthz"
    id: 'smoke-test'
    waitFor: ['deploy-service']

options:
  logging: CLOUD_LOGGING_ONLY
  machineType: E2_HIGHCPU_8
timeout: '2400s'
```

## R2. Terraform-gated approval pipeline

Pattern: an early step detects whether infra changed; if so, the trigger requires manual approval before continuing.

The approval gate lives at the **trigger** level — add `--require-approval` to the trigger that runs this config. To make the approval conditional on diff content, use **two triggers**:

```bash
# Auto-approve trigger: only fires when nothing under deploy/terraform/** changed
gcloud builds triggers create github \
  --name=ci-main-app-only \
  --region=us-central1 \
  --repo-owner=O --repo-name=R \
  --branch-pattern='^main$' \
  --build-config=cloudbuild.yaml \
  --included-files='src/**,cloudbuild.yaml' \
  --ignored-files='deploy/terraform/**'

# Approval-gated trigger: only fires when terraform/** changed
gcloud builds triggers create github \
  --name=ci-main-infra \
  --region=us-central1 \
  --repo-owner=O --repo-name=R \
  --branch-pattern='^main$' \
  --build-config=cloudbuild.terraform.yaml \
  --included-files='deploy/terraform/**' \
  --require-approval
```

In the terraform-config file, run `terraform plan` first and emit the plan as a build artifact; the approver reviews the plan before approving.

## R3. GitOps for triggers

Store trigger definitions under `triggers/*.yaml`. Round-trip via:

```bash
# Export every trigger to disk
mkdir -p triggers
for T in $(gcloud builds triggers list --region=us-central1 --format='value(name)'); do
  gcloud builds triggers export "$T" --destination="triggers/${T}.yaml" --region=us-central1
done

# Apply changes
gcloud builds triggers import --source=triggers/ci-main.yaml --region=us-central1
```

Wrap the import in a Cloud Build trigger that fires on changes to `triggers/**`. (Yes — Cloud Build deploying its own triggers.) That trigger needs `roles/cloudbuild.connectionAdmin` to mutate triggers.

## R4. Blue/green via Cloud Run revision tags

```yaml
- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk:slim'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      set -euo pipefail
      gcloud run deploy ${_SERVICE} \
        --image=${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_AR_REPO}/app:${SHORT_SHA} \
        --region=${_REGION} \
        --no-traffic \
        --tag=green-${SHORT_SHA} \
        --quiet
      # Smoke test the tagged URL
      URL=$(gcloud run services describe ${_SERVICE} --region=${_REGION} \
        --format="value(status.traffic[?tag='green-${SHORT_SHA}'].url)")
      curl --fail "${URL}/healthz"
      # Promote
      gcloud run services update-traffic ${_SERVICE} --region=${_REGION} \
        --to-tags=green-${SHORT_SHA}=100 --quiet
```

## R5. Caching `node_modules` between builds via Cloud Storage

Cloud Build has no first-class layer cache for non-Docker steps. Use a GCS rsync pattern:

```yaml
- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk:slim'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      set -euo pipefail
      gsutil -m -q rsync -r gs://${PROJECT_ID}-build-cache/node_modules node_modules || true
  id: 'restore-cache'

- name: 'node:22'
  entrypoint: 'npm'
  args: ['ci', '--prefer-offline']
  id: 'install'
  waitFor: ['restore-cache']

- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk:slim'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      set -euo pipefail
      gsutil -m -q rsync -d -r node_modules gs://${PROJECT_ID}-build-cache/node_modules
  id: 'save-cache'
  waitFor: ['install']
```
For Docker layer caches, push to Artifact Registry and use `--cache-from` in subsequent builds.

## R6. Private pool for VPC-attached resources

When the build needs to reach a private Cloud SQL instance, Memorystore, or a peered VPC service:

```bash
# Create a Service Networking peering, then:
gcloud builds worker-pools create internal-pool \
  --region=us-central1 \
  --peered-network=projects/${PROJECT_ID}/global/networks/build-vpc \
  --worker-machine-type=e2-standard-4 \
  --worker-disk-size=100GB
```
Reference in the config:
```yaml
options:
  pool:
    name: projects/${PROJECT_ID}/locations/us-central1/workerPools/internal-pool
```
Private pools cost more per minute than the default pool and don't share its log streaming UX. Use only when network access genuinely requires it.

## R7. Matrix builds (sort of)

Cloud Build has no native matrix. Two workable patterns:

**(a) One trigger per matrix cell** — fastest, fully parallel, expensive only in trigger management. Use GitOps (R3) so the matrix lives in code.

**(b) Single trigger, fan-out via `waitFor` siblings**:
```yaml
- name: 'node:18'
  entrypoint: 'npm'
  args: ['test']
  id: 'test-node-18'
  waitFor: ['-']
- name: 'node:20'
  entrypoint: 'npm'
  args: ['test']
  id: 'test-node-20'
  waitFor: ['-']
- name: 'node:22'
  entrypoint: 'npm'
  args: ['test']
  id: 'test-node-22'
  waitFor: ['-']
```
All three install + test in parallel (same step pulls deps fresh — no shared `node_modules`). For five-plus cells, switch to (a).
