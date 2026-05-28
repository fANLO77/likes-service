# Architecture — Likes Service
**Project Code:** `likes-s03`
---

## Общая схема

```
Client (HTTP)
      │
      ▼  REST :8154
┌─────────────────┐
│    gateway      │  FastAPI
│  (публичный)    │
└────────┬────────┘
         │  gRPC :50051
         ▼
┌─────────────────┐
│  likes-svc-s03  │  Python gRPC
│  (внутренний)   │  in-memory store
└─────────────────┘
```

---

## Сервисы

### 1. `likes-svc-s03` — бизнес-логика

| Атрибут     | Значение               |
|-------------|------------------------|
| Протокол    | gRPC (HTTP/2)          |
| Порт        | 50051 (внутренний)     |
| Хранилище   | In-memory dict         |
| Proto-пакет | `likes.v1`             |
| gRPC-сервис | `LikesService`         |

**gRPC-методы:**

| Метод      | Запрос              | Ответ                | Описание           |
|------------|---------------------|----------------------|--------------------|
| CreateLike | CreateLikeRequest   | LikeResponse         | Создать лайк       |
| GetLike    | GetLikeRequest      | LikeResponse         | Получить по ID     |
| ListLikes  | ListLikesRequest    | ListLikesResponse    | Список всех        |
| DeleteLike | DeleteLikeRequest   | DeleteLikeResponse   | Удалить по ID      |

**Модель данных:**
```proto
message Like {
  int32  id     = 1;
  string target = 2;   // на что поставлен лайк (пост, коммент и т.д.)
}
```

---

### 2. `gateway` — API Gateway

| Атрибут   | Значение         |
|-----------|------------------|
| Протокол  | REST (HTTP/1.1)  |
| Порт      | 8154 (публичный) |
| Фреймворк | FastAPI          |
| Prefix    | `/api`           |

**REST-маршруты:**

| Метод  | Путь              | Код | Описание       |
|--------|-------------------|-----|----------------|
| GET    | `/health`         | 200 | Health check   |
| GET    | `/api/likes`      | 200 | Список лайков  |
| POST   | `/api/likes`      | 201 | Создать лайк   |
| GET    | `/api/likes/{id}` | 200 | Получить по ID |
| DELETE | `/api/likes/{id}` | 204 | Удалить        |

---

## Взаимодействие сервисов

```
Client ──POST /api/likes──▶ gateway ──CreateLike (gRPC)──▶ likes-svc
Client ◀──── 201 Created ── gateway ◀───── LikeResponse ── likes-svc
```

- Внешние клиенты общаются с `gateway` по **REST** — удобно для браузера и curl.
- `gateway` транслирует запросы в `likes-svc` по **gRPC** — бинарный протокол, типобезопасный контракт через `.proto`.
- `likes-svc` не экспонируется наружу (только внутренняя Docker/K8s-сеть).

| Аспект       | REST (gateway)              | gRPC (likes-svc)               |
|--------------|-----------------------------|--------------------------------|
| Клиент       | Браузер, curl, мобилка      | Только внутренние сервисы      |
| Контракт     | OpenAPI / JSON              | `.proto` — строгая типизация   |
| Производит.  | Достаточно для edge-трафика | Быстрый бинарный inter-svc     |
| Отладка      | Легко (curl, браузер)       | Нужен grpcurl или grpc-client  |

---

## Инфраструктура

### Docker Compose (локально)

Для локальной разработки и тестирования используется Docker Compose:

```
docker compose up --build -d
```

Оба сервиса запускаются в одной bridge-сети `likes-network`. `gateway` обращается к `likes-svc` по DNS-имени контейнера. Healthcheck настроен на обоих контейнерах.

```yaml
services:
  likes-svc:   # gRPC, expose 50051 (только внутри)
  gateway:     # REST, ports 8154:8154 (публично)
```

---

## Kubernetes

### Архитектура в кластере

```
Internet
    │
    ▼
┌──────────────────────────────────┐  Kubernetes Cluster
│                                  │
│  ┌────────────────────────────┐  │
│  │  Service: likes-gateway    │  │
│  │  type: LoadBalancer :8154  │  │
│  └──────────┬─────────────────┘  │
│             │                    │
│  ┌──────────▼─────────────────┐  │
│  │  Deployment: likes-gateway │  │
│  │  (replica: 1)              │  │
│  │  image: .../likes-gateway  │  │
│  └──────────┬─────────────────┘  │
│             │ gRPC (ClusterIP)   │
│  ┌──────────▼─────────────────┐  │
│  │  Service: likes-svc-s03    │  │
│  │  type: ClusterIP :50051    │  │
│  └──────────┬─────────────────┘  │
│             │                    │
│  ┌──────────▼─────────────────┐  │
│  │  Deployment: likes-svc-s03 │  │
│  │  (replica: 1)              │  │
│  │  image: .../likes-svc-s03  │  │
│  └────────────────────────────┘  │
│                                  │
│  ConfigMap: likes-app-config     │
│  (GRPC_HOST, GRPC_PORT)          │
└──────────────────────────────────┘
```

