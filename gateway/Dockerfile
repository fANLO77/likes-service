FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn grpcio grpcio-tools

COPY proto_stubs/ /app/proto_stubs/

COPY main.py .

EXPOSE 8154

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8154"]