import io
import logging
import uuid
from datetime import datetime, timezone

from minio import Minio
from minio.error import S3Error

from app.config import settings

logger = logging.getLogger(__name__)

_minio_client: Minio | None = None


def _get_minio() -> Minio:
    global _minio_client
    if _minio_client is None:
        _minio_client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=False,
        )
    return _minio_client


async def upload_to_minio(file_bytes: bytes, filename: str, bucket: str | None = None, prefix: str = "") -> str:
    """上传文件到 MinIO，返回 object_path。

    Args:
        file_bytes: 文件字节流
        filename: 原始文件名（用于生成存储路径）
        bucket: 桶名称，默认使用 settings.minio_bucket_reports
        prefix: 可选路径前缀（如 "user_15/"）

    Returns:
        对象存储路径，格式: "{prefix}{date}/{uuid}_{filename}"
    """
    bucket = bucket or settings.minio_bucket_reports
    client = _get_minio()
    await _ensure_bucket(client, bucket)

    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    date_prefix = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    object_path = f"{prefix}{date_prefix}/{uuid.uuid4().hex}_{filename}"

    data = io.BytesIO(file_bytes)
    client.put_object(
        bucket_name=bucket,
        object_name=object_path,
        data=data,
        length=len(file_bytes),
        content_type=_mime_from_ext(ext),
    )
    logger.info(f"Uploaded {len(file_bytes)} bytes to {bucket}/{object_path}")
    return object_path


async def get_from_minio(object_path: str, bucket: str | None = None) -> bytes:
    """从 MinIO 下载文件。

    Args:
        object_path: 上传时返回的对象路径
        bucket: 桶名称

    Returns:
        文件字节流
    """
    bucket = bucket or settings.minio_bucket_reports
    client = _get_minio()

    try:
        response = client.get_object(bucket_name=bucket, object_name=object_path)
        data = response.read()
        response.close()
        response.release_conn()
        return data
    except S3Error as e:
        logger.error(f"MinIO get failed: {e}")
        raise


async def _ensure_bucket(client: Minio, bucket: str) -> None:
    found = client.bucket_exists(bucket)
    if not found:
        client.make_bucket(bucket)
        logger.info(f"Created MinIO bucket: {bucket}")


def _mime_from_ext(ext: str) -> str:
    return {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "pdf": "application/pdf",
        "dcm": "application/dicom",
    }.get(ext.lower(), "application/octet-stream")
