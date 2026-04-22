# CopilotKit Node runtime bridge between React SDK and the Python agent.
FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts

COPY runtime.mjs ./

EXPOSE 5003

CMD ["node", "runtime.mjs"]
