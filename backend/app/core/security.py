import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from dataclasses import dataclass
from app.core.config import get_settings


class SecurityError(Exception):
    """Custom security exception."""
    pass


@dataclass
class UserClaims:
    """JWT user claims."""
    user_id: str
    tenant_id: str
    email: str
    role: str
    exp: int
    iat: int
    aud: str
    iss: str


def load_jwt_public_key() -> str:
    """Load JWT public key from file."""
    settings = get_settings()
    try:
        with open(settings.JWT_PUBLIC_KEY_PATH, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""  # allow HS256 fallback in dev


def decode_jwt_token(token: str) -> UserClaims:
    """Decode and validate JWT token with fallback support."""
    s = get_settings()
    try:
        # First, check which algorithm the token uses
        header = jwt.get_unverified_header(token)
        token_alg = header.get("alg")
        
        if token_alg == "RS256":
            # Use RS256 with public key
            pub = load_jwt_public_key()
            if not pub:
                raise InvalidTokenError("No public key available for RS256 token")
            payload = jwt.decode(
                token, pub, algorithms=["RS256"],
                audience=s.JWT_AUDIENCE, issuer=s.JWT_ISSUER
            )
        elif token_alg == "HS256":
            # Use HS256 with secret key
            payload = jwt.decode(
                token, s.SECRET_KEY, algorithms=["HS256"],
                audience=s.JWT_AUDIENCE, issuer=s.JWT_ISSUER
            )
        else:
            raise InvalidTokenError(f"Unsupported algorithm: {token_alg}")

        required = ["user_id", "tenant_id", "email", "role", "exp", "iat", "aud", "iss"]
        for k in required:
            if k not in payload:
                raise SecurityError(f"Missing claim: {k}")
        return UserClaims(**payload)

    except ExpiredSignatureError:
        raise SecurityError("Token expired")
    except InvalidTokenError as e:
        raise SecurityError(f"Invalid token: {e}")
    except Exception as e:
        raise SecurityError(f"Token validation failed: {e}")


def create_dev_jwt_token(user_id: str, tenant_id: str, email: str, role: str = "user") -> str:
    """Create a development JWT token for testing."""
    import time
    s = get_settings()
    payload = {
        "user_id": user_id, "tenant_id": tenant_id, "email": email, "role": role,
        "exp": int(time.time()) + 86400, "iat": int(time.time()),  # 24 hours
        "aud": s.JWT_AUDIENCE, "iss": s.JWT_ISSUER
    }
    # Try RS256 if private key exists; else HS256
    try:
        priv_path = s.JWT_PUBLIC_KEY_PATH.replace(".pub", ".key")
        with open(priv_path, "r") as f:
            priv = f.read()
        return jwt.encode(payload, priv, algorithm="RS256")
    except Exception:
        return jwt.encode(payload, s.SECRET_KEY, algorithm="HS256")


def extract_token_from_header(authorization: str | None) -> str | None:
    """Extract Bearer token from Authorization header."""
    if not authorization:
        return None
    if authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return None


def check_meeting_access(user_claims: UserClaims, meeting_id: str) -> bool:
    """Check if user has access to meeting (development placeholder)."""
    # For development, allow all access with valid tokens
    # In production, implement proper access control
    return True


# Mock function for development
def get_current_user_claims(authorization: str) -> UserClaims:
    """Get current user claims from authorization header."""
    token = extract_token_from_header(authorization)
    if not token:
        raise SecurityError("No token provided")
    return decode_jwt_token(token)