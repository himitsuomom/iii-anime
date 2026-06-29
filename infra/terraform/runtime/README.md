# infra/terraform/runtime

The ECS Fargate runtime for the resale stack: the **engine**, the **EC worker**,
and **automation-studio** (public, behind an ALB with TLS), on a dedicated VPC.

```
internet ──HTTPS──> ALB ──8787──> automation-studio ─┐
                                                      ├─ ws://engine.iii.local:49134 ─> engine (Cloud Map)
                                   ec-worker ─────────┘
```

- **VPC** (`terraform-aws-modules/vpc/aws`): 2 AZs, public subnets (ALB) +
  private subnets (Fargate tasks) with a single NAT gateway.
- **ECS cluster** (Fargate, Container Insights) + a Cloud Map private namespace
  `iii.local`; the engine registers as `engine.iii.local`, which the workers
  reach at `ws://engine.iii.local:49134`.
- **engine** uses the config-baked image (`deploy/engine.Dockerfile`).
- **automation-studio** is fronted by an ALB: ACM cert (DNS-validated in the
  `iii.dev` Route53 zone), HTTPS listener, HTTP→HTTPS redirect, and a Route53
  alias for `var.domain`. Health check: `/api/health`.
- Secrets (`ANTHROPIC_API_KEY`, `SHOPIFY_WEBHOOK_SECRET`) are read from
  Secrets Manager by ARN and injected as container secrets — their values never
  enter Terraform state.

## Apply order

1. `infra/terraform/apps` — `terraform apply` (creates the ECR repos incl.
   `iii-engine`, and the OIDC deploy role).
2. Create the two secrets in Secrets Manager and note their ARNs:
   ```bash
   aws secretsmanager create-secret --name iii/anthropic-api-key       --secret-string "$ANTHROPIC_API_KEY"
   aws secretsmanager create-secret --name iii/shopify-webhook-secret  --secret-string "$SHOPIFY_WEBHOOK_SECRET"
   ```
3. Build & push the images: run the **Deploy Apps** workflow
   (`deploy-apps.yml`) once (it pushes `iii-engine`, `iii-ec-worker`,
   `iii-automation-studio`). The `:latest` tag (or a SHA) feeds the `*_image`
   vars below.
4. `infra/terraform/runtime` — `terraform apply` with, e.g.:
   ```bash
   terraform apply \
     -var 'domain=app.iii.dev' \
     -var "engine_image=$REG/iii-engine:latest" \
     -var "ec_worker_image=$REG/iii-ec-worker:latest" \
     -var "automation_studio_image=$REG/iii-automation-studio:latest" \
     -var "anthropic_secret_arn=$ANTHROPIC_ARN" \
     -var "shopify_webhook_secret_arn=$SHOPIFY_ARN"
   ```
   (`$REG` = the `ecr_registry` output of the apps module.)
5. Enable the rolling deploy: set the GitHub Actions variable
   `ECS_CLUSTER` to the `cluster_name` output (service names already match the
   `deploy-apps.yml` matrix). Subsequent workflow runs roll the services.

## Verify

```bash
curl https://<domain>/api/health      # {"ok":true,...}
curl https://<domain>/api/stats        # workerConnected:true once the engine + EC worker are up
```

> Cost note: a NAT gateway, an ALB, and 3 Fargate services run continuously.
> Tune `desired_count` / `*_cpu` / `*_memory`, or scale services to 0 when idle.
