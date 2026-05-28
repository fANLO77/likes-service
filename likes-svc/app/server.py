import grpc
import logging
from concurrent import futures

import likes_pb2
import likes_pb2_grpc

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_store: dict[int, dict] = {}
_counter = 0


class LikesServicer(likes_pb2_grpc.LikesServiceServicer):

    def CreateLike(self, request, context):
        global _counter
        _counter += 1
        like = {"id": _counter, "target": request.target}
        _store[_counter] = like
        logger.info("CreateLike id=%d target=%s", _counter, request.target)
        return likes_pb2.LikeResponse(
            like=likes_pb2.Like(id=like["id"], target=like["target"])
        )

    def GetLike(self, request, context):
        like = _store.get(request.id)
        if not like:
            context.abort(grpc.StatusCode.NOT_FOUND, f"Like {request.id} not found")
        logger.info("GetLike id=%d", request.id)
        return likes_pb2.LikeResponse(
            like=likes_pb2.Like(id=like["id"], target=like["target"])
        )

    def ListLikes(self, request, context):
        logger.info("ListLikes count=%d", len(_store))
        return likes_pb2.ListLikesResponse(
            likes=[likes_pb2.Like(id=v["id"], target=v["target"]) for v in _store.values()]
        )

    def DeleteLike(self, request, context):
        if request.id not in _store:
            context.abort(grpc.StatusCode.NOT_FOUND, f"Like {request.id} not found")
        del _store[request.id]
        logger.info("DeleteLike id=%d", request.id)
        return likes_pb2.DeleteLikeResponse(success=True)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    likes_pb2_grpc.add_LikesServiceServicer_to_server(LikesServicer(), server)
    server.add_insecure_port("[::]:50051")
    logger.info("gRPC LikesService listening on :50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()