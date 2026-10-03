# syntax=docker/dockerfile:1
# Loyalty Service. Контекст сборки — корень репозитория: образу нужны и общая библиотека, и сам сервис.

FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt


FROM python:3.12-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8050

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY libs/common ./common
COPY services/loyalty ./loyalty

RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8050

CMD ["sh", "-c", "exec uvicorn loyalty.main:app --host 0.0.0.0 --port ${PORT}"]
