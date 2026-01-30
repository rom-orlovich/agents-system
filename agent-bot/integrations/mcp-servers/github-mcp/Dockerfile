FROM node:20-slim

WORKDIR /app

RUN npm install -g @github/github-mcp-server

EXPOSE 9001

ENV GITHUB_TOKEN=""
ENV PORT=9001

CMD ["github-mcp-server"]
