```
// repo: https://github.com/atulkamble/aws-eks-app

- app.py
- requirements.txt 
/templates/index.html

stage: dev 
>> code >> git/github 
tech stack - python 

pip install -r requirements.txt 
python app.py 
http://localhost:5000 

git branch dev 
git checkout dev 
git push origin dev 

// stage 2 - create cluster 

eksctl create cluster --name mycluster --region us-east-1 --nodegroup-name mynodes --node-type t3.medium --nodes 2 --nodes-min 2 --nodes-max 2 --managed

aws eks update-kubeconfig --name mycluster --region us-east-1

kubectl get nodes 


// stage 3 - Dockerfile

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
ENTRYPOINT ["python", "app.py"]

// stage 4 - test dockerfile 

docker images 
docker buildx build  -t pythonapp --load .
docker images
docker run -d -p 5000:5000 pythonapp:latest

// stage ECR 

aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 535002879962.dkr.ecr.us-east-1.amazonaws.com

docker buildx build --platform linux/amd64,linux/arm64 -t cloudnautic/pythonapp:latest --load .

docker tag cloudnautic/pythonapp:latest 535002879962.dkr.ecr.us-east-1.amazonaws.com/cloudnautic/pythonapp:latest

 docker push 535002879962.dkr.ecr.us-east-1.amazonaws.com/cloudnautic/pythonapp:latest

// k8s phase 

kubectl get nodes
kubectl apply -f ./k8s 

kubectl get deployment 
kubectl get pods 
kubectl get svc 

http://ac914ab5251394da783d865002746fe4-1544151355.us-east-1.elb.amazonaws.com/

eksctl delete cluster --name mycluster --region us-east-1





```
