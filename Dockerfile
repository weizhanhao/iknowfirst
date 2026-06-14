FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -e .
ENV CONFIG_PATH=/app/config.yaml
CMD ["python", "-m", "iknowfirst.main"]
