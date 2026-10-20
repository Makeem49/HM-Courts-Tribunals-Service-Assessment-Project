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


def test_rejects_duplicate_title_ignoring_case_and_whitespace(client, valid_task):
    client.post("/api/tasks", json=valid_task)
    response = client.post("/api/tasks", json={**valid_task, "title": "  REVIEW case documents "})
    assert response.status_code == 409
    assert response.get_json()["message"] == "A task with this title already exists."
    assert client.get("/api/tasks").get_json()["total"] == 1


def test_update_rejects_title_of_another_task(client, valid_task):
    client.post("/api/tasks", json=valid_task)
    task_id = client.post("/api/tasks", json={**valid_task, "title": "File order"}).get_json()["id"]
    response = client.patch(f"/api/tasks/{task_id}", json={"title": "review case documents"})
    assert response.status_code == 409
    assert client.get(f"/api/tasks/{task_id}").get_json()["title"] == "File order"


def test_update_can_keep_or_recase_own_title(client, valid_task):
    task_id = client.post("/api/tasks", json=valid_task).get_json()["id"]
    unchanged = client.patch(f"/api/tasks/{task_id}", json={**valid_task, "status": "completed"})
    assert unchanged.status_code == 200
    recased = client.patch(f"/api/tasks/{task_id}", json={"title": "REVIEW CASE DOCUMENTS"})
    assert recased.status_code == 200
    assert recased.get_json()["title"] == "REVIEW CASE DOCUMENTS"


def test_database_rejects_duplicate_title_that_bypasses_service_check(client, valid_task, monkeypatch):
    from app.repositories.task_repository import TaskRepository

    client.post("/api/tasks", json=valid_task)
    monkeypatch.setattr(TaskRepository, "title_exists", staticmethod(lambda *args, **kwargs: False))
    response = client.post("/api/tasks", json={**valid_task, "title": "Review Case Documents"})
    assert response.status_code == 409
    assert client.get("/api/tasks").get_json()["total"] == 1


def test_title_can_be_reused_after_delete(client, valid_task):
    task_id = client.post("/api/tasks", json=valid_task).get_json()["id"]
    client.delete(f"/api/tasks/{task_id}")
    assert client.post("/api/tasks", json=valid_task).status_code == 201


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


def create_tasks(client, valid_task, total):
    for day in range(1, total + 1):
        client.post("/api/tasks", json={
            **valid_task,
            "title": f"Task {day:02d}",
            "due_at": f"2030-10-{day:02d}T15:00:00Z",
        })


def test_list_tasks_is_paginated_by_default(client, valid_task):
    create_tasks(client, valid_task, 12)

    payload = client.get("/api/tasks").get_json()
    assert payload["count"] == 10
    assert payload["total"] == 12
    assert payload["page"] == 1
    assert payload["page_size"] == 10
    assert payload["pages"] == 2
    assert payload["items"][0]["title"] == "Task 01"

    second_page = client.get("/api/tasks?page=2").get_json()
    assert [task["title"] for task in second_page["items"]] == ["Task 11", "Task 12"]


def test_list_tasks_honours_page_size(client, valid_task):
    create_tasks(client, valid_task, 5)

    payload = client.get("/api/tasks?page=2&page_size=2").get_json()
    assert [task["title"] for task in payload["items"]] == ["Task 03", "Task 04"]
    assert payload["pages"] == 3


def test_page_beyond_last_returns_empty_items(client, valid_task):
    create_tasks(client, valid_task, 3)

    response = client.get("/api/tasks?page=5")
    assert response.status_code == 200
    assert response.get_json()["items"] == []
    assert response.get_json()["total"] == 3


def test_rejects_invalid_pagination_parameters(client):
    for query in ("page=0", "page=abc", "page_size=0", "page_size=101", "status=blocked"):
        response = client.get(f"/api/tasks?{query}")
        assert response.status_code == 400, query
        assert "details" in response.get_json()


def test_blank_query_parameters_are_ignored(client, valid_task):
    create_tasks(client, valid_task, 2)

    response = client.get("/api/tasks?status=&search=")
    assert response.status_code == 200
    assert response.get_json()["total"] == 2


def test_search_matches_title_or_description_and_combines_with_status(client, valid_task):
    client.post("/api/tasks", json={**valid_task, "title": "Prepare HEARING bundle", "description": None})
    client.post("/api/tasks", json={**valid_task, "title": "Call applicant", "description": "Confirm hearing date"})
    client.post("/api/tasks", json={**valid_task, "title": "File order", "status": "completed"})

    found = client.get("/api/tasks?search=hearing").get_json()
    assert found["total"] == 2

    combined = client.get("/api/tasks?search=hearing&status=pending&page_size=1").get_json()
    assert combined["total"] == 2
    assert combined["count"] == 1
    assert combined["pages"] == 2


def test_search_treats_wildcards_literally(client, valid_task):
    client.post("/api/tasks", json={**valid_task, "title": "Apply 100% fee remission"})
    client.post("/api/tasks", json={**valid_task, "title": "Apply fee remission"})

    payload = client.get("/api/tasks?search=100%25").get_json()
    assert [task["title"] for task in payload["items"]] == ["Apply 100% fee remission"]
    assert client.get("/api/tasks?search=_").get_json()["total"] == 0


def test_summary_counts_tasks_by_status(client, valid_task):
    client.post("/api/tasks", json=valid_task)
    client.post("/api/tasks", json={**valid_task, "title": "File order", "status": "completed"})
    client.post("/api/tasks", json={**valid_task, "title": "Send notice", "status": "completed"})

    response = client.get("/api/tasks/summary")
    assert response.status_code == 200
    assert response.get_json() == {"total": 3, "pending": 1, "in_progress": 0, "completed": 2}
