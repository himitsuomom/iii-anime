# Role assumed by GitHub Actions (deploy-apps.yml) via OIDC to push images to
# ECR and roll the ECS services. Mirrors the website module's deploy role but
# scoped to the apps environment.
data "aws_iam_policy_document" "github_apps_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:${var.github_repo}:ref:refs/heads/main",
        "repo:${var.github_repo}:environment:${var.github_environment}",
      ]
    }
  }
}

resource "aws_iam_role" "github_deploy_apps" {
  name                 = "iii-apps-prod-github-deploy"
  description          = "Assumed by GitHub Actions (${var.github_repo}, ${var.github_environment}) to push app images to ECR and roll ECS services"
  assume_role_policy   = data.aws_iam_policy_document.github_apps_trust.json
  max_session_duration = 3600
}

data "aws_iam_policy_document" "github_deploy_apps" {
  # ECR auth token is account-wide and must be granted on "*".
  statement {
    sid       = "EcrAuth"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  # Push/pull, scoped to the managed repositories only.
  statement {
    sid    = "EcrPushPull"
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
      "ecr:PutImage",
    ]
    resources = [for r in aws_ecr_repository.app : r.arn]
  }

  # Rolling deploy (force-new-deployment). Scope to your cluster/service ARNs in
  # production; "*" here keeps the skeleton usable before ECS is provisioned.
  statement {
    sid    = "EcsRollout"
    effect = "Allow"
    actions = [
      "ecs:UpdateService",
      "ecs:DescribeServices",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "github_deploy_apps" {
  name   = "iii-apps-prod-github-deploy"
  policy = data.aws_iam_policy_document.github_deploy_apps.json
}

resource "aws_iam_role_policy_attachment" "github_deploy_apps" {
  role       = aws_iam_role.github_deploy_apps.name
  policy_arn = aws_iam_policy.github_deploy_apps.arn
}
