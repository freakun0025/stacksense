# StackSense - zero-dependency image (Python standard library only)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STACKSENSE_LLM=off \
    STACKSENSE_OPEN_BROWSER=0 \
    STACKSENSE_HOST=0.0.0.0 \
    STACKSENSE_PORT=8000

WORKDIR /app
COPY . /app

RUN useradd --create-home stacksense && chown -R stacksense /app
USER stacksense

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status==200 else 1)"

CMD ["python", "stacksense.py", "serve", "--host", "0.0.0.0", "--port", "8000"]
