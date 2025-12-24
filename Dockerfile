FROM python:3.13-slim AS builder

WORKDIR /usr/src/app/tesla_dashcam

# Install uv
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Install from lockfile (reproducible) into a dedicated venv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Install project into that venv without re-resolving dependencies
COPY tesla_dashcam ./tesla_dashcam
COPY README.md LICENSE AUTHORS ./
RUN uv pip install --no-deps --prefix /opt/venv .


FROM python:3.13-slim AS runtime

WORKDIR /usr/src/app/tesla_dashcam

RUN apt-get update -y \
    && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-freefont-ttf \
    libnotify-bin \
    && rm -rf /var/lib/apt/lists/*

ENV LIBRARY_PATH=/lib:/usr/lib

COPY --from=builder /opt/venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Enable Logs to show on run
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=true
# Provide a default timezone
ENV TZ=America/New_York

ENTRYPOINT ["python", "-m", "tesla_dashcam"]