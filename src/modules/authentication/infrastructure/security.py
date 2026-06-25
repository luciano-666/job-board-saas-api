import structlog
import uuid
import json
import hashlib
import hmac
from datetime import datetime, UTC

from jwcrypto import jwk, jwt
from jwcrypto.common import JWException
from jwcrypto.jwe import InvalidJWEData
from jwcrypto.jws import InvalidJWSSignature, InvalidJWSObject
from jwcrypto.jwt import (
    JWTExpired,
    JWTNotYetValid,
    JWTMissingClaim,
    JWTInvalidClaimValue,
    JWTInvalidClaimFormat,
)

from src.modules.authentication.domain.entities import (
    Session,
    AccessToken,
    RefreshToken,
)
from src.modules.authentication.presentation.exceptions import (
    AuthenticationTokenExpiredException,
    AuthenticationTokenNotYetValidException,
    AuthenticationTokenException,
    AuthenticationTokenMalformedError,
    AuthenticationException,
    HashingException,
    RefreshTokenExpiredException,
    RefreshTokenNotYetValidException,
    RefreshTokenException,
    RefreshTokenMalformedError,
    StandardException,
)
from src.modules.authentication.domain.value_objects import Claims, RefreshClaims
from src.modules.shared.application.enums import Role
from src.modules.user.domain.entities import User
from src.core.config import settings

logger = structlog.get_logger(__name__)


# JWT TOKEN (JWS + JWE)
async def _read_pem(path: str) -> bytes:
    try:
        with open(path, "rb") as f:
            return f.read()
    except StandardException:
        raise
    except Exception as e:
        logger.error("An error occurred during pem file reading.", exc_info=e)
        raise AuthenticationException()


async def load_signing_private_key() -> jwk.JWK:
    try:
        password = settings.JWT_SIGNING_KEY_PASSWORD.encode("utf-8")

        return jwk.JWK.from_pem(
            await _read_pem(settings.JWT_SIGNING_PRIVATE_KEY_PATH), password=password
        )
    except StandardException:
        raise
    except Exception as e:
        logger.error("An error occurred during private key loading.", exc_info=e)
        raise AuthenticationException()


async def load_signing_public_key() -> jwk.JWK:
    try:
        return jwk.JWK.from_pem(await _read_pem(settings.JWT_SIGNING_PUBLIC_KEY_PATH))
    except StandardException:
        raise
    except Exception as e:
        logger.error("An error occurred during public key loading.", exc_info=e)
        raise AuthenticationException()


async def load_encryption_private_key() -> jwk.JWK:
    try:
        password = settings.JWT_ENCRYPTION_KEY_PASSWORD.encode("utf-8")

        return jwk.JWK.from_pem(
            await _read_pem(settings.JWT_ENCRYPTION_PRIVATE_KEY_PATH), password=password
        )
    except StandardException:
        raise
    except Exception as e:
        logger.error("An error occurred during private key loading.", exc_info=e)
        raise AuthenticationException()


async def load_encryption_public_key() -> jwk.JWK:
    try:
        return jwk.JWK.from_pem(
            await _read_pem(settings.JWT_ENCRYPTION_PUBLIC_KEY_PATH)
        )
    except StandardException:
        raise
    except Exception as e:
        logger.error("An error occurred during public key loading.", exc_info=e)
        raise AuthenticationException()


async def generate_tokens(session: Session) -> Session:
    try:
        # access token
        session.refresh_token.access_token.set_claims(
            iss=settings.JWT_ISSUER,
            sub=session.user.id,
            aud=settings.JWT_AUDIENCE,
            jti=uuid.uuid4(),
            grant_id=str(session.user.email),
            scope=str(session.user.role.value),
        )

        access_claims = session.refresh_token.access_token.claims
        if access_claims is None:
            raise ValueError(
                "Access token claims must be set before generating the access JWT."
            )

        inner = jwt.JWT(
            header={
                "alg": "RS256",
                "typ": "access+jwt",
            },
            claims=access_claims.to_dict(),
        )

        inner.make_signed_token(await load_signing_private_key())
        signed_jwt = inner.serialize()

        outer = jwt.JWT(
            header={
                "alg": "RSA-OAEP-256",
                "enc": "A256GCM",
                "cty": "JWT",
            },
            claims=signed_jwt,
        )

        outer.make_encrypted_token(await load_encryption_public_key())
        session.refresh_token.access_token.token = outer.serialize()

        # refresh token
        session.refresh_token.set_claims(
            iss=settings.JWT_ISSUER,
            sub=session.user.id,
            aud=settings.JWT_AUDIENCE,
            jti=uuid.uuid4(),
            client_id=str(settings.APPLICATION_URL),
            grant_id=str(session.user.email),
            scope=str(session.user.role.value),
        )

        refresh_claims = session.refresh_token.refresh_claims
        if refresh_claims is None:
            raise ValueError(
                "Refresh token claims must be set before generating the refresh JWT."
            )

        inner = jwt.JWT(
            header={
                "alg": "RS256",
                "typ": "refresh+jwt",
            },
            claims=refresh_claims.to_dict(),
        )

        inner.make_signed_token(await load_signing_private_key())
        signed_jwt = inner.serialize()

        outer = jwt.JWT(
            header={
                "alg": "RSA-OAEP-256",
                "enc": "A256GCM",
                "cty": "JWT",
            },
            claims=signed_jwt,
        )

        outer.make_encrypted_token(await load_encryption_public_key())
        session.refresh_token.token = outer.serialize()

        return session
    except StandardException:
        raise
    except Exception as e:
        logger.error("An error occurred during token generation.", exc_info=e)
        raise AuthenticationException()


