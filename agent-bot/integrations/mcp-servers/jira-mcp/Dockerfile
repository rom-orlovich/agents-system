FROM node:20-slim

WORKDIR /app

RUN npm install -g @atlassian/mcp-server-jira

EXPOSE 9002

ENV JIRA_URL=""
ENV JIRA_EMAIL=""
ENV JIRA_API_TOKEN=""
ENV PORT=9002

CMD ["mcp-server-jira"]
