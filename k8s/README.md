# Kubernetes manifests (EKS)

Templates for deploying this gateway to EKS. See
[docs/aws-eks-deployment.md](../docs/aws-eks-deployment.md) for the full,
step-by-step guide (cluster creation, ECR push, RDS/ElastiCache, etc.);
this folder only holds the manifest files referenced from step 7-8 of
that guide.

These files can be edited/committed at any time — they are plain YAML and
do not require an EKS cluster to exist. They only take effect once you run
`kubectl apply` against a live cluster.

| File | Purpose | Placeholders to fill in |
|---|---|---|
| `configmap.yaml` | Non-secret runtime config | `REDIS_HOST` (ElastiCache endpoint) |
| `secret.yaml` | **Template only** — do not fill in and commit real values. Prefer creating the Secret via `kubectl create secret generic ...` or an `ExternalSecret` synced from AWS Secrets Manager. | n/a (imperative creation recommended) |
| `deployment.yaml` | Gateway Deployment | `<ACCOUNT_ID>` / image tag (ECR repo + pushed version) |
| `service.yaml` | ClusterIP Service | none |
| `ingress.yaml` | ALB Ingress (requires AWS Load Balancer Controller installed) | `<acm-cert-arn>`, `litellm.example.com` host |
| `hpa.yaml` | HorizontalPodAutoscaler (requires metrics-server) | none |

`deployment.yaml` also mounts a ConfigMap named `litellm-gateway-proxy-config`
at `/app/config.yaml` — create it from the repo's `litellm_config.yaml`, e.g.:

```powershell
kubectl create configmap litellm-gateway-proxy-config `
  --namespace litellm-gateway `
  --from-file=config.yaml=litellm_config.yaml
```

## Apply order

```powershell
kubectl create namespace litellm-gateway
kubectl create configmap litellm-gateway-proxy-config --namespace litellm-gateway --from-file=config.yaml=litellm_config.yaml
kubectl create secret generic litellm-gateway-secrets --namespace litellm-gateway --from-literal=...   # see secret.yaml for required keys
kubectl apply -f configmap.yaml -f deployment.yaml -f service.yaml -f ingress.yaml -f hpa.yaml -n litellm-gateway
```

`secret.yaml` is intentionally excluded from the `kubectl apply` line above —
create the Secret imperatively or via External Secrets instead of applying
the checked-in template directly.
