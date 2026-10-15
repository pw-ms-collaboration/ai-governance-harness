"""Pinned JWT verification with a bounded, rate-limited JWKS cache."""

import json
import logging
import threading
import time
from urllib.error import URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

import jwt

from ai_governance_harness.identity.tokens import InvalidIdentityToken

logger = logging.getLogger(__name__)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class JwtVerifier:
    """Verify RS256 tokens using only configured keys, never token-supplied URLs."""

    def __init__(
        self,
        *,
        issuer: str,
        jwks_url: str,
        audience: str,
        tenant: str,
        timeout: float = 5,
    ) -> None:
        self.issuer = issuer
        self.jwks_url = jwks_url
        self.audience = audience
        self.tenant = tenant
        self.timeout = timeout
        self._keys: dict[str, jwt.PyJWK] = {}
        self._last_fetch = float("-inf")
        self._lock = threading.Lock()

    @property
    def ready(self) -> bool:
        return bool(self._keys)

    def refresh(self) -> bool:
        """Fetch at most once per five seconds; failures clear trusted keys."""
        with self._lock:
            if time.monotonic() - self._last_fetch < 5:
                return self.ready
            self._last_fetch = time.monotonic()
            try:
                opener = build_opener(ProxyHandler({}), _NoRedirect())
                with opener.open(
                    Request(self.jwks_url), timeout=self.timeout
                ) as response:
                    data = response.read(65_537)
                if len(data) > 65_536:
                    raise ValueError("JWKS too large")
                raw_keys = json.loads(data)["keys"]
                if not isinstance(raw_keys, list) or not 1 <= len(raw_keys) <= 16:
                    raise ValueError("Invalid JWKS")
                keys: dict[str, jwt.PyJWK] = {}
                for value in raw_keys:
                    if (
                        not isinstance(value, dict)
                        or value.get("kty") != "RSA"
                        or value.get("alg") != "RS256"
                        or value.get("use") != "sig"
                        or not isinstance(value.get("kid"), str)
                        or not value["kid"]
                        or value["kid"] in keys
                        or {"d", "p", "q", "dp", "dq", "qi"} & value.keys()
                    ):
                        raise ValueError("Invalid signing key")
                    key = jwt.PyJWK.from_dict(value, algorithm="RS256")
                    if key.key.key_size < 2048:
                        raise ValueError("Invalid signing key size")
                    keys[value["kid"]] = key
                self._keys = keys
                return True
            except (URLError, OSError, ValueError, KeyError, TypeError, jwt.PyJWTError):
                self._keys = {}
                logger.warning("identity.jwks.unavailable")
                return False

    def verify(self, token: str) -> dict[str, object]:
        """Reject any invalid signature, lifetime, tenant, audience or issuer."""
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if (
                header.get("alg") != "RS256"
                or not isinstance(kid, str)
                or len(kid) > 128
            ):
                raise InvalidIdentityToken("invalid_token")
            if kid not in self._keys:
                self.refresh()
            key = self._keys.get(kid)
            if key is None:
                raise InvalidIdentityToken("invalid_token")
            claims = jwt.decode(
                token,
                key.key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                leeway=0,
                options={
                    "require": ["iss", "aud", "exp", "nbf", "iat", "tid"],
                    "strict_aud": True,
                },
            )
            if claims["tid"] != self.tenant:
                raise InvalidIdentityToken("invalid_token")
            return claims
        except (jwt.PyJWTError, ValueError, TypeError):
            raise InvalidIdentityToken("invalid_token") from None