def from_access_claims(claims: dict) -> Session:
    """Build a minimal Session shell from decoded access token claims.

    Only the fields hash_tokens() and the lookup builders need are populated.
    ip_address/user_agent/device are placeholders, overwritten by the caller
    with request data before any repository call.
    """
    access_claims = Claims.from_dict(claims)
    role = Role(access_claims.scope)
    user = User(id=access_claims.sub, email=access_claims.grant_id, role=role)
    access_token = AccessToken(
        expires_at=datetime.fromtimestamp(access_claims.exp, tz=UTC),
        permission=role,
        claims=access_claims,
    )
    refresh_token = RefreshToken(
        expires_at=access_token.expires_at,
        access_token=access_token,
    )
    return Session(
        id=uuid.uuid4(),
        user=user,
        refresh_token=refresh_token,
        ip_address="",
        user_agent="",
        device="",
        created_at=datetime.fromtimestamp(access_claims.iat, tz=UTC),
        last_updated_at=datetime.fromtimestamp(access_claims.iat, tz=UTC),
    )


def from_refresh_claims(claims: dict) -> Session:
    """Build a minimal Session shell from decoded refresh token claims."""
    refresh_claims = RefreshClaims.from_dict(claims)
    role = Role(refresh_claims.scope)
    user = User(id=refresh_claims.sub, email=refresh_claims.grant_id, role=role)
    access_token = AccessToken(
        expires_at=datetime.fromtimestamp(refresh_claims.exp, tz=UTC),
        permission=role,
    )
    refresh_token = RefreshToken(
        expires_at=datetime.fromtimestamp(refresh_claims.exp, tz=UTC),
        access_token=access_token,
        refresh_claims=refresh_claims,
    )
    return Session(
        id=uuid.uuid4(),
        user=user,
        refresh_token=refresh_token,
        ip_address="",
        user_agent="",
        device="",
        created_at=datetime.fromtimestamp(refresh_claims.iat, tz=UTC),
        last_updated_at=datetime.fromtimestamp(refresh_claims.iat, tz=UTC),
    )


async def decode_nested_access_token(token: str) -> Session:
    try:
        outer = jwt.JWT(
            jwt=token,
            key=await load_encryption_private_key(),
            expected_type="JWE",
            algs=["RSA-OAEP-256", "A256GCM"],
        )
        inner_raw = outer.claims

        inner = jwt.JWT(
            jwt=inner_raw,
            key=await load_signing_public_key(),
            expected_type="JWS",
            algs=["RS256"],
            check_claims={
                "iss": settings.JWT_ISSUER,
                "sub": None,
                "aud": settings.JWT_AUDIENCE,
                "jti": None,
                "grant_id": None,
                "scope": None,
                "iat": None,
                "exp": None,
                "nbf": None,
            },
        )

        session = from_access_claims(json.loads(inner.claims))

        logger.debug(
            f"Access token decoded successfully for user: {session.user.email} with role: {session.user.role.value}"
        )
        return session
    except JWTExpired:
        logger.warning(
            "Attempt to use an expired token. Raising token expired exception."
        )
        raise AuthenticationTokenExpiredException()
    except JWTNotYetValid:
        logger.warning(
            "Attempt to use a token that has not yet been valid. Raising token not yet valid exception."
        )
        raise AuthenticationTokenNotYetValidException()
    except JWTMissingClaim as e:
        logger.opt(exception=e).warning(
            "Attempt to use a token with missing claims. Raising authentication token exception."
        )
        raise AuthenticationTokenException()
    except JWTInvalidClaimValue as e:
        logger.opt(exception=e).warning(
            "Attempt to use a token with invalid claims. Raising authentication token exception."
        )
        raise AuthenticationTokenException()
    except JWTInvalidClaimFormat as e:
        logger.opt(exception=e).warning(
            "Attempt to use a token with invalid claim format. Raising token authentication exception."
        )
        raise AuthenticationTokenException()
    except InvalidJWSSignature as e:
        logger.opt(exception=e).warning(
            "Attempt to use a token with an invalid signature. Raising token authentication exception."
        )
        raise AuthenticationTokenException()
    except (InvalidJWEData, InvalidJWSObject) as e:
        logger.opt(exception=e).warning(
            "Attempt to use a token with an invalid format. Raising token authentication exception."
        )
        raise AuthenticationTokenException()
    except json.JSONDecodeError as e:
        logger.opt(exception=e).warning(
            "Attempt to use a token with an invalid format. Raising token authentication exception."
        )
        raise AuthenticationTokenMalformedError()
    except JWException as e:
        logger.error(
            "Attempt to use a token with an invalid format or signature. Raising token authentication exception.",
            exc_info=e,
        )
        raise AuthenticationTokenException()
    except Exception as e:
        logger.error("An error occurred during token decoding.", exc_info=e)
        raise AuthenticationTokenException()


