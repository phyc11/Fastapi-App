import pytest
from fastapi.testclient import TestClient

from src.app import app, auth_service, image_storage, product_catalog
from src.uploads.service import ImageStorage, MAX_IMAGE_SIZE

client = TestClient(app)
PNG = b"\x89PNG\r\n\x1a\n" + b"image-data"
JPEG = b"\xff\xd8\xff" + b"image-data"
WEBP = b"RIFF\x04\x00\x00\x00WEBP" + b"data"


@pytest.fixture(autouse=True)
def clear_state():
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()
    image_storage.avatars.clear()
    image_storage.product_images.clear()
    product_catalog.products.clear()
    yield
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()
    image_storage.avatars.clear()
    image_storage.product_images.clear()
    product_catalog.products.clear()


def auth_headers(name="Alice", email="alice@example.com"):
    user = auth_service.register(name, email, "password123")
    token = auth_service.create_access_token(user)
    return user, {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(
    ("content_type", "content"),
    [("image/jpeg", JPEG), ("image/png", PNG), ("image/webp", WEBP)],
)
def test_storage_accepts_supported_images(content_type, content):
    storage = ImageStorage()
    image = storage.save_avatar("user", "image", content_type, content)
    assert image.content == content
    assert image.size == len(content)
    assert storage.avatars["user"] is image


@pytest.mark.parametrize(
    ("content_type", "content", "message"),
    [
        ("text/plain", b"hello", "file must be a JPEG, PNG, or WebP image"),
        ("image/png", b"", "file must not be empty"),
        ("image/png", PNG + b"x" * MAX_IMAGE_SIZE, "file size must not exceed 5 MB"),
        ("image/png", JPEG, "file content does not match its MIME type"),
    ],
    ids=["unsupported-mime", "empty", "too-large", "mime-mismatch"],
)
def test_storage_rejects_invalid_images(content_type, content, message):
    storage = ImageStorage()
    with pytest.raises(ValueError, match=message):
        storage.save_avatar("user", "image", content_type, content)


def test_avatar_upload_replaces_previous_avatar():
    user, headers = auth_headers()
    first = client.post(
        "/users/me/avatar",
        files={"file": ("first.png", PNG, "image/png")},
        headers=headers,
    )
    second = client.post(
        "/users/me/avatar",
        files={"file": ("second.jpg", JPEG, "image/jpeg")},
        headers=headers,
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["filename"] == "second.jpg"
    assert "content" not in second.json()
    assert image_storage.avatars[user.user_id].filename == "second.jpg"


def test_product_image_upload_and_delete():
    _, headers = auth_headers()
    product_id = product_catalog.add_product("Keyboard", 50, 3)

    upload = client.post(
        f"/products/{product_id}/images",
        files={"file": ("keyboard.webp", WEBP, "image/webp")},
        headers=headers,
    )
    assert upload.status_code == 201
    image = upload.json()
    assert image["product_id"] == product_id
    assert image["content_type"] == "image/webp"

    response = client.delete(
        f"/products/{product_id}/images/{image['image_id']}",
        headers=headers,
    )
    assert response.status_code == 204
    assert image["image_id"] not in image_storage.product_images


def test_only_uploader_can_delete_product_image():
    owner, owner_headers = auth_headers()
    _, other_headers = auth_headers("Bob", "bob@example.com")
    product_id = product_catalog.add_product("Keyboard", 50, 3)
    image = image_storage.save_product_image(
        product_id, owner.user_id, "image.png", "image/png", PNG
    )

    response = client.delete(
        f"/products/{product_id}/images/{image.image_id}",
        headers=other_headers,
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "not allowed to delete this image"}
    assert image.image_id in image_storage.product_images


def test_product_image_endpoints_return_404():
    _, headers = auth_headers()
    upload = client.post(
        "/products/missing/images",
        files={"file": ("image.png", PNG, "image/png")},
        headers=headers,
    )
    assert upload.status_code == 404
    assert upload.json() == {"detail": "Product not found"}

    product_id = product_catalog.add_product("Keyboard", 50, 3)
    delete = client.delete(
        f"/products/{product_id}/images/missing", headers=headers
    )
    assert delete.status_code == 404
    assert delete.json() == {"detail": "image not found"}


@pytest.mark.parametrize(
    ("path", "method"),
    [
        ("/users/me/avatar", "post"),
        ("/products/product/images", "post"),
        ("/products/product/images/image", "delete"),
    ],
)
def test_upload_endpoints_require_authentication(path, method):
    if method == "post":
        response = client.post(
            path, files={"file": ("image.png", PNG, "image/png")}
        )
    else:
        response = client.delete(path)
    assert response.status_code == 401


@pytest.mark.parametrize(
    ("filename", "content", "content_type", "message"),
    [
        ("file.txt", b"hello", "text/plain", "file must be a JPEG, PNG, or WebP image"),
        ("fake.png", JPEG, "image/png", "file content does not match its MIME type"),
    ],
)
def test_avatar_endpoint_rejects_invalid_files(
    filename, content, content_type, message
):
    _, headers = auth_headers()
    response = client.post(
        "/users/me/avatar",
        files={"file": (filename, content, content_type)},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json() == {"detail": message}
