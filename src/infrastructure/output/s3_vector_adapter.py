import time
from typing import Tuple, List, Dict, Any
from src.application.ports.output.vector_store_port import VectorStorePort
from s3_client import S3VectorsClient

class S3VectorAdapter(VectorStorePort):
    def __init__(self, s3_client: S3VectorsClient, bucket_name: str, index_name: str):
        self.s3_client = s3_client
        self.bucket_name = bucket_name
        self.index_name = index_name

    def retrieve(self, vector: List[float], top_k: int = 5) -> Tuple[List[Dict[str, Any]], float]:
        t0 = time.perf_counter()
        docs = self.s3_client.retrieve(vector, self.bucket_name, self.index_name, top_k)
        t1 = time.perf_counter()
        return docs, (t1 - t0) * 1000