### K8s-манифесты (`k8s/`)

| Файл                      | Ресурс                        | Назначение                           |
|---------------------------|-------------------------------|--------------------------------------|
| `configmap.yaml`          | ConfigMap                     | Env-переменные (GRPC_HOST/PORT)      |
| `svc-deployment.yaml`     | Deployment `likes-svc-s03`    | gRPC-сервис, 1 реплика               |
| `svc-service.yaml`        | Service `likes-svc-s03`       | ClusterIP :50051 — только внутренний |
| `gateway-deployment.yaml` | Deployment `likes-gateway`    | REST gateway, 1 реплика              |
| `gateway-service.yaml`    | Service `likes-gateway`       | LoadBalancer :8154 — публичный       |

**Почему ClusterIP для likes-svc?** Сервис gRPC не должен быть доступен снаружи кластера — только через gateway. ClusterIP даёт DNS-имя `likes-svc-s03` внутри кластера и закрывает порт от внешнего мира.

**Почему LoadBalancer для gateway?** Это единственная публичная точка входа. LoadBalancer выдаёт внешний IP через облачный провайдер (или `minikube tunnel` локально).

### Деплой в K8s вручную

```bash
export DOCKERHUB_USERNAME=your_username

envsubst < k8s/configmap.yaml          | kubectl apply -f -
envsubst < k8s/svc-deployment.yaml     | kubectl apply -f -
envsubst < k8s/svc-service.yaml        | kubectl apply -f -
envsubst < k8s/gateway-deployment.yaml | kubectl apply -f -
envsubst < k8s/gateway-service.yaml    | kubectl apply -f -

kubectl rollout status deployment/likes-svc-s03 --timeout=120s
kubectl rollout status deployment/likes-gateway  --timeout=120s
```

---

## CI/CD Pipeline

### Схема пайплайна

```
git push main
      │
      ▼
┌─────────────┐     fail → stop
│  Job: test  │──────────────────▶ ✗
│             │
│ 1. pip install
│ 2. make proto
│ 3. docker compose build
│ 4. docker compose up -d
│ 5. wait /health
│ 6. pytest tests/ -v
│ 7. docker compose down
└──────┬──────┘
       │ success
       ▼
┌──────────────────┐
│ Job: build-push  │  (только main/master)
│                  │
│ 1. docker login
│ 2. build & push likes-svc-s03:latest
│ 3. build & push likes-gateway-s03:latest
└──────┬───────────┘
       │ success
       ▼
┌──────────────────┐
│  Job: deploy     │  (только main)
│                  │
│ 1. kubectl apply configmap
│ 2. kubectl apply svc manifests
│ 3. kubectl apply gateway manifests
│ 4. kubectl rollout status (wait)
│ 5. smoke test /health
└──────────────────┘
```

### Файл: `.github/workflows/ci_cd.yml`

Три последовательных job-а:

| Job         | Триггер              | Что делает                           |
|-------------|----------------------|--------------------------------------|
| `test`      | push/PR → any branch | Собирает, запускает, тестирует       |
| `build-push`| push → main/master   | Пушит образы в Docker Hub            |
| `deploy`    | push → main only     | Раскатывает манифесты в K8s          |

**Необходимые GitHub Secrets:**

| Secret              | Описание                          |
|---------------------|-----------------------------------|
| `DOCKERHUB_USERNAME`| Логин Docker Hub                  |
| `DOCKERHUB_TOKEN`   | Access token Docker Hub           |
| `KUBECONFIG`        | base64 kubeconfig для `kubectl`   |

### Zero Downtime при обновлении

Kubernetes Deployment использует стратегию `RollingUpdate` (по умолчанию): новый под поднимается до того, как старый убивается. Для likes-svc с in-memory хранилищем это означает кратковременную потерю данных при рестарте — допустимо для учебного проекта, в продакшне нужна БД.

---

## Наблюдаемость

- Оба сервиса пишут структурированные логи (`logging`, уровень INFO) с timestamp и методом.
- Docker Compose: healthcheck на каждом контейнере (проверка каждые 10s).
- Kubernetes: readiness/liveness можно добавить через httpGet на `/health` у gateway и exec-проверку у likes-svc.
- CI/CD: smoke-тест `/health` после каждого деплоя.

