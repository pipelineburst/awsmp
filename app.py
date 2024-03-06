#!/usr/bin/env python3
import os
import aws_cdk as cdk
from stacks.amp_fulfillment_stack import AmpFulfillmentStack
from stacks.amp_edge_stack import AmpEdgeStack

app = cdk.App()

account_id = "069127586842"
region_1 = "eu-west-1"
region_2 = "us-east-1"

stack1 = AmpEdgeStack(app, "AmpEdgeStack",
            description="Provision backend resources to process reqeusts and hit awsmp api's", 
            termination_protection=False, 
            cross_region_references=True,
            tags={"marketplace":"ainsights"}, 
            env=cdk.Environment(region=region_2, account=account_id),
        )

stack2 = AmpFulfillmentStack(app, "AmpFulfillmentStack",
            description="Provision fulfillment page for awsmp integration", 
            termination_protection=False, 
            cross_region_references=True,
            tags={"marketplace":"ainsights"}, 
            env=cdk.Environment(region=region_2, account=account_id),
            cert=stack1.acm_certificate,
        )

cdk.Tags.of(stack1).add(key="project",value="awsmp")
cdk.Tags.of(stack2).add(key="project",value="awsmp")

stack2.add_dependency(stack1)

app.synth()
