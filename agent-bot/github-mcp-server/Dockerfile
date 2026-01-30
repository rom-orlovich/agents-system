FROM node:20-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/github/github-mcp-server.git . && \
    npm install && \
    npm run build

ENV GITHUB_PERSONAL_ACCESS_TOKEN=${GITHUB_TOKEN}

CMD ["node", "dist/index.js"]
