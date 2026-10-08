# Builds the React app, then serves it and the API from one Python image.
FROM node:22-slim AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/ ./backend/
RUN pip install --no-cache-dir "./backend[postgres]"
COPY --from=frontend /src/dist ./frontend/dist
ENV PREFSTUDIO_FRONTEND_DIST=/app/frontend/dist
EXPOSE 8000
CMD ["prefstudio", "serve", "--host", "0.0.0.0", "--port", "8000"]
