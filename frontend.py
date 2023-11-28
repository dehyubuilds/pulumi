from pulumi import ComponentResource, ResourceOptions, Output
import pulumi_aws as aws
import pulumi_awsx as awsx
import json

class WebServiceArgs:
    def __init__(self,
                 db_host=None,
                 db_port=None,
                 db_name=None,
                 db_user=None,
                 db_password=None,
                 vpc_id=None,
                 subnet_ids=None,  # array of subnet IDs
                 security_group_ids=None):  # array of security group Ids
        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.vpc_id = vpc_id
        self.subnet_ids = subnet_ids
        self.security_group_ids = security_group_ids

class WebService(ComponentResource):
    def __init__(self,
                 name: str,
                 args: WebServiceArgs,
                 opts: ResourceOptions = None):
        super().__init__('custom:resource:Frontend', name, {}, opts)

        # Define the ECR repository
        self.repo = awsx.ecr.Repository(name)

        # Build and push the Node.js application Docker image to ECR
        self.image = awsx.ecr.Image(name,
                                    repository_url=self.repo.url,
                                    build="./app",  # Assuming your Node.js app is in the "app" directory
                                    cache_from=["build"])

        # Create an ECS cluster to run a container-based service
        self.cluster = aws.ecs.Cluster(f'{name}-ecs',
                                       opts=ResourceOptions(parent=self))

        # Create a load balancer to listen for HTTP traffic on port 80
        self.alb = aws.lb.LoadBalancer(f'{name}-alb',
                                       security_groups=args.security_group_ids,
                                       subnets=args.subnet_ids,
                                       opts=ResourceOptions(parent=self))

        # Create a target group for routing traffic to ECS tasks
        atg = aws.lb.TargetGroup(f'{name}-app-tg',
                                 port=80,
                                 protocol='HTTP',
                                 target_type='ip',
                                 vpc_id=args.vpc_id,
                                 health_check=aws.lb.TargetGroupHealthCheckArgs(
                                     healthy_threshold=2,
                                     interval=5,
                                     timeout=4,
                                     protocol='HTTP',
                                     matcher='200-399'),
                                 opts=ResourceOptions(parent=self))

        # Create an ALB listener
        wl = aws.lb.Listener(f'{name}-listener',
                             load_balancer_arn=self.alb.arn,
                             port=80,
                             default_actions=[aws.lb.ListenerDefaultActionArgs(
                                 type='forward',
                                 target_group_arn=atg.arn)],
                             opts=ResourceOptions(parent=self))

        # Create an IAM role that can be used by our service's task
        role = aws.iam.Role(f'{name}-task-role',
                            assume_role_policy=json.dumps({
                                'Version': '2008-10-17',
                                'Statement': [{
                                    'Sid': '',
                                    'Effect': 'Allow',
                                    'Principal': {
                                        'Service': 'ecs-tasks.amazonaws.com'
                                    },
                                    'Action': 'sts:AssumeRole',
                                }]
                            }),
                            opts=ResourceOptions(parent=self))

        # Attach the Amazon ECS task execution role policy to the IAM role
        rpa = aws.iam.RolePolicyAttachment(f'{name}-task-policy',
                                           role=role.name,
                                           policy_arn='arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy',
                                           opts=ResourceOptions(parent=self))

        # Spin up a load balanced service running our container image
        task_name = f'{name}-app-task'
        container_name = f'{name}-app-container'
        self.task_definition = Output.all(args.db_host, args.db_port, args.db_name, args.db_user,
                                          args.db_password).apply(
            lambda args:
            aws.ecs.TaskDefinition(task_name,
                                   family='fargate-task-definition',
                                   cpu='256',
                                   memory='512',
                                   network_mode='awsvpc',
                                   requires_compatibilities=['FARGATE'],
                                   execution_role_arn=role.arn,
                                   container_definitions=json.dumps([{
                                       'name': container_name,
                                       'image': self.image.image_uri,
                                       'logConfiguration': {
                                           "logDriver": "awslogs",
                                           "options": {
                                               "awslogs-group": "/ecs/fargate-task-definition",
                                               "awslogs-region": "us-east-1",
                                               "awslogs-stream-prefix": "ecs"
                                           }
                                       },
                                       'portMappings': [{
                                           'containerPort': 3000,
                                           'hostPort': 3000,
                                           'protocol': 'tcp'
                                       }],
                                       'environment': [
                                           {
                                               'name': 'DB_HOST',
                                               'value': f'{args[0]}:{args[1]}'
                                           },
                                           {
                                               'name': 'DB_NAME',
                                               'value': f'{args[2]}'
                                           },
                                           {
                                               'name': 'DB_USER',
                                               'value': f'{args[3]}'
                                           },
                                           {
                                               'name': 'DB_PASSWORD',
                                               'value': f'{args[4]}'
                                           },
                                           {
                                               'name': 'DB_PORT',
                                               'value': 5432
                                           },
                                           {
                                               'name': 'GOOGLE_MAP_API_KEY',
                                               'value': 'AIzaSyCw-gQ57DGLV7pmHoGgwsW1Yo43JTN_NfM'
                                           },
                                           {
                                               'name': 'NODE_ENV',  
                                               'value': 'development'
                                           }
                                       ]
                                   }]),
                                   opts=ResourceOptions(parent=self)
                                   )
        )

        # Create the ECS service
        self.service = aws.ecs.Service(f'{name}-app-svc',
                                       cluster=self.cluster.
