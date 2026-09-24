from django.core import signing

# No login required to unsubscribe (#289), so the token itself is the credential:
# a signed, tamper-proof pointer to the user, with no expiry (unsubscribe links in
# old emails should keep working).
NEWSLETTER_UNSUBSCRIBE_SALT = "users.newsletter-unsubscribe"


def make_unsubscribe_token(user_id: int) -> str:
    return signing.dumps({"user_id": user_id}, salt=NEWSLETTER_UNSUBSCRIBE_SALT)


def verify_unsubscribe_token(token: str) -> int:
    """Raises django.core.signing.BadSignature if the token is invalid or tampered."""
    return signing.loads(token, salt=NEWSLETTER_UNSUBSCRIBE_SALT)["user_id"]
