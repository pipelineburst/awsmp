from aws_cdk import (
    Duration,
    Stack,
    RemovalPolicy,
    aws_certificatemanager as acm,
    aws_iam as iam,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_cloudfront as cloudfront,
    aws_lambda  as lambda_,
)
from constructs import Construct

class AmpEdgeStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        ### defining the acm cert in us-east-1 for cloudfront
        acm_cert = acm.Certificate(self, "AmpFulfillementSiteCertificate",
                                   domain_name="ainsights.acs.saas.mycom-osi.com",
                                   validation=acm.CertificateValidation.from_dns(),
                                   #subject_alternative_names=["*.ainsights.acs.saas.mycom-osi.com"],
                                   )

        self.acm_certificate=acm_cert # Reference for a downstream Stack        

        ## defining the lambda function that will then be associated to a cf distribtion
        # creating the lambda execution role 
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

        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        # creating the lambda function
        lambda_function = lambda_.Function(
            self,
            "awsmp_lambda_function",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="lambda.lambda_handler",
            code=lambda_.Code.from_asset("lambda"),
            role=lambda_role,
            timeout=Duration.seconds(5),
        )
        
        self.edge_function=lambda_function # Reference for a downstream Stack 
