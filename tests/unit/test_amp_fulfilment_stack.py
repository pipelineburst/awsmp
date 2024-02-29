import aws_cdk as core
import aws_cdk.assertions as assertions

from amp_fulfilment.amp_fulfilment_stack import AmpFulfilmentStack

# example tests. To run these tests, uncomment this file along with the example
# resource in amp_fulfilment/amp_fulfilment_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = AmpFulfilmentStack(app, "amp-fulfilment")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
