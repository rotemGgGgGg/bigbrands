FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bridge bridge
ENV BRIDGE_DATA=/data
VOLUME /data
EXPOSE 8000
CMD ["uvicorn", "bridge.cloud:create_cloud_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
