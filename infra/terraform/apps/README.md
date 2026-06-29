# infra/terraform/apps

Provisions the AWS resources that `.github/workflows/deploy-apps.yml` needs to
build, push, and roll the resale apps (`apps/ec`, `apps/automation-studio`):

- **ECR repositories** (`iii-ec-worker`, `iii-automation-studio`) with
  scan-on-push and a keep-last-N lifecycle policy.
- **GitHub OIDC deploy role** (`iii-apps-prod-github-deploy`) trusted by
  `main` + the `iii-apps-prod` environment, with permissions to push to those
  ECR repos and run `ecs:UpdateService` for a rolling deploy.

It **reuses** the account-wide GitHub OIDC provider created by
`infra/terraform/website` (a per-account singleton) via a data source — it does
not create a second one.

## Apply

Same backend/bootstrap as the other modules (`infra/terraform/_bootstrap`):

```bash
cd infra/terraform/apps
terraform init
terraform apply
```

Then wire the outputs into GitHub:

| Terraform output | GitHub setting |
|---|---|
| `deploy_role_arn` | secret `AWS_DEPLOY_ROLE_ARN` |
| `ecr_registry`    | variable `ECR_REGISTRY` |

To enable the rolling deploy, also set the repo variables `ECS_CLUSTER` (and run
the apps as ECS services named `iii-ec-worker` / `iii-automation-studio`, or
adjust the `service` values in `deploy-apps.yml`). Until then the workflow
builds and pushes images and skips the rollout step.

> Scope the `EcsRollout` statement in `iam_github_oidc.tf` to your specific
> cluster/service ARNs once they exist; it defaults to `*` so the skeleton is
> usable before ECS is provisioned.
