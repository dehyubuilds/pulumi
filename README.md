# Twilly Site in AWS Fargate with RDS DB Backend

This serves the Twilly site in AWS ECS Fargate using an RDS Postgresql Backend.

It leverages the following Pulumi concepts/constructs:

- [Component Resources](https://www.pulumi.com/docs/intro/concepts/programming-model/#components): Allows one to create custom resources that encapsulate one's best practices.

- [Other Providers](https://www.pulumi.com/docs/reference/pkg/): Beyond the providers for the various clouds and Kubernetes, etc, Pulumi allows one to create and manage non-cloud resources. 

This app uses the following AWS products (and related Pulumi providers):

- [Amazon VPC](https://aws.amazon.com/vpc): Used to set up a new virtual network in which the system is deployed.
- [Amazon RDS](https://aws.amazon.com/rds): A managed DB service used to provide the Postgresql backend for Twilly application.
- [Amazon ECS Fargate](https://aws.amazon.com/fargate): A container service used to run the Twilly frontend.

## Getting Started

There are no required configuration parameters for this project since the code will use defaults or generate values as needed - see the beginning of `__main__.py` to see the defaults.
However, you can override these defaults by using `pulumi config` to set the following values (e.g. `pulumi config set service_name my-wp-demo`).

- `service_name` - This is used as a prefix for resources created by the Pulumi program.
- `db_name` - The name of the Postgresql DB created in RDS.
- `db_user` - The user created with access to the Postgresql DB.
- `db_password` - The password for the DB user. Be sure to use `--secret` if creating this config value (e.g. `pulumi config set db_password --secret`).

## Deploying and running the program

Note: some values in this example will be different from run to run.

1. Create a new stack:

   ```bash
   $ pulumi stack init Twilly-dev
   ```

1. Set the AWS region:

   ```bash
   $ pulumi config set aws:region us-east-1
   ```

1. Run `pulumi up` to preview and deploy changes. After the preview is shown you will be
   prompted if you want to continue or not. Note: If you set the `db_password` in the configuration as described above, you will not see the `RandomPassword` resource below.

   ```bash
   $ pulumi up
    +   pulumi:pulumi:Stack                  Twilly-dev          create
    +   ├─ custom:resource:VPC               kk-net                    create
    +   │  ├─ aws:ec2:Vpc                    kk-net-vpc                create
    +   pulumi:pulumi:Stack                  Twilly-dev          create
    +   pulumi:pulumi:Stack                  Twilly-dev          create
    +   │  ├─ aws:ec2:Subnet                 kk-net-subnet-us-east-1a  create
    +   │  ├─ aws:ec2:Subnet                 kk-net-subnet-us-east-1b  create
    +   │  ├─ aws:ec2:SecurityGroup          kk-net-rds-sg             create
    +   │  ├─ aws:ec2:SecurityGroup          kk-net-fe-sg              create
    +   │  ├─ aws:ec2:RouteTableAssociation  vpc-route-table-assoc-us-east-1a  create
    +   │  └─ aws:ec2:RouteTableAssociation  vpc-route-table-assoc-us-east-1b  create
    +   ├─ random:index:RandomPassword       db_password                       create
    +   ├─ custom:resource:Backend           kk-be                     create
    +   │  ├─ aws:rds:SubnetGroup            kk-be-sng                 create
    +   │  └─ aws:rds:Instance               kk-be-rds                 create
    +   └─ custom:resource:Frontend          kk-fe                     create
    +      ├─ aws:ecs:Cluster                kk-fe-ecs                 create
    +      ├─ aws:iam:Role                   kk-fe-task-role           create
    +      ├─ aws:lb:TargetGroup             kk-fe-app-tg              create
    +      ├─ aws:iam:RolePolicyAttachment   kk-fe-task-policy         create
    +      ├─ aws:lb:LoadBalancer            kk-fe-alb                 create
    +      ├─ aws:lb:Listener                kk-fe-listener            create
    +      ├─ aws:ecr:Repository             kk-repo                   create
    +      ├─ aws:ecr:LifecyclePolicy        kk-repo                   create
    +      ├─ awsx:ecr:Image                 Twilly              create
    +      └─ aws:ecs:Service                kk-fe-app-svc             create

   ```

1. The program outputs the following values:

- `DB Endpoint`: This is the RDS DB endpoint. By default, the DB is deployed to disallow public access. This can be overriden in the resource declaration for the backend.
- `DB Password`: This is managed as a secret. To see the value, you can use `pulumi stack output --show-secrets`
- `DB User Name`: The user name for access the DB.
- `ECS Cluster Name`: The name of the ECS cluster created by the stack.
- `Web Service URL`: This is a link to the load balancer fronting the Twilly container. Note: It may take a few minutes for AWS to complete deploying the service and so you may see a 503 error initially.

1. To clean up resources, run `pulumi destroy` and answer the confirmation question at the prompt.

## Troubleshooting

### 503 Error for the Web Service

AWS can take a few minutes to complete deploying the Twilly container and connect the load balancer to the service. So you may see a 503 error for a few minutes right after launching the stack. You can see the status of the service by looking at the cluster in AWS.

## Deployment Speed

Since the stack creates an RDS instance, ECS cluster, load balancer, ECS service, as well as other elements, the stack can take about 4-5 minutes to launch and become ready.
