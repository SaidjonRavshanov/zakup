# Zakup backend: API (uvicorn) va worker bitta image'dan; buyruq — compose'da.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Avval faqat bog'liqliklar — kod o'zgarsa qatlam keshdan olinadi
COPY pyproject.toml ./
RUN mkdir -p src/zakup && touch src/zakup/__init__.py && pip install . && pip uninstall -y zakup && rm -rf build src

COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src
RUN pip install --no-deps .

# Root emas (VPS qo'llanma §15.3); media — tashqi volume
RUN useradd --system --uid 10001 --home /app app && mkdir -p /app/var/media && chown -R app /app/var
USER app

EXPOSE 8010
CMD ["uvicorn", "zakup.entrypoints.api:app", "--host", "0.0.0.0", "--port", "8010", "--proxy-headers", "--forwarded-allow-ips", "*"]
