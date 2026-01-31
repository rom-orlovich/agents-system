FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastmcp>=2.0.0 \
    httpx>=0.27.0 \
    pydantic-settings>=2.0.0

COPY . .

ENV KG_PORT=9005
ENV KG_KNOWLEDGE_GRAPH_URL=http://knowledge-graph:4000

EXPOSE 9005

CMD ["python", "main.py"]
