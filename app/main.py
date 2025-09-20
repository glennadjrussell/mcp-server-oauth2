import os
import requests
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from jose import jwt, JWTError
from typing import Dict

# --- Configuration ---
# These are loaded from environment variables set in docker-compose.yml
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak:8080/")
REALM_NAME = os.getenv("REALM_NAME", "mcp-realm")
CLIENT_ID = os.getenv("CLIENT_ID", "mcp-client")

# --- Keycloak Public Key ---
# In a real app, you might cache this and have a refresh mechanism.
# For this example, we fetch it on startup.
def get_jwks():
    KEYCLOAK_CERTS_URL = f"{KEYCLOAK_URL}realms/{REALM_NAME}/protocol/openid-connect/certs"
    try:
        jwks_client = requests.get(KEYCLOAK_CERTS_URL, timeout=5)
        jwks_client.raise_for_status()
        JWKS = jwks_client.json()
    except requests.exceptions.RequestException as e:
        print(f"Could not fetch JWKS from Keycloak: {e}")
        JWKS = {}

    return JWKS

# --- FastAPI Setup ---
app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{KEYCLOAK_URL}realms/{REALM_NAME}/protocol/openid-connect/token")

# --- Pydantic Models ---
class DummyContext(BaseModel):
    request_id: str
    user_id: str
    context: Dict[str, str]

# --- Security Dependency ---
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Decodes and validates the JWT token from the Authorization header.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Get the unverified header to find the correct key
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        JWKS = get_jwks()
        if not JWKS:
             raise credentials_exception

        for key in JWKS["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }
        if not rsa_key:
            raise credentials_exception

        # Decode and validate the token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=CLIENT_ID,
            #issuer=f"{KEYCLOAK_URL}realms/{REALM_NAME}",
            issuer=f"http://localhost:8080/realms/{REALM_NAME}",
        )
        username: str = payload.get("preferred_username")
        if username is None:
            raise credentials_exception
        return payload
    except JWTError as je:
        print(je)
        raise credentials_exception

# --- API Endpoint ---
@app.get("/context", response_model=DummyContext)
async def get_model_context(current_user: dict = Depends(get_current_user)):
    """
    This is the protected endpoint. It will only return data if the
    user provides a valid JWT token.
    """
    user_id = current_user.get("sub") # 'sub' is the standard JWT claim for subject/user ID
    return {
        "request_id": "xyz-123-abc-456",
        "user_id": user_id,
        "context": {
            "message": f"Hello, {current_user.get('preferred_username')}! This is your protected dummy data.",
            "timestamp": "2025-09-20T15:21:00Z"
        }
    }

@app.get("/")
def read_root():
    return {"status": "Model Context Protocol Server is running"}
