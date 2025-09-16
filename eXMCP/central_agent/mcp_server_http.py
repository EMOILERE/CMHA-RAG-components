import asyncio
from fastapi import FastAPI, Request, Response
from starlette.responses import StreamingResponse
from mcp.server.streamable_http import streamablehttp_server
from central_agent.mcp_server import mcp_server_main

app = FastAPI()

@app.post("/mcp")
async def mcp_endpoint(request: Request):
    # 使用官方streamablehttp_server对接MCP协议流
    async def stream_response():
        async for chunk in streamablehttp_server(request):
            yield chunk
    return StreamingResponse(stream_response(), media_type="application/octet-stream")

# 启动命令：
# uvicorn central_agent.mcp_server_http:app --host 0.0.0.0 --port 8080 