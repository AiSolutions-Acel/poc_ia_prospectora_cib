import boto3
from typing import List, Dict, Any
from src.providers.config import get_settings

settings = get_settings()

class S3VectorsClient:
    def __init__(self):
        self.client = boto3.client(
            "s3vectors",
            region_name=settings.s3vectors_region,
        )

    def retrieve(
        self,
        query_vector: List[float],
        bucket_name: str,
        index_name: str,
        k: int | None = None,
    ) -> List[Dict[str, Any]]:
        if k is None:
            k = settings.retrieval_top_k

        res = self.client.query_vectors(
            vectorBucketName=bucket_name,
            indexName=index_name,
            queryVector={"float32": query_vector},
            topK=k,
            returnMetadata=True,
            returnDistance=True,
        )

        documents = []
        for match in res.get("vectors", []):
            documents.append({
                "text": match.get("metadata", {}).get("text", ""),
                "score": 1.0 - match.get("distance", 0.0),
            })
        return documents