async def decode_nested_refresh_token(token: str) -> Session:
    try:
        outer = jwt.JWT(
            jwt=token,
            key=await load_encryption_private_key(),
            expected_type="JWE",
            algs=["RSA-OAEP-256", "A256GCM"],
        )
        inner_raw = outer.claims

        inner = jwt.JWT(
            jwt=inner_raw,
            key=await load_signing_public_key(),
            expected_type="JWS",
            algs=["RS256"],
            check_claims={
                "iss": settings.JWT_ISSUER,
                "sub": None,
                "aud": settings.JWT_AUDIENCE,
                "jti": None,
                "client_id": None,
                "grant_id": None,
                "scope": None,
                "iat": None,
                "exp": None,
                "nbf": None,
            },
        )

        session = from_refresh_claims(json.loads(inner.claims))

        logger.debug(
            f"Refresh token decoded successfully for user: {session.user.email} with role: {session.user.role.value}"
        )
        return session
    except JWTExpired:
        logger.warning(
            "Attempt to use an expired refresh token. Raising refresh token expired exception."
        )
        raise RefreshTokenExpiredException()
    except JWTNotYetValid:
        logger.warning(
            "Attempt to use a refresh token that has not yet been valid. Raising refresh token not yet valid exception."
        )
        raise RefreshTokenNotYetValidException()
    except JWTMissingClaim as e:
        logger.opt(exception=e).warning(
            "Attempt to use a refresh token with missing claims. Raising authentication refresh token exception."
        )
        raise RefreshTokenException()
    except JWTInvalidClaimValue as e:
        logger.opt(exception=e).warning(
            "Attempt to use a refresh token with invalid claims. Raising authentication refresh token exception."
        )
        raise RefreshTokenException()
    except JWTInvalidClaimFormat as e:
        logger.opt(exception=e).warning(
            "Attempt to use a refresh token with invalid claim format. Raising refresh token authentication exception."
        )
        raise RefreshTokenException()
    except InvalidJWSSignature as e:
        logger.opt(exception=e).warning(
            "Attempt to use a refresh token with an invalid signature. Raising refresh token authentication exception."
        )
        raise RefreshTokenException()
    except (InvalidJWEData, InvalidJWSObject) as e:
        logger.opt(exception=e).warning(
            "Attempt to use a refresh token with an invalid format. Raising refresh token authentication exception."
        )
        raise RefreshTokenException()
    except json.JSONDecodeError as e:
        logger.opt(exception=e).warning(
            "Attempt to use a refresh token with an invalid format. Raising refresh token authentication exception."
        )
        raise RefreshTokenMalformedError()
    except JWException as e:
        logger.error(
            "Attempt to use a refresh token with an invalid format or signature. Raising refresh token authentication exception.",
            exc_info=e,
        )
        raise RefreshTokenException()
    except Exception as e:
        logger.error("An error occurred during refresh token decoding.", exc_info=e)
        raise RefreshTokenException()


# JWT HASHING
async def _token_fingerprint(material: str, namespace: str) -> str:
    try:
        key = bytes.fromhex(settings.JWT_HASH_FINGERPRINT)
        msg = f"{namespace}:{material}".encode("utf-8")

        return hmac.new(key, msg, hashlib.sha256).hexdigest()
    except StandardException:
        raise
    except Exception as e:
        logger.error("An error occurred during token hashing.", exc_info=e)
        raise HashingException()


async def hash_tokens(session: Session) -> Session:
    try:
        access_claims = session.refresh_token.access_token.claims
        session.refresh_token.access_token.hashed_jti = (
            await _token_fingerprint(str(access_claims.jti), "access-jti")
            if access_claims and access_claims.jti
            else None
        )

        refresh_claims = session.refresh_token.refresh_claims
        session.refresh_token.hashed_jti = (
            await _token_fingerprint(str(refresh_claims.jti), "refresh-jti")
            if refresh_claims and refresh_claims.jti
            else None
        )

        return session
    except StandardException:
        raise
    except Exception as e:
        logger.error("An error occurred during token hashing.", exc_info=e)
        raise HashingException()
