from fastapi import Request, Response
from fastapi.routing import APIRoute
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse

from auth_routes import limiter


MAX_REQUEST_BYTES = 65_536
SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}


@limiter.shared_limit("120/minute", scope="business_writes")
def check_business_write(request: Request, response: Response):
    return response


class BusinessRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handle(request: Request):
            if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
                headers = Response()
                await run_in_threadpool(check_business_write, request, headers)
                response = await original(request)
                for key, value in headers.headers.items():
                    if key.startswith("x-ratelimit-") or key == "retry-after":
                        response.headers[key] = value
                return response
            return await original(request)

        return handle


class RequestSecurityMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def secured_send(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.update(SECURITY_HEADERS)
            await send(message)

        headers = dict(scope.get("headers", []))
        try:
            declared_size = int(headers.get(b"content-length", b"0"))
            if declared_size < 0:
                raise ValueError
        except ValueError:
            return await JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)(scope, receive, secured_send)
        if declared_size > MAX_REQUEST_BYTES:
            return await JSONResponse({"detail": "Request body too large"}, status_code=413)(scope, receive, secured_send)

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > MAX_REQUEST_BYTES:
                return await JSONResponse({"detail": "Request body too large"}, status_code=413)(scope, receive, secured_send)
            body.extend(chunk)
            if not message.get("more_body", False):
                break

        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, secured_send)
