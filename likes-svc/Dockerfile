FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir grpcio grpcio-tools

COPY app/ ./app/

COPY app/likes_pb2.py      ./app/
COPY app/likes_pb2_grpc.py ./app/

WORKDIR /app/app

EXPOSE 50051

CMD ["python", "server.py"]