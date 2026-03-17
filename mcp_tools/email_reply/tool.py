"""Reply to an email message via SMTP/IMAP."""


def run(
    id: str,
    body: str,
    smtp_host: str,
    smtp_user: str,
    smtp_pass: str,
    imap_host: str,
) -> str:
    """Reply to an email message.

    Connects to the mail server using the provided SMTP and IMAP credentials,
    fetches the original message, and sends a reply.

    Args:
        id: Message ID to reply to.
        body: Reply body text.
        smtp_host: SMTP server hostname.
        smtp_user: SMTP authentication username.
        smtp_pass: SMTP authentication password.
        imap_host: IMAP server hostname for fetching the original message.

    Returns:
        Confirmation string on success.

    Raises:
        ValueError: If any credential parameter is empty.
        NotImplementedError: Stub — full implementation pending.
    """
    if not smtp_host:
        raise ValueError("smtp_host is required")
    if not smtp_user:
        raise ValueError("smtp_user is required")
    if not smtp_pass:
        raise ValueError("smtp_pass is required")
    if not imap_host:
        raise ValueError("imap_host is required")

    raise NotImplementedError(
        "email_reply is a stub. Provide a full implementation to use this tool."
    )
