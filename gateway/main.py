import logging
import os
import grpc
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
sys.path.insert(0, "/app/proto_stubs")

import likes_pb2
import likes_pb2_grpc

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

GRPC_HOST = os.getenv("GRPC_HOST", "likes-svc")
GRPC_PORT = os.getenv("GRPC_PORT", "50051")

app = FastAPI(title="Likes Gateway", version="1.0.0")


def get_stub():
    channel = grpc.insecure_channel(f"{GRPC_HOST}:{GRPC_PORT}")
    return likes_pb2_grpc.LikesServiceStub(channel)


class LikeCreate(BaseModel):
    target: str


class LikeOut(BaseModel):
    id: int
    target: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/likes", response_model=list[LikeOut])
def list_likes():
    try:
        stub = get_stub()
        resp = stub.ListLikes(likes_pb2.ListLikesRequest())
        logger.info("list_likes count=%d", len(resp.likes))
        return [{"id": l.id, "target": l.target} for l in resp.likes]
    except grpc.RpcError as e:
        logger.error("gRPC error: %s", e)
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/likes", response_model=LikeOut, status_code=201)
def create_like(body: LikeCreate):
    try:
        stub = get_stub()
        resp = stub.CreateLike(likes_pb2.CreateLikeRequest(target=body.target))
        logger.info("create_like id=%d target=%s", resp.like.id, resp.like.target)
        return {"id": resp.like.id, "target": resp.like.target}
    except grpc.RpcError as e:
        logger.error("gRPC error: %s", e)
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/likes/{like_id}", response_model=LikeOut)
def get_like(like_id: int):
    try:
        stub = get_stub()
        resp = stub.GetLike(likes_pb2.GetLikeRequest(id=like_id))
        return {"id": resp.like.id, "target": resp.like.target}
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Like not found")
        raise HTTPException(status_code=502, detail=str(e))


@app.delete("/api/likes/{like_id}", status_code=204)
def delete_like(like_id: int):
    try:
        stub = get_stub()
        stub.DeleteLike(likes_pb2.DeleteLikeRequest(id=like_id))
        logger.info("delete_like id=%d", like_id)
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Like not found")
        raise HTTPException(status_code=502, detail=str(e))