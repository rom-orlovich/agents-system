FROM node:20-alpine

WORKDIR /app

RUN apk add --no-cache git curl

RUN npm install -g @modelcontextprotocol/server-github

ENV PORT=9001
ENV GITHUB_API_URL=http://github-api:3001

EXPOSE 9001

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9001/health || exit 1

CMD ["npx", "-y", "@modelcontextprotocol/server-github"]
