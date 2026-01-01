import httpx
from jose import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Replace with your actual Clerk domain!!
CLERK_ISSUER="https://glorious-cicada-91.clerk.accounts.dev"
CLERK_JWKS_URL = "https://glorious-cicada-91.clerk.accounts.dev/.well-known/jwks.json"
CLERK_API_URL = "https://api.clerk.com/v1/users"
CLERK_SECRET_KEY = "sk_test_ydR5mlLnUrufnI0RcWGRh4twj9iuIuMnh2Q5hZhVhn"

security = HTTPBearer()
jwks_cache = None

async def get_clerk_public_keys():
    global jwks_cache
    if jwks_cache is None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(CLERK_JWKS_URL)
            resp.raise_for_status()
            jwks_cache = resp.json()["keys"]
    return jwks_cache

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    headers = jwt.get_unverified_header(token)
    jwks = await get_clerk_public_keys()

    key = None
    for jwk in jwks:
        if jwk["kid"] == headers["kid"]:
            key = jwk
            break

    if not key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Public key not found for token.")

    try:
        # Verify jwt
        payload = jwt.decode(token, key, issuer=CLERK_ISSUER, algorithms=["RS256"])
        clerk_user_id = payload["sub"]

        # Fetch user details from Clerk API
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {CLERK_SECRET_KEY}"}
            resp = await client.get(f"{CLERK_API_URL}/{clerk_user_id}", headers=headers)
            resp.raise_for_status()
            user_data = resp.json()

        # extract email from user_data
        email = user_data.get("email_addresses")[0].get("email_address")

        return {"clerk_id": payload["sub"], "email": email}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid credentials: {e}")