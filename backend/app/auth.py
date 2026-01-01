import httpx
from jose import jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Replace with your actual Clerk domain!!
CLERK_ISSUER = "https://glorious-cicada-91.clerk.accounts.dev"
CLERK_JWKS_URL = "https://glorious-cicada-91.clerk.accounts.dev/.well-known/jwks.json"
CLERK_API_URL = "https://api.clerk.com/v1/users"
CLERK_SECRET_KEY = "sk_test_ydR5mlLnUrufnI0RcWGRh4twj9iuIuMnh2Q5hZhVhn"

# 🔴 CHANGE 1: auto_error=False (CRITICAL)
security = HTTPBearer(auto_error=False)
jwks_cache = None


async def get_clerk_public_keys():
    global jwks_cache
    if jwks_cache is None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(CLERK_JWKS_URL)
            resp.raise_for_status()
            jwks_cache = resp.json()["keys"]
    return jwks_cache


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # 🔴 CHANGE 2: Allow OPTIONS (CORS preflight)
    if request.method == "OPTIONS":
        return None

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )

    token = credentials.credentials

    try:
        headers = jwt.get_unverified_header(token)
        jwks = await get_clerk_public_keys()

        key = None
        for jwk in jwks:
            if jwk["kid"] == headers["kid"]:
                key = jwk
                break

        if not key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Public key not found for token"
            )

        # Verify JWT
        payload = jwt.decode(
            token,
            key,
            issuer=CLERK_ISSUER,
            algorithms=["RS256"]
        )

        clerk_user_id = payload["sub"]

        # Fetch user details from Clerk API
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {CLERK_SECRET_KEY}"}
            resp = await client.get(
                f"{CLERK_API_URL}/{clerk_user_id}",
                headers=headers
            )
            resp.raise_for_status()
            user_data = resp.json()

        email = user_data["email_addresses"][0]["email_address"]

        return {
            "clerk_id": clerk_user_id,
            "email": email
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid credentials: {e}"
        )
