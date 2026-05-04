FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV AA_MCP_HOST=0.0.0.0
ENV AA_MCP_PORT=8000
CMD ["python", "-m", "src.server"]
