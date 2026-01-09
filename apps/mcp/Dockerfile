FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Minimal runtime deps for MCP server + Google Sheets API
RUN pip install --no-cache-dir \
    "mcp[cli]" \
    httpx \
    uvicorn \
    fastmcp \
    starlette \
    sse-starlette \
    google-auth \
    google-api-python-client \
    gspread \
    python-dotenv

COPY . /app/

CMD ["python","-u","/app/server.py"]
