# Deploying to AWS EKS

How to take the containers built from this repo (`Dockerfile`, today run via
`docker-compose.quickstart.yml`) and run them on Amazon EKS instead, with the
stateful pieces (Postgres, Redis) moved to managed AWS services. This is a setup
guide, not a turnkey script: adapt names, regions, and sizes to your account.

Scope mapping from the compose stack:

| Compose service | EKS equivalent |
|---|---|
| `litellm` (built image) | Kubernetes `Deployment` + `Service`, image in Amazon ECR |
| `db` (Postgres 16 container) | Amazon RDS for PostgreSQL (recommended) or a StatefulSet if you must self-host |
| `redis` (Redis 7 container) | Amazon ElastiCache for Redis (recommended) or a StatefulSet |
| `.env` secrets | AWS Secrets Manager, synced into Kubernetes `Secret`s |
| `monitoring/docker-compose.monitoring.yml` | Deployed the same way (Prometheus/Grafana/Loki/otel-collector manifests or the kube-prometheus-stack Helm chart), or replaced by Amazon Managed Prometheus/Grafana |

---

## 1. Prerequisites

- An AWS account and a user/role with permissions for EKS, ECR, VPC, IAM, RDS,
  ElastiCache, and Secrets Manager.
- Tools installed locally or in CI: `aws` CLI v2, `kubectl`, `eksctl`, `helm`
  (optional, for ingress/monitoring charts), `docker`.
- Decide region, e.g. `us-east-1`, and a cluster name, e.g. `litellm-gateway`.

```powershell
aws configure
aws sts get-caller-identity   # confirms credentials work
```

## 2. Build and push the image to ECR

The gateway image bakes in pinned Python packages and model weights at build
time (see the `Dockerfile` header), so build it once per release and push it —
do not rebuild on every pod start.

```powershell
aws ecr create-repository --repository-name litellm-gateway --region us-east-1

$ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
$REGION = "us-east-1"
$REPO = "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/litellm-gateway"

aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

docker build -t "${REPO}:v1.106.0" .
docker push "${REPO}:v1.106.0"
```

Re-tag and push again whenever the `Dockerfile` pins (base image, package
versions, model revisions) change.

## 3. Create the EKS cluster

```powershell
eksctl create cluster `
  --name litellm-gateway `
  --region us-east-1 `
  --version 1.30 `
  --nodegroup-name workers `
  --node-type m5.xlarge `
  --nodes 2 `
  --nodes-min 2 `
  --nodes-max 4 `
  --managed
```

Notes:
- Size nodes around the same CPU/memory you gave the container in compose
  (`LITELLM_MEM_LIMIT`, `LITELLM_CPUS`): each worker process holds about 1 GB
  for the compression/classification models, so `NUM_WORKERS x ~1.2 GB` plus
  headroom is a reasonable request/limit.
- `--managed` uses a managed node group; use Fargate profiles instead if you
  want no node management, but note Fargate pods cannot use `hostPath`/EBS the
  way a self-hosted Postgres/Redis StatefulSet would need.
- `eksctl` wires up IAM OIDC automatically; confirm with
  `eksctl utils associate-iam-oidc-provider --cluster litellm-gateway --approve`
  if you created the cluster another way.

```powershell
aws eks update-kubeconfig --name litellm-gateway --region us-east-1
kubectl get nodes
```

## 4. Managed Postgres and Redis

Replace the `db` and `redis` compose services with managed equivalents in the
same VPC as the cluster (lower operational risk than running stateful
databases on EKS, and this repo's containers already only need a connection
string/host, not local storage).

```powershell
# RDS for PostgreSQL (Multi-AZ optional)
aws rds create-db-instance `
  --db-instance-identifier litellm-gateway-db `
  --db-instance-class db.t3.medium `
  --engine postgres --engine-version 16 `
  --master-username litellm --master-user-password "<POSTGRES_PASSWORD>" `
  --allocated-storage 20 `
  --vpc-security-group-ids <sg-id> --db-subnet-group-name <subnet-group>

# ElastiCache for Redis, with AUTH (matches REDIS_PASSWORD in compose)
aws elasticache create-replication-group `
  --replication-group-id litellm-gateway-redis `
  --replication-group-description "litellm-gateway" `
  --engine redis --cache-node-type cache.t3.medium `
  --num-cache-clusters 1 --transit-encryption-enabled --auth-token "<REDIS_PASSWORD>"
