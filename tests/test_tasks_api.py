"""API tests for task lifecycle and validation."""


def test_create_and_retrieve_task(client, valid_task):
    created = client.post("/api/tasks", json=valid_task)
    assert created.status_code == 201
    payload = created.get_json()
    assert payload["title"] == valid_task["title"]
    assert payload["status"] == "pending"
    assert payload["id"] == 1

    retrieved = client.get(f"/api/tasks/{payload['id']}")
    assert retrieved.status_code == 200
    assert retrieved.get_json()["description"] == valid_task["description"]


def test_list_tasks_and_filter_by_status(client, valid_task):
    client.post("/api/tasks", json=valid_task)
    second = {**valid_task, "title": "Prepare hearing bundle", "status": "completed"}
    client.post("/api/tasks", json=second)

    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert response.get_json()["count"] == 2

    filtered = client.get("/api/tasks?status=completed")
    assert filtered.get_json()["count"] == 1
    assert filtered.get_json()["items"][0]["status"] == "completed"


def test_rejects_blank_title(client, valid_task):
    response = client.post("/api/tasks", json={**valid_task, "title": "   "})
    assert response.status_code == 400
    assert "details" in response.get_json()


def test_rejects_invalid_status(client, valid_task):
    response = client.post("/api/tasks", json={**valid_task, "status": "blocked"})
    assert response.status_code == 400


def test_rejects_timezone_naive_due_date(client, valid_task):
    response = client.post("/api/tasks", json={**valid_task, "due_at": "2030-10-20T15:00:00"})
    assert response.status_code == 400


def test_update_status(client, valid_task):
    task_id = client.post("/api/tasks", json=valid_task).get_json()["id"]
    response = client.patch(f"/api/tasks/{task_id}/status", json={"status": "in_progress"})
    assert response.status_code == 200
    assert response.get_json()["status"] == "in_progress"


def test_update_task_fields(client, valid_task):
    task_id = client.post("/api/tasks", json=valid_task).get_json()["id"]
    response = client.patch(f"/api/tasks/{task_id}", json={"title": "Updated title"})
    assert response.status_code == 200
    assert response.get_json()["title"] == "Updated title"


def test_delete_task(client, valid_task):
    task_id = client.post("/api/tasks", json=valid_task).get_json()["id"]
    response = client.delete(f"/api/tasks/{task_id}")
    assert response.status_code == 204
    assert client.get(f"/api/tasks/{task_id}").status_code == 404


def test_unknown_task_returns_404(client):
    response = client.get("/api/tasks/999")
    assert response.status_code == 404
    assert response.get_json()["error"] == "Not Found"


def test_update_requires_at_least_one_field(client, valid_task):
    task_id = client.post("/api/tasks", json=valid_task).get_json()["id"]
    response = client.patch(f"/api/tasks/{task_id}", json={})
    assert response.status_code == 400
