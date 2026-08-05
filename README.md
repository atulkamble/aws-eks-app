# Kubernetes Application Deployment Project on AWS EKS

This project deploys a simple Python Flask web application to **Amazon EKS** using:

* Docker
* Amazon ECR
* Amazon EKS
* Kubernetes Deployment
* ClusterIP Service
* AWS Network Load Balancer
* ConfigMap and Secret
* Health probes
* Horizontal Pod Autoscaler

Amazon EKS is AWS’s managed Kubernetes platform. The simplest learning approach is to create the cluster with `eksctl`, deploy the application using Kubernetes manifests, and expose it through an AWS load balancer. ([AWS Documentation][1])

---

## 1. Project architecture

```text
User
  |
  v
AWS Network Load Balancer
  |
  v
Kubernetes Service
  |
  v
Flask Application Pods
  |
  v
Kubernetes Deployment
  |
  v
Amazon EKS Worker Nodes
```

Application image flow:

```text
Application Code
      |
      v
Docker Image
      |
      v
Amazon ECR
      |
      v
Amazon EKS Deployment
```

---

## 2. Project directory

```text
aws-eks-app-project/
├── app.py
├── requirements.txt
├── Dockerfile
├── .dockerignore
└── kubernetes/
    ├── namespace.yaml
    ├── configmap.yaml
    ├── secret.yaml
    ├── deployment.yaml
    ├── service.yaml
    └── hpa.yaml
```

Create the project:

```bash
mkdir -p aws-eks-app-project/kubernetes
cd aws-eks-app-project
```

---

# 3. Create the application

## `app.py`

```python
import os
import socket
from flask import Flask, jsonify

app = Flask(__name__)

APP_NAME = os.getenv("APP_NAME", "Cloudnautic EKS Application")
APP_ENV = os.getenv("APP_ENV", "development")
APP_PASSWORD = os.getenv("APP_PASSWORD", "not-configured")


@app.route("/")
def home():
    return jsonify(
        {
            "message": "Application successfully deployed on Amazon EKS",
            "application": APP_NAME,
            "environment": APP_ENV,
            "hostname": socket.gethostname()
        }
    )


@app.route("/health")
def health():
    return jsonify(
        {
            "status": "healthy"
        }
    ), 200


@app.route("/secret-status")
def secret_status():
    return jsonify(
        {
            "secretConfigured": APP_PASSWORD != "not-configured"
        }
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000
    )
```

## `requirements.txt`

```text
Flask==3.1.1
gunicorn==23.0.0
```

## `Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
```

## `.dockerignore`

```text
.git
.gitignore
__pycache__
*.pyc
.env
kubernetes
README.md
```

---

# 4. Test locally

Build the image:

```bash
docker build -t eks-python-app:v1 .
```

Run the container:

```bash
docker run -d \
  --name eks-python-app \
  -p 5000:5000 \
  -e APP_NAME="Cloudnautic Application" \
  -e APP_ENV="local" \
  eks-python-app:v1
```

Test:

```bash
curl http://localhost:5000
```

Health check:

```bash
curl http://localhost:5000/health
```

Check the container:

```bash
docker ps
docker logs eks-python-app
```

Remove it:

```bash
docker rm -f eks-python-app
```

---

# 5. Configure AWS CLI

Check the installed tools:

```bash
aws --version
kubectl version --client
eksctl version
docker --version
```

Configure AWS credentials:

```bash
aws configure
```

Enter:

```text
AWS Access Key ID:
AWS Secret Access Key:
Default region name: us-east-1
Default output format: json
```

Verify:

```bash
aws sts get-caller-identity
```

Set environment variables:

```bash
export AWS_REGION=us-east-1
export CLUSTER_NAME=cloudnautic-eks-cluster
export ECR_REPOSITORY=eks-python-app
```

Get the AWS account ID:

```bash
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity \
  --query Account \
  --output text)
```

Check:

```bash
echo $AWS_ACCOUNT_ID
```

---

# 6. Create Amazon ECR repository

```bash
aws ecr create-repository \
  --repository-name $ECR_REPOSITORY \
  --region $AWS_REGION
```

Authenticate Docker:

```bash
aws ecr get-login-password \
  --region $AWS_REGION |