```

Put the resulting endpoints into the `Secret`/`ConfigMap` in step 6:
`DATABASE_URL=postgresql://litellm:<password>@<rds-endpoint>:5432/litellm`,
`REDIS_HOST=<elasticache-endpoint>`, `REDIS_PORT=6379`.

Security groups: allow inbound 5432/6379 only from the EKS node security group
(or VPC CIDR), not `0.0.0.0/0`.

## 5. Namespace

```powershell
kubectl create namespace litellm-gateway
```

## 6. Secrets and config

Every value that is `${VAR:?set it in .env}` in `docker-compose.quickstart.yml`
is required here too. Store secrets in AWS Secrets Manager and sync them into
the cluster rather than committing a plaintext `Secret` manifest — install the
[External Secrets Operator](https://external-secrets.io/) (or the AWS Secrets
and Configuration Provider for the Secrets Store CSI Driver) via Helm, grant it
an IRSA role scoped to `secretsmanager:GetSecretValue`, then reference your
AWS secret from a Kubernetes `ExternalSecret`.

For a first pass without External Secrets, create the `Secret` directly
(replace with your real values, generated the same way as for compose:
`openssl rand -hex 32`):

```powershell
kubectl create secret generic litellm-gateway-secrets `
  --namespace litellm-gateway `
  --from-literal=LITELLM_MASTER_KEY=sk-... `
  --from-literal=LITELLM_SALT_KEY=sk-... `
  --from-literal=DATABASE_URL=postgresql://litellm:...@<rds-endpoint>:5432/litellm `
  --from-literal=REDIS_PASSWORD=... `
  --from-literal=LANGFUSE_PUBLIC_KEY=pk-lf-... `
  --from-literal=LANGFUSE_SECRET_KEY=sk-lf-... `
  --from-literal=OBS_HASH_SALT=...
```

Non-secret, per-environment settings (`PROMPT_COMPRESSION_*`,
`CONTEXT_ENGINEERING_*`, `OTEL_*`, see `prompt_compression.env.example` and
`context_engineering.env.example`) go in a `ConfigMap`:

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: litellm-gateway-config
  namespace: litellm-gateway
data:
  NUM_WORKERS: "2"
  OMP_NUM_THREADS: "4"
  HF_HUB_OFFLINE: "1"
  TRANSFORMERS_OFFLINE: "1"
  STORE_MODEL_IN_DB: "True"
  REDIS_HOST: "<elasticache-endpoint>"
  REDIS_PORT: "6379"
  LITELLM_OTEL_V2: "true"
  OTEL_EXPORTER: "otlp_http"
  OTEL_EXPORTER_OTLP_ENDPOINT: "http://otel-collector.monitoring.svc.cluster.local:4318"
  OTEL_SERVICE_NAME: "litellm-gateway"
  OTEL_ENVIRONMENT_NAME: "production"
  OBS_ENABLED: "true"
  OBS_CAPTURE_TEXT: "false"
```

The `litellm_config.yaml` file that compose mounts as a volume
(`/app/config.yaml`) should instead be baked into the image or supplied as a
second `ConfigMap` mounted at the same path — use whichever your rollout
process prefers; a `ConfigMap` volume lets you change routing without
rebuilding the image.

## 7. Kubernetes manifests

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: litellm-gateway
  namespace: litellm-gateway
spec:
  replicas: 2
  selector:
    matchLabels:
      app: litellm-gateway
  template:
    metadata:
      labels:
        app: litellm-gateway
    spec:
      containers:
        - name: litellm-gateway
          image: <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/litellm-gateway:v1.106.0
          args: ["--config", "/app/config.yaml"]
          ports:
            - containerPort: 4000
          envFrom:
            - configMapRef:
                name: litellm-gateway-config
            - secretRef:
                name: litellm-gateway-secrets
          resources:
            requests:
              cpu: "4"
              memory: "3Gi"
            limits:
              cpu: "8"
              memory: "6Gi"
          readinessProbe:
            httpGet:
              path: /health/readiness
              port: 4000
            initialDelaySeconds: 30
            periodSeconds: 15
          livenessProbe:
            httpGet:
              path: /health/liveliness
              port: 4000
            initialDelaySeconds: 120   # model load, matches start_period in docker-compose.quickstart.yml
            periodSeconds: 15
            failureThreshold: 5
          volumeMounts:
            - name: litellm-config
              mountPath: /app/config.yaml
              subPath: config.yaml
      volumes:
        - name: litellm-config
          configMap:
            name: litellm-gateway-proxy-config
---
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: litellm-gateway
  namespace: litellm-gateway
spec:
  selector:
    app: litellm-gateway
  ports:
    - port: 4000
      targetPort: 4000
  type: ClusterIP
```

