from datetime import datetime, timezone
from uuid import uuid4


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024


class StoredImage:
    def __init__(
        self,
        owner_id: str,
        filename: str,
        content_type: str,
        content: bytes,
        product_id: str | None = None,
    ) -> None:
        self.image_id = uuid4().hex
        self.owner_id = owner_id
        self.filename = filename
        self.content_type = content_type
        self.content = content
        self.size = len(content)
        self.product_id = product_id
        self.created_at = datetime.now(timezone.utc)


class ImageStorage:
    def __init__(self) -> None:
        self.avatars: dict[str, StoredImage] = {}
        self.product_images: dict[str, StoredImage] = {}

    def save_avatar(
        self,
        user_id: str,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> StoredImage:
        self._validate_image(content_type, content)
        image = StoredImage(user_id, filename, content_type, content)
        self.avatars[user_id] = image
        return image

    def save_product_image(
        self,
        product_id: str,
        owner_id: str,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> StoredImage:
        self._validate_image(content_type, content)
        image = StoredImage(
            owner_id, filename, content_type, content, product_id
        )
        self.product_images[image.image_id] = image
        return image

    def delete_product_image(
        self, product_id: str, image_id: str, owner_id: str
    ) -> None:
        image = self.product_images.get(image_id)
        if image is None or image.product_id != product_id:
            raise KeyError("image not found")
        if image.owner_id != owner_id:
            raise PermissionError("not allowed to delete this image")
        del self.product_images[image_id]

    @staticmethod
    def _validate_image(content_type: str, content: bytes) -> None:
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise ValueError("file must be a JPEG, PNG, or WebP image")
        if not content:
            raise ValueError("file must not be empty")
        if len(content) > MAX_IMAGE_SIZE:
            raise ValueError("file size must not exceed 5 MB")

        signatures_are_valid = {
            "image/jpeg": content.startswith(b"\xff\xd8\xff"),
            "image/png": content.startswith(b"\x89PNG\r\n\x1a\n"),
            "image/webp": (
                len(content) >= 12
                and content.startswith(b"RIFF")
                and content[8:12] == b"WEBP"
            ),
        }
        if not signatures_are_valid[content_type]:
            raise ValueError("file content does not match its MIME type")