docker login \
  --username AWS \
  --password-stdin \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
```

Tag the image:

```bash
docker tag eks-python-app:v1 \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:v1
```

Push the image:

```bash
docker push \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:v1
```

Verify:

```bash
aws ecr list-images \
  --repository-name $ECR_REPOSITORY \
  --region $AWS_REGION
```

---

# 7. Create the Amazon EKS cluster

For a learning environment, `eksctl` is the fastest AWS-documented way to create an EKS cluster and worker nodes. ([AWS Documentation][2])

```bash
eksctl create cluster \
  --name $CLUSTER_NAME \
  --region $AWS_REGION \
  --nodegroup-name worker-nodes \
  --node-type t3.medium \
  --nodes 2 \
  --nodes-min 2 \
  --nodes-max 4 \
  --managed
```

Update kubeconfig:

```bash
aws eks update-kubeconfig \
  --region $AWS_REGION \
  --name $CLUSTER_NAME
```

Verify the cluster:

```bash
kubectl cluster-info
kubectl get nodes
kubectl get nodes -o wide
```

Expected result:

```text
NAME                             STATUS   ROLES    AGE   VERSION
ip-192-168-x-x.ec2.internal      Ready    <none>   5m    v1.xx.x
ip-192-168-x-x.ec2.internal      Ready    <none>   5m    v1.xx.x
```

---

# 8. Kubernetes manifests

## `kubernetes/namespace.yaml`

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cloudnautic
```

## `kubernetes/configmap.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: eks-app-config
  namespace: cloudnautic
data:
  APP_NAME: "Cloudnautic Kubernetes Application"
  APP_ENV: "production"
```

## `kubernetes/secret.yaml`

The value under `stringData` is converted by Kubernetes when the Secret is created. Kubernetes Secrets prevent credentials from being written directly into the Pod specification or container image, though production environments should also enable appropriate encryption and access controls. ([Kubernetes][3])

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: eks-app-secret
  namespace: cloudnautic
type: Opaque
stringData:
  APP_PASSWORD: "ChangeThisPassword123"
```

Do not commit real passwords to Git.

## `kubernetes/deployment.yaml`

Replace the image with your ECR image URI.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: eks-python-app
  namespace: cloudnautic
  labels:
    app: eks-python-app
spec:
  replicas: 2

  selector:
    matchLabels:
      app: eks-python-app

  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1

  template:
    metadata:
      labels:
        app: eks-python-app

    spec:
      containers:
        - name: eks-python-app
          image: AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/eks-python-app:v1

          imagePullPolicy: Always

          ports:
            - name: http
              containerPort: 5000
              protocol: TCP

          envFrom:
            - configMapRef:
                name: eks-app-config

            - secretRef:
                name: eks-app-secret

          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"

            limits:
              cpu: "500m"
              memory: "256Mi"

          readinessProbe:
            httpGet:
              path: /health
              port: 5000
            initialDelaySeconds: 5
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 3

          livenessProbe:
            httpGet:
              path: /health
              port: 5000
            initialDelaySeconds: 15
            periodSeconds: 20
            timeoutSeconds: 3
            failureThreshold: 3
```

Update the image automatically:

```bash
sed -i.bak \
  "s|AWS_ACCOUNT_ID|$AWS_ACCOUNT_ID|g" \
  kubernetes/deployment.yaml
```

On Linux:

```bash
sed -i \
  "s|AWS_ACCOUNT_ID|$AWS_ACCOUNT_ID|g" \
  kubernetes/deployment.yaml
```

Check:

```bash
grep image kubernetes/deployment.yaml
```

## `kubernetes/service.yaml`

A Kubernetes `LoadBalancer` Service can expose the application through an AWS load balancer. AWS recommends using the AWS Load Balancer Controller for new EKS load-balancing configurations. ([AWS Documentation][4])

```yaml
apiVersion: v1
kind: Service
metadata:
  name: eks-python-service
  namespace: cloudnautic
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internet-facing
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: instance

spec:
  type: LoadBalancer

  selector:
    app: eks-python-app

  ports:
    - name: http
      protocol: TCP
      port: 80
      targetPort: 5000
