import os

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import JWTVerifier

auth = GoogleProvider(
    client_id=os.getenv("FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID") or "",
    client_secret=os.getenv("FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET") or "",
    base_url="http://localhost:8000",
    # redirect_path="/auth/callback",  # Default path - change if using a different callback URL
    # Optional: specify required scopes
    # required_scopes=["openid", "https://www.googleapis.com/auth/userinfo.email"],
)

def get_jkws():
    url = "http://keycloak:8080/realms/mcp-realm/protocol/openid-connect/certs",
    try:
        jwks_client = requests.get(url, timeout=5)
        jwks_client.raise_for_status()
        JWKS = jwks_client.json()
    except requests.exceptions.RequestException as e:
        JWKS = {}

    return JWKS

def get_rsa_key(pub):
    pass


#JWKS = get_jwks()

auth = JWTVerifier(
    jwks_uri="http://keycloak:8080/realms/mcp-realm/protocol/openid-connect/certs",
    audience="mcp-client",
    issuer="http://localhost:8080/realms/mcp-realm",
    algorithm="RS256",
    base_url="http://keycloak:8080/realms/mcp-realm/protocol/openid-connect/token",
)

mcp = FastMCP("Google OAuth Example Server", auth=auth)


@mcp.tool
def echo(message: str) -> str:
    """Echo the provided message."""
    return message


#if __name__ == "__main__":
#    mcp.run(transport="http", port=8000)
app = mcp.http_app()
