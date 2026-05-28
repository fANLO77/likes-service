.PHONY: up down test proto clean

# Запуск всей системы
up:
	docker compose up --build -d

# Остановка
down:
	docker compose down

# Тесты (неделя 17 — интеграционные)
test:
	@echo "=== Checking required files ==="
	@test -f ARCHITECTURE.md       && echo "OK ARCHITECTURE.md"     || (echo "MISSING ARCHITECTURE.md"; exit 1)
	@test -f docker-compose.yml    && echo "OK docker-compose.yml"  || (echo "MISSING docker-compose.yml"; exit 1)
	@test -f README.md             && echo "OK README.md"           || (echo "MISSING README.md"; exit 1)
	@test -f proto/likes.proto     && echo "OK proto/likes.proto"   || (echo "MISSING proto/likes.proto"; exit 1)
	@test -f .github/workflows/ci.yml && echo "OK CI pipeline"     || (echo "MISSING .github/workflows/ci.yml"; exit 1)
	@echo "=== Running integration tests ==="
	pytest tests/ -v

# Перегенерировать proto stubs (нужен grpcio-tools)
proto:
	python -m grpc_tools.protoc -I./proto \
	    --python_out=./likes-svc/app \
	    --grpc_python_out=./likes-svc/app \
	    ./proto/likes.proto
	cp likes-svc/app/likes_pb2*.py gateway/proto_stubs/

clean:
	docker compose down --rmi local -v