Resource requests/limits above mirror `LITELLM_CPUS`/`LITELLM_MEM_LIMIT` in
`docker-compose.quickstart.yml`; adjust to `NUM_WORKERS` in your `ConfigMap`.

### Exposing it: ALB Ingress

Install the AWS Load Balancer Controller (Helm chart `aws-load-balancer-controller`,
needs an IRSA role with the published IAM policy), then:

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: litellm-gateway
  namespace: litellm-gateway
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing   # use "internal" to keep it off the public internet
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: <acm-cert-arn>
spec:
  rules:
    - host: litellm.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: litellm-gateway
                port:
                  number: 4000
```

`litellm_config.yaml` leaves `/metrics` unauthenticated behind TLS only; put
the ALB behind a TLS certificate (as above) and do not expose this Service
directly with `type: LoadBalancer`, which would skip the ALB/TLS layer.

### Autoscaling

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: litellm-gateway
  namespace: litellm-gateway
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: litellm-gateway
  minReplicas: 2
  maxReplicas: 6
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

Redis-backed shared state (`REDIS_HOST`/`REDIS_PASSWORD` in the `ConfigMap`/
`Secret`) is what makes horizontal pod scaling safe — rate limits, budgets,
router state, and cache are shared across replicas, same as across compose
workers.

## 8. Apply and verify

```powershell
kubectl apply -f configmap.yaml -f secret.yaml -f deployment.yaml -f service.yaml -f ingress.yaml -f hpa.yaml -n litellm-gateway

kubectl -n litellm-gateway rollout status deployment/litellm-gateway
kubectl -n litellm-gateway get pods
kubectl -n litellm-gateway logs -l app=litellm-gateway --tail=100

# from inside the cluster or via port-forward
kubectl -n litellm-gateway port-forward svc/litellm-gateway 4000:4000
curl http://127.0.0.1:4000/health/liveliness
```

## 9. Monitoring and evals on EKS

`monitoring/docker-compose.monitoring.yml` (Prometheus, Grafana, Loki,
Alertmanager, otel-collector) can be ported to the cluster the same way:
either translate each service to a `Deployment`/`Service` in a `monitoring`
namespace, or install the `kube-prometheus-stack` and `grafana-loki` Helm
charts and import the dashboards from `monitoring/grafana/dashboards/`. Point
`OTEL_EXPORTER_OTLP_ENDPOINT` in the gateway's `ConfigMap` at the in-cluster
otel-collector Service. `evals/` (`evals/run_evals.sh`) can run as a
`CronJob` or a CI step against the cluster's Service endpoint; it does not
need to run inside the cluster.

## 10. Rollout and rollback

```powershell
# new image after a Dockerfile/pin change
docker build -t "${REPO}:v1.106.1" .
docker push "${REPO}:v1.106.1"
kubectl -n litellm-gateway set image deployment/litellm-gateway litellm-gateway="${REPO}:v1.106.1"
kubectl -n litellm-gateway rollout status deployment/litellm-gateway

# rollback
kubectl -n litellm-gateway rollout undo deployment/litellm-gateway
```

## Checklist

- [ ] Image built and pushed to ECR with the same pins as `Dockerfile`.
- [ ] RDS Postgres and ElastiCache Redis created, reachable only from the
      cluster's security group.
- [ ] Secrets in Secrets Manager (or a `Secret` object), never committed to git.
- [ ] `litellm_config.yaml` mounted/baked the same as in compose.
- [ ] Readiness/liveness probes point at `/health/readiness` and
      `/health/liveliness`, with `initialDelaySeconds` covering model load.
- [ ] Ingress terminates TLS before `/metrics` is reachable.
- [ ] `OTEL_EXPORTER_OTLP_ENDPOINT` points at an in-cluster or managed
      collector.
- [ ] HPA and Redis-backed shared state are both enabled before scaling beyond
      1 replica.
