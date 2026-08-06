# Bazaar shipping-cost engine, runnable in a single container.
#
# The engine uses only the Python standard library; this image additionally
# installs tzdata (needed by zoneinfo for the Asia/Tehran timezone) and pytest
# (to also run the test suite in-container).

FROM python:3.12-slim

# tzdata: the engine resolves ZoneInfo("Asia/Tehran"), which needs the system
# timezone database that slim images do not ship by default.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

# Non-root user (best practice).
RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin appuser

# pytest so the suite can run inside the container too.
RUN pip install --no-cache-dir pytest

WORKDIR /app
COPY shipping_engine/ /app/shipping_engine/
COPY test_shipping.py /app/
COPY orders.json /app/

RUN chown -R appuser:appuser /app
USER appuser

# Default command: run the engine against the files copied into the image.
# compose.yaml overrides this to read/write through a host bind-mount at /work.
CMD ["python", "-m", "shipping_engine.cli", "-i", "orders.json", "-o", "results.json"]