Микросервисная система управления лайками. Два сервиса:
- **`gateway`** — REST API (FastAPI, порт 8154), единственная публичная точка входа
- **`likes-svc-s03`** — бизнес-логика на gRPC (порт 50051, только внутренняя сеть)

---

## Быстрый старт (Docker Compose)

```bash
# Клонировать репозиторий
git clone <repo-url> && cd likes-s03

# Запустить одной командой
docker compose up --build -d

# Проверить что всё живо
curl http://localhost:8154/health
# {"status":"ok"}
```

### Основные команды

```bash
# Создать лайк
curl -X POST http://localhost:8154/api/likes \
     -H "Content-Type: application/json" \
     -d '{"target": "post-42"}'
# {"id":1,"target":"post-42"}

# Список всех лайков
curl http://localhost:8154/api/likes

# Получить по ID
curl http://localhost:8154/api/likes/1

# Удалить
curl -X DELETE http://localhost:8154/api/likes/1

# Остановить
docker compose down
```

### Логи

```bash
docker compose logs -f gateway    # REST-логи
docker compose logs -f likes-svc  # gRPC-логи
```

---

## Тесты

Сервисы должны быть запущены (`docker compose up -d`).

```bash
# Установить зависимости для тестов 
pip install httpx pytest

# Запустить тесты
pytest tests/ -v
```

---

## Запуск в Kubernetes

### Требования

- Kubernetes кластер (minikube, kind, или облачный)
- `kubectl` настроен на нужный контекст
- Образы запушены в Docker Hub (см. CI/CD)

### Деплой вручную

```bash
# 1. Установить переменную с вашим Docker Hub username
export DOCKERHUB_USERNAME=your_dockerhub_username

# 2. Применить манифесты (envsubst подставит переменную в имена образов)
envsubst < k8s/configmap.yaml        | kubectl apply -f -
envsubst < k8s/svc-deployment.yaml   | kubectl apply -f -
envsubst < k8s/svc-service.yaml      | kubectl apply -f -
envsubst < k8s/gateway-deployment.yaml | kubectl apply -f -
envsubst < k8s/gateway-service.yaml  | kubectl apply -f -

# 3. Дождаться готовности
kubectl rollout status deployment/likes-svc-s03 --timeout=120s
kubectl rollout status deployment/likes-gateway  --timeout=120s

# 4. Получить адрес gateway
kubectl get svc likes-gateway

# Для minikube:
minikube service likes-gateway --url
```

### Проверка в K8s

```bash
# Smoke-тест (подставьте реальный IP из kubectl get svc)
curl http://<EXTERNAL-IP>:8154/health

# Посмотреть поды
kubectl get pods -l app=likes-app

# Логи
kubectl logs -l component=gateway  -f
kubectl logs -l component=likes-svc -f
```

### Удалить из кластера

```bash
kubectl delete -f k8s/
```

---

## CI/CD (GitHub Actions)

При пуше в `main`/`master` автоматически:
1. **test** — поднимает сервисы, запускает `pytest`
2. **build-push** — собирает и пушит образы в Docker Hub
3. **deploy** — применяет K8s-манифесты через `kubectl`

Нужные secrets в GitHub: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `KUBECONFIG`.

---

## Структура проекта

```
likes-s03/
├── proto/
│   └── likes.proto                  # gRPC-контракт
├── likes-svc/
│   ├── Dockerfile
│   └── app/
│       ├── server.py                # gRPC-сервер (бизнес-логика)
│       ├── likes_pb2.py             # сгенерировано из proto
│       └── likes_pb2_grpc.py
├── gateway/
│   ├── Dockerfile
│   ├── main.py                      # FastAPI REST → gRPC
│   └── proto_stubs/                 # копия pb2-файлов для gateway
├── k8s/
│   ├── configmap.yaml
│   ├── svc-deployment.yaml
│   ├── svc-service.yaml
│   ├── gateway-deployment.yaml
│   └── gateway-service.yaml
├── tests/
│   └── test_integration.py
├── .github/
│   └── workflows/
│       └── ci_cd.yml
├── docker-compose.yml
├── Makefile
├── ARCHITECTURE.md
└── README.md
```

## API Reference

| Метод  | Путь              | Тело                   | Успех |
|--------|-------------------|------------------------|-------|
| GET    | /health           | —                      | 200   |
| GET    | /api/likes        | —                      | 200   |
| POST   | /api/likes        | `{"target":"string"}`  | 201   |
| GET    | /api/likes/{id}   | —                      | 200   |
| DELETE | /api/likes/{id}   | —                      | 204   |

Модель: `{"id": 1, "target": "post-42"}`