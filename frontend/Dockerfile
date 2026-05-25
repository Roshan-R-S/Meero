FROM node:18-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --silent || npm install --silent

COPY ./frontend /app

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]