```

## `kubernetes/hpa.yaml`

The Horizontal Pod Autoscaler adjusts replica counts according to observed workload metrics such as CPU or memory utilization. ([Kubernetes][5])

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: eks-python-app-hpa
  namespace: cloudnautic
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: eks-python-app

  minReplicas: 2
  maxReplicas: 6

  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 60

    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 50
          periodSeconds: 60

  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
```

---

# 9. Install Metrics Server

HPA requires resource metrics.

```bash
kubectl apply -f \
https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

Verify:

```bash
kubectl get deployment metrics-server -n kube-system
kubectl get apiservice | grep metrics
kubectl top nodes
```

---

# 10. Deploy the application

Apply the files:

```bash
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/secret.yaml
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
kubectl apply -f kubernetes/hpa.yaml
```

Or apply the complete directory:

```bash
kubectl apply -f kubernetes/
```

---

# 11. Verify deployment

Check all resources:

```bash
kubectl get all -n cloudnautic
```

Check Pods:

```bash
kubectl get pods -n cloudnautic
```

Detailed Pod information:

```bash
kubectl describe pod \
  -n cloudnautic \
  -l app=eks-python-app
```

Check Deployment:

```bash
kubectl get deployment -n cloudnautic
```

Check ReplicaSet:

```bash
kubectl get replicasets -n cloudnautic
```

Check Service:

```bash
kubectl get service -n cloudnautic
```

Watch the external load balancer address:

```bash
kubectl get service eks-python-service \
  -n cloudnautic \
  --watch
