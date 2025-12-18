FROM debian:bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NODE_ENV=production \
    PORT=8080

WORKDIR /app

# Install Python + Node + Nginx + Supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv nodejs npm nginx supervisor build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create isolated Python environment to avoid PEP 668 issues
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# ---------- Backend ----------
COPY backend/ /app/backend/
WORKDIR /app/backend
# Install backend runtime deps explicitly (matches pyproject.toml)
RUN pip install --upgrade pip && \
    pip install \
      fastapi \
      "uvicorn[standard]" \
      python-multipart \
      pydantic \
      pydantic-settings \
      python-dateutil \
      pytz \
      Pillow \
      google-generativeai \
      icalendar \
      python-dotenv

# ---------- Frontend ----------
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./

# Allow Next.js build to pick up NEXT_PUBLIC_API_BASE (empty in production for same-origin)
ARG NEXT_PUBLIC_API_BASE
ENV NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE}

RUN npm run build

# ---------- Combine ----------
WORKDIR /app
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 8080

CMD ["/usr/bin/supervisord", "-n"]
