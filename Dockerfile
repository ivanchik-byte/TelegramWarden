# Multi-stage production Dockerfile for TelegramWarden
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build tools and C-libraries for compiling requirements if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libzbar-dev \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# Final runtime stage
FROM python:3.12-slim AS runner

WORKDIR /app

# Install minimal runtime shared libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libzbar0 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python wheels from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy project source code
COPY . .

# Create logs directory
RUN mkdir -p logs models_cache

EXPOSE 2009

CMD ["python", "-m", "bot.main"]