```

Expected:

```text
NAME                 TYPE           EXTERNAL-IP
eks-python-service   LoadBalancer   xxxxx.elb.amazonaws.com
```

---

# 12. Access the application

Store the load balancer DNS name:

```bash
export LOAD_BALANCER=$(kubectl get service eks-python-service \
  -n cloudnautic \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
```

Check:

```bash
echo $LOAD_BALANCER
```

Test:

```bash
curl http://$LOAD_BALANCER
```

Health endpoint:

```bash
curl http://$LOAD_BALANCER/health
```

Secret status:

```bash
curl http://$LOAD_BALANCER/secret-status
```

Call the application repeatedly:

```bash
for i in {1..10}; do
  curl -s http://$LOAD_BALANCER
  echo
done
```

The hostname should change between Pods, demonstrating load balancing.

---

# 13. Access a Pod

Get Pod names:

```bash
kubectl get pods -n cloudnautic
```

Open a shell:

```bash
kubectl exec -it \
  -n cloudnautic \
  deployment/eks-python-app \
  -- /bin/sh
```

Check environment variables:

```bash
env | grep APP
```

Check the internal port:

```bash
python -c "
import urllib.request
print(urllib.request.urlopen('http://localhost:5000/health').read().decode())
"
```

Exit:

```bash
exit
```

---

# 14. View application logs

```bash
kubectl logs \
  -n cloudnautic \
  deployment/eks-python-app
```

Follow logs:

```bash
kubectl logs \
  -n cloudnautic \
  deployment/eks-python-app \
  --follow
```

Logs from all matching Pods:

```bash
kubectl logs \
  -n cloudnautic \
  -l app=eks-python-app \
  --prefix
```

---

# 15. Scale the application manually

```bash
kubectl scale deployment eks-python-app \
  --replicas=4 \
  -n cloudnautic
```

Verify:

```bash
kubectl get pods -n cloudnautic
```

Return to two replicas:

```bash
kubectl scale deployment eks-python-app \
  --replicas=2 \
  -n cloudnautic
```

---

# 16. Test self-healing

Delete one Pod:

```bash
kubectl get pods -n cloudnautic
```

```bash
kubectl delete pod \
  -n cloudnautic \
  <pod-name>
```

Immediately check again:

```bash
kubectl get pods -n cloudnautic --watch
```

The Deployment creates a replacement Pod because it maintains the declared replica count.

---

# 17. Test a rolling update

Change the application message:

```python
"message": "Version 2 successfully deployed on Amazon EKS"
```

Build the new image:

```bash
docker build -t eks-python-app:v2 .
```

Tag it:

```bash
docker tag eks-python-app:v2 \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:v2
```

Push it:

```bash
docker push \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:v2
```

Update the Deployment:

```bash
kubectl set image deployment/eks-python-app \
  eks-python-app=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:v2 \
  -n cloudnautic
```

Watch the rollout:

```bash
kubectl rollout status \
  deployment/eks-python-app \
  -n cloudnautic
```

Check the rollout history:

```bash
kubectl rollout history \
  deployment/eks-python-app \
  -n cloudnautic
```

Test:

```bash
curl http://$LOAD_BALANCER
```

---

# 18. Roll back the deployment

```bash
kubectl rollout undo \
  deployment/eks-python-app \
  -n cloudnautic
```

Check:

```bash
kubectl rollout status \
  deployment/eks-python-app \
  -n cloudnautic
```

---

# 19. Test autoscaling

Check HPA:

```bash
kubectl get hpa -n cloudnautic
```

Generate traffic:

```bash
kubectl run load-generator \
  --image=busybox:1.36 \
  --restart=Never \
  -n cloudnautic \
  -- /bin/sh -c \
  "while true; do wget -q -O- http://eks-python-service; done"
```

Watch scaling:

```bash
kubectl get hpa -n cloudnautic --watch
```

In another terminal:

```bash
kubectl get pods -n cloudnautic --watch
```

Stop the test:

```bash
kubectl delete pod load-generator -n cloudnautic
```

---

# 20. Troubleshooting commands

## Pods not starting

```bash
kubectl get pods -n cloudnautic
kubectl describe pod <pod-name> -n cloudnautic
kubectl logs <pod-name> -n cloudnautic
```

## `ImagePullBackOff`

Check the image name:

```bash
kubectl get deployment eks-python-app \
  -n cloudnautic \
  -o jsonpath='{.spec.template.spec.containers[0].image}'
```

Check the ECR image:

```bash
aws ecr describe-images \
  --repository-name eks-python-app \
  --region us-east-1
```

## Service has no external address

```bash
kubectl describe service eks-python-service \
  -n cloudnautic
```

Check recent events:

```bash
kubectl get events \
  -n cloudnautic \
  --sort-by=.metadata.creationTimestamp
```

## Application not responding

Use port forwarding:

```bash
kubectl port-forward \
  service/eks-python-service \
  8080:80 \
  -n cloudnautic
```

Then open:

```text
http://localhost:8080
```

## HPA shows unknown metrics

```bash
kubectl top nodes
kubectl top pods -n cloudnautic
kubectl get deployment metrics-server -n kube-system
kubectl logs deployment/metrics-server -n kube-system
```

---

# 21. Cleanup

Delete the Kubernetes application first so AWS can remove the provisioned load balancer:

```bash
kubectl delete -f kubernetes/
```

Verify that the Service is gone:

```bash
kubectl get services -n cloudnautic
```

Delete the EKS cluster:

```bash
eksctl delete cluster \
  --name $CLUSTER_NAME \
  --region $AWS_REGION
```

Delete the ECR repository:

```bash
aws ecr delete-repository \
  --repository-name $ECR_REPOSITORY \
  --region $AWS_REGION \
  --force
```

Verify:

```bash
aws eks list-clusters --region $AWS_REGION
aws ecr describe-repositories --region $AWS_REGION
```

---

# 22. Skills covered

```text
Docker image creation
Amazon ECR image storage
Amazon EKS cluster creation
Kubernetes Namespace
ConfigMap and Secret
Deployment and ReplicaSet
Resource requests and limits
Liveness and readiness probes
LoadBalancer Service
AWS Network Load Balancer
Application scaling
Horizontal Pod Autoscaler
Rolling updates
Rollback
Self-healing
Logs and troubleshooting
AWS resource cleanup
```

This provides a complete beginner-to-intermediate AWS Kubernetes application deployment project suitable for classroom practice, GitHub documentation, and interview demonstrations.

[1]: https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html?utm_source=chatgpt.com "What is Amazon EKS? - Amazon EKS"
[2]: https://docs.aws.amazon.com/eks/latest/userguide/getting-started.html?utm_source=chatgpt.com "Get started with Amazon EKS"
[3]: https://kubernetes.io/docs/concepts/configuration/secret/?utm_source=chatgpt.com "Secrets"
[4]: https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html?utm_source=chatgpt.com "Route internet traffic with AWS Load Balancer Controller"
[5]: https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/?utm_source=chatgpt.com "Horizontal Pod Autoscaling"
