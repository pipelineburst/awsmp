from aws_cdk import (
    Duration,
    Stack,
    RemovalPolicy,
    aws_s3_deployment as s3deploy,
    aws_certificatemanager as acm,
    aws_sqs as sqs,
    aws_iam as iam,
    aws_kms as kms,
    aws_ecr as ecr,
    aws_s3 as s3,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_cloudfront as cloudfront,
    aws_dynamodb as dynamodb,
    aws_lambda  as lambda_,
)
from constructs import Construct

class AmpFulfillmentStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, cert, edge_func, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ### Create S3 bucket for AMP fulfillment website
        website_bucket = s3.Bucket(self, "AmpFulfillementSite",
            bucket_name="ainsights.acs.saas.mycom-osi.com",
            website_index_document="index.html",
            auto_delete_objects=True,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            intelligent_tiering_configurations=[
                s3.IntelligentTieringConfiguration(
                name="my_s3_tiering",
                archive_access_tier_time=Duration.days(90),
                deep_archive_access_tier_time=Duration.days(180),
                prefix="prefix",
                tags=[s3.Tag(
                    key="owner",
                    value="acs"
                )]
             )],
            lifecycle_rules=[
                s3.LifecycleRule(
                    noncurrent_version_expiration=Duration.days(7)
                )
            ],
        )

        ### Upload the fulfilment website to the S3 website bucket
        s3deploy.BucketDeployment(self, "DeployWebsite",
            sources=[s3deploy.Source.asset("./assets")],
            destination_bucket=website_bucket,
            destination_key_prefix="/"
        )

        ### We need cloudfront for AMP the fulfilment website as S3 hosting does not support https natively
        # Creating a cloudfront OAI, so the bucket website can only be accessed from the DF distribution 
        cf_origin_access_identity = cloudfront.OriginAccessIdentity(self, "AmpFulfillementSiteOAI",
            comment="AMP Fulfillement Site OAI"
        )        
        
        cf_distribution = cloudfront.CloudFrontWebDistribution(self, "AmpFulfillementSiteDistribution",
            origin_configs=[
                cloudfront.SourceConfiguration(
                    s3_origin_source=cloudfront.S3OriginConfig(
                        s3_bucket_source=website_bucket,
                        origin_access_identity=cf_origin_access_identity
                    ),
                    behaviors=[
                        cloudfront.Behavior(
                            is_default_behavior=True
                        )
                    ]
                )
            ],
            error_configurations=[
                {
                    "errorCode": 403,
                    "responseCode": 200,
                    "responsePagePath": "/index.html"
                }
            ],
            viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
            viewer_certificate=cloudfront.ViewerCertificate.from_acm_certificate(
                certificate=cert, # passing in the acm cert object created in stack 1
                aliases=["ainsights.acs.saas.mycom-osi.com"],
                security_policy=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
            )
        )

        ################## lambda work ##################
        # creating the lambda function
        lambda_role = iam.Role(
            self,
            "lambda_role",
            assumed_by=iam.CompositePrincipal(iam.ServicePrincipal("lambda.amazonaws.com"), iam.ServicePrincipal("edgelambda.amazonaws.com") ),
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")],
        )
        # adding permissions to the lambda execution role
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:DescribeTable",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                ],
                resources=["arn:aws:dynamodb:*:*:table/*"],
            )
        )
        # adding permissions to the lambda execution role
        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        # creating the lambda function
        new_lambda_function = lambda_.Function(
            self,
            "new_awsmp_lambda_function",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="lambda.lambda_handler",
            code=lambda_.Code.from_asset("lambda"),
            role=lambda_role,
            timeout=Duration.seconds(5),
        )

        # note: for now, manually added the lambda arn version to the cf default behaviour in the console
        # note: for now, manually adding the distribution ID to the route53 hosted zone in digital-dev
        
        ### Now we create a dynamodb table that can store our awsmp details
        dynamodb_table = dynamodb.Table(self, "AmpFulfilmentTable",
                                        table_name="awsmp",
                                        partition_key=dynamodb.Attribute(name="customer-id", type=dynamodb.AttributeType.STRING),
                                        billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
                                        removal_policy=RemovalPolicy.DESTROY,
                                        )
        
        