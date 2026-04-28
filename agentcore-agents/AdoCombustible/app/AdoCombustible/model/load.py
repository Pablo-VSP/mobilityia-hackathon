from strands.models.bedrock import BedrockModel


def load_model() -> BedrockModel:
    """Amazon Nova Pro via US cross-region inference profile."""
    return BedrockModel(
        model_id="us.amazon.nova-pro-v1:0",
        region_name="us-east-2",
    )
