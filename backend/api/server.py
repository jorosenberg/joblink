"""
HTTP shim - replaces AWS API Gateway (AWS_PROXY v2) + Lambda runtime.
handler.handler is called unchanged; this only converts HTTP <-> event dict.
Run: uvicorn server:app --host 0.0.0.0 --port 7860
"""
import json

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from handler import handler

app = FastAPI(title="joblink api")

# Mirrors the API Gateway cors_configuration 1:1
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Scrape-Password"],
    max_age=3600,
)


@app.get("/")
def health():
    return {"status": "ok", "service": "joblink-api"}


@app.api_route("/api/{rest:path}", methods=["GET", "DELETE"])
async def dispatch(request: Request, rest: str):
    event = {
        "rawPath": request.url.path,
        "requestContext": {"http": {"method": request.method}},
        "queryStringParameters": dict(request.query_params) or None,
        "headers": {k.lower(): v for k, v in request.headers.items()},
    }
    result = handler(event, None)
    return Response(
        content=result.get("body", "{}"),
        status_code=result.get("statusCode", 200),
        media_type="application/json",
    )
