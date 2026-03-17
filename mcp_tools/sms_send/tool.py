"""Send an SMS message via a supported provider."""


def run(to: str, body: str, provider: str, api_key: str) -> str:
    """Send an SMS text message.

    Dispatches the message through the specified SMS provider using the
    supplied API key.

    Args:
        to: Phone number to send the message to.
        body: Message text.
        provider: SMS provider name ("twilio" or "vonage").
        api_key: API key for the chosen SMS provider.

    Returns:
        Confirmation string on success.

    Raises:
        ValueError: If provider or api_key is empty.
        NotImplementedError: Stub — full implementation pending.
    """
    if not provider:
        raise ValueError("provider is required")
    if not api_key:
        raise ValueError("api_key is required")

    raise NotImplementedError(
        "sms_send is a stub. Provide a full implementation to use this tool."
    )
