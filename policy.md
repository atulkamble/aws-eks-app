For **EKS worker nodes to pull Docker images from Amazon ECR**, attach ECR read permissions to the **IAM role used by your EKS node group**.

A simple AWS-managed policy is:

```text
AmazonEC2ContainerRegistryReadOnly
```

Attach it to the EKS worker node IAM role.

For example:

```bash
aws iam attach-role-policy \
  --role-name <EKS-NODE-ROLE-NAME> \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
```

The equivalent minimum custom policy is roughly:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    }
  ]
}
```

Then your Kubernetes Deployment can directly use the ECR image:

```yaml
containers:
  - name: pythonapp
    image: <AWS_ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com/pythonapp:latest
```

For a standard **EKS managed node group**, you normally do **not need `imagePullSecrets`** for ECR. The kubelet uses the worker node IAM credentials to authenticate with ECR.
