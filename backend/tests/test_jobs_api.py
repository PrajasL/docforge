import pytest
from httpx import AsyncClient

VALID_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF\n"


@pytest.mark.asyncio
async def test_create_job_success(async_client: AsyncClient):
    payload = {
        "tool": "merge",
        "files": [
            {"name": "file1.pdf", "size": 1024, "content_type": "application/pdf"},
            {"name": "file2.pdf", "size": 2048, "content_type": "application/pdf"},
        ],
        "config": {"file_order": []},
    }
    response = await async_client.post(
        "/api/v1/jobs",
        json=payload,
        headers={"X-Session-Id": "test-session-1"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    job_data = data["data"]["job"]
    assert job_data["status"] == "PENDING"
    assert job_data["tool"] == "merge"
    assert len(data["data"]["uploads"]) == 2
    for upload in data["data"]["uploads"]:
        assert "upload_url" in upload
        assert upload["upload_method"] == "PUT"


@pytest.mark.asyncio
async def test_create_job_invalid_extension(async_client: AsyncClient):
    payload = {
        "tool": "merge",
        "files": [
            {"name": "document.exe", "size": 1024, "content_type": "application/pdf"}
        ],
    }
    response = await async_client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422  # Pydantic validator rejects non-.pdf


@pytest.mark.asyncio
async def test_create_job_oversized_file(async_client: AsyncClient):
    payload = {
        "tool": "merge",
        "files": [
            {"name": "huge.pdf", "size": 100 * 1024 * 1024, "content_type": "application/pdf"}
        ],
    }
    response = await async_client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 413
    data = response.json()
    assert data["error"]["code"] == "FILE_TOO_LARGE"


@pytest.mark.asyncio
async def test_create_job_too_many_files(async_client: AsyncClient):
    files = [{"name": f"doc{i}.pdf", "size": 100, "content_type": "application/pdf"} for i in range(25)]
    payload = {"tool": "merge", "files": files}
    response = await async_client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "TOO_MANY_FILES"


@pytest.mark.asyncio
async def test_direct_upload_and_confirmation(async_client: AsyncClient):
    # 1. Create job
    create_resp = await async_client.post(
        "/api/v1/jobs",
        json={
            "tool": "merge",
            "files": [{"name": "test.pdf", "size": len(VALID_PDF_BYTES), "content_type": "application/pdf"}],
        },
        headers={"X-Session-Id": "session-upload-test"},
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["data"]["job"]["id"]
    file_id = create_resp.json()["data"]["uploads"][0]["file_id"]

    # 2. Direct upload valid PDF
    upload_resp = await async_client.put(
        f"/api/v1/jobs/{job_id}/files/{file_id}",
        content=VALID_PDF_BYTES,
        headers={"X-Session-Id": "session-upload-test"},
    )
    assert upload_resp.status_code == 200
    file_info = upload_resp.json()["data"]["file"]
    assert file_info["status"] == "uploaded"

    # 3. Confirm file upload (verifies storage and magic bytes)
    confirm_resp = await async_client.post(
        f"/api/v1/jobs/{job_id}/files/{file_id}/confirm",
        headers={"X-Session-Id": "session-upload-test"},
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["data"]["file"]["status"] == "verified"


@pytest.mark.asyncio
async def test_direct_upload_invalid_content(async_client: AsyncClient):
    create_resp = await async_client.post(
        "/api/v1/jobs",
        json={
            "tool": "merge",
            "files": [{"name": "fake.pdf", "size": 50, "content_type": "application/pdf"}],
        },
        headers={"X-Session-Id": "session-fake-test"},
    )
    job_id = create_resp.json()["data"]["job"]["id"]
    file_id = create_resp.json()["data"]["uploads"][0]["file_id"]

    # Upload non-PDF bytes
    bad_bytes = b"Hello, this is not a PDF file at all."
    upload_resp = await async_client.put(
        f"/api/v1/jobs/{job_id}/files/{file_id}",
        content=bad_bytes,
        headers={"X-Session-Id": "session-fake-test"},
    )
    assert upload_resp.status_code == 415
    assert upload_resp.json()["error"]["code"] == "INVALID_CONTENT_TYPE"


@pytest.mark.asyncio
async def test_start_job_lifecycle(async_client: AsyncClient):
    create_resp = await async_client.post(
        "/api/v1/jobs",
        json={
            "tool": "merge",
            "files": [{"name": "file.pdf", "size": len(VALID_PDF_BYTES), "content_type": "application/pdf"}],
        },
        headers={"X-Session-Id": "session-start-test"},
    )
    job_id = create_resp.json()["data"]["job"]["id"]
    file_id = create_resp.json()["data"]["uploads"][0]["file_id"]

    # Starting without uploading fails
    start_fail = await async_client.post(
        f"/api/v1/jobs/{job_id}/start",
        headers={"X-Session-Id": "session-start-test"},
    )
    assert start_fail.status_code == 409
    assert start_fail.json()["error"]["code"] == "FILES_NOT_READY"

    # Upload file
    await async_client.put(
        f"/api/v1/jobs/{job_id}/files/{file_id}",
        content=VALID_PDF_BYTES,
        headers={"X-Session-Id": "session-start-test"},
    )

    # Start job successfully
    start_success = await async_client.post(
        f"/api/v1/jobs/{job_id}/start",
        headers={"X-Session-Id": "session-start-test"},
    )
    assert start_success.status_code == 200
    assert start_success.json()["data"]["job"]["status"] == "QUEUED"

    # Starting again fails
    start_again = await async_client.post(
        f"/api/v1/jobs/{job_id}/start",
        headers={"X-Session-Id": "session-start-test"},
    )
    assert start_again.status_code == 409
    assert start_again.json()["error"]["code"] == "JOB_ALREADY_STARTED"


@pytest.mark.asyncio
async def test_session_access_control(async_client: AsyncClient):
    create_resp = await async_client.post(
        "/api/v1/jobs",
        json={
            "tool": "merge",
            "files": [{"name": "private.pdf", "size": 100, "content_type": "application/pdf"}],
        },
        headers={"X-Session-Id": "session-user-1"},
    )
    job_id = create_resp.json()["data"]["job"]["id"]

    # Same session can view
    get_ok = await async_client.get(
        f"/api/v1/jobs/{job_id}",
        headers={"X-Session-Id": "session-user-1"},
    )
    assert get_ok.status_code == 200

    # Different session is blocked (403 ACCESS_DENIED)
    get_forbidden = await async_client.get(
        f"/api/v1/jobs/{job_id}",
        headers={"X-Session-Id": "session-user-attacker"},
    )
    assert get_forbidden.status_code == 403
    assert get_forbidden.json()["error"]["code"] == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_cancel_job(async_client: AsyncClient):
    create_resp = await async_client.post(
        "/api/v1/jobs",
        json={
            "tool": "merge",
            "files": [{"name": "doc.pdf", "size": 100, "content_type": "application/pdf"}],
        },
        headers={"X-Session-Id": "session-cancel-test"},
    )
    job_id = create_resp.json()["data"]["job"]["id"]

    cancel_resp = await async_client.post(
        f"/api/v1/jobs/{job_id}/cancel",
        headers={"X-Session-Id": "session-cancel-test"},
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["data"]["job"]["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_pipeline_health(async_client: AsyncClient):
    response = await async_client.get("/api/v1/jobs/pipeline-health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "pipeline" in data["data"]
    assert "database" in data["data"]["pipeline"]
    assert "redis" in data["data"]["pipeline"]
    assert "storage" in data["data"]["pipeline"]
