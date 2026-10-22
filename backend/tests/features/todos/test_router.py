import pytest

NOT_FOUND = {"detail": "Task not found."}


def generated_fields_removed(body):
    return {name: value for name, value in body.items() if name not in {"id", "created_at", "updated_at"}}


def create(client, **payload):
    response = client.post("/api/todos", json=payload)
    assert response.status_code == 201
    return response.json()


def error_locations(response):
    return [error["loc"] for error in response.json()["detail"]]


def test_list_without_tasks_returns_an_empty_array(client):
    response = client.get("/api/todos")
    assert (response.status_code, response.json()) == (200, [])


def test_create_returns_201_with_trimmed_text_and_defaults(client):
    response = client.post("/api/todos", json={"title": "  Plan the sprint  ", "description": "  Agenda  "})
    assert response.status_code == 201
    assert generated_fields_removed(response.json()) == {
        "title": "Plan the sprint", "description": "Agenda", "priority": "medium",
        "due_date": None, "completed": False,
    }


def test_created_task_is_returned_by_get(client):
    body = create(
        client, title="Plan the sprint", description="Agenda", priority="high",
        due_date="2026-10-15", completed=True,
    )
    response = client.get(f"/api/todos/{body['id']}")
    assert (response.status_code, response.json()) == (200, body)
    assert generated_fields_removed(body) == {
        "title": "Plan the sprint", "description": "Agenda", "priority": "high",
        "due_date": "2026-10-15", "completed": True,
    }


def test_list_returns_200_with_the_created_task(client):
    body = create(client, title="Plan the sprint")
    response = client.get("/api/todos")
    assert (response.status_code, response.json()) == (200, [body])


def test_create_accepts_maximum_length_title_and_description(client):
    body = create(client, title="x" * 120, description="d" * 2000)
    assert (body["title"], body["description"]) == ("x" * 120, "d" * 2000)


@pytest.mark.parametrize(
    ("payload", "location"),
    [
        ({}, ["body", "title"]),
        ({"title": "   "}, ["body", "title"]),
        ({"title": "x" * 121}, ["body", "title"]),
        ({"title": None}, ["body", "title"]),
        ({"title": "Task", "description": "d" * 2001}, ["body", "description"]),
        ({"title": "Task", "description": None}, ["body", "description"]),
        ({"title": "Task", "priority": "urgent"}, ["body", "priority"]),
        ({"title": "Task", "due_date": "2026-02-30"}, ["body", "due_date"]),
        ({"title": "Task", "completed": "true"}, ["body", "completed"]),
        ({"title": "Task", "completed": 1}, ["body", "completed"]),
        ({"title": "Task", "owner": "me"}, ["body", "owner"]),
    ],
    ids=[
        "missing-title", "blank-title", "title-too-long", "null-title", "description-too-long",
        "null-description", "unknown-priority", "impossible-date", "completed-as-string",
        "completed-as-number", "unknown-field",
    ],
)
def test_invalid_create_returns_422_naming_the_field_and_stores_nothing(client, payload, location):
    response = client.post("/api/todos", json=payload)
    assert (response.status_code, error_locations(response)) == (422, [location])
    assert client.get("/api/todos").json() == []


def test_get_unknown_id_returns_404(client):
    response = client.get("/api/todos/404")
    assert (response.status_code, response.json()) == (404, NOT_FOUND)


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
@pytest.mark.parametrize("todo_id", ["0", "-1", "abc"], ids=["zero", "negative", "not-a-number"])
def test_invalid_task_id_returns_422_naming_the_path_parameter(client, method, todo_id):
    response = client.request(method, f"/api/todos/{todo_id}", json={"title": "Renamed"})
    assert (response.status_code, error_locations(response)) == (422, [["path", "todo_id"]])


def test_patch_returns_the_task_with_trimmed_changes(client):
    body = create(client, title="Plan the sprint", description="Agenda", priority="high")
    response = client.patch(f"/api/todos/{body['id']}", json={"title": "  Renamed  ", "completed": True})
    assert response.status_code == 200
    assert generated_fields_removed(response.json()) == {
        "title": "Renamed", "description": "Agenda", "priority": "high",
        "due_date": None, "completed": True,
    }


def test_patch_with_null_due_date_returns_200_with_the_date_cleared(client):
    body = create(client, title="Plan the sprint", due_date="2026-10-15")
    response = client.patch(f"/api/todos/{body['id']}", json={"due_date": None})
    assert response.status_code == 200
    assert generated_fields_removed(response.json()) == {
        "title": "Plan the sprint", "description": "", "priority": "medium",
        "due_date": None, "completed": False,
    }


def test_patch_unknown_id_returns_404(client):
    response = client.patch("/api/todos/404", json={"title": "Renamed"})
    assert (response.status_code, response.json()) == (404, NOT_FOUND)


@pytest.mark.parametrize(
    ("payload", "location"),
    [
        ({"title": "   "}, ["body", "title"]),
        ({"title": "x" * 121}, ["body", "title"]),
        ({"description": "d" * 2001}, ["body", "description"]),
        ({"priority": "urgent"}, ["body", "priority"]),
        ({"due_date": "2026-02-30"}, ["body", "due_date"]),
        ({"completed": "yes"}, ["body", "completed"]),
        ({"owner": "me"}, ["body", "owner"]),
    ],
    ids=[
        "blank-title", "title-too-long", "description-too-long", "unknown-priority",
        "impossible-date", "completed-as-string", "unknown-field",
    ],
)
def test_invalid_patch_returns_422_naming_the_field_and_changes_nothing(client, payload, location):
    body = create(client, title="Plan the sprint")
    response = client.patch(f"/api/todos/{body['id']}", json=payload)
    assert (response.status_code, error_locations(response)) == (422, [location])
    assert client.get(f"/api/todos/{body['id']}").json() == body


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({}, "Value error, Provide at least one field to update."),
        ({"title": None}, "Value error, Field title cannot be null."),
        ({"description": None}, "Value error, Field description cannot be null."),
        ({"priority": None}, "Value error, Field priority cannot be null."),
        ({"completed": None}, "Value error, Field completed cannot be null."),
    ],
    ids=["empty-patch", "null-title", "null-description", "null-priority", "null-completed"],
)
def test_patch_rejects_empty_or_null_fields_with_422_on_the_body(client, payload, message):
    body = create(client, title="Plan the sprint")
    response = client.patch(f"/api/todos/{body['id']}", json=payload)
    assert response.status_code == 422
    assert [(error["loc"], error["msg"]) for error in response.json()["detail"]] == [(["body"], message)]
    assert client.get(f"/api/todos/{body['id']}").json() == body


def test_delete_returns_204_with_an_empty_body(client):
    body = create(client, title="Plan the sprint")
    response = client.delete(f"/api/todos/{body['id']}")
    assert (response.status_code, response.content) == (204, b"")


def test_deleted_task_is_no_longer_found(client):
    body = create(client, title="Plan the sprint")
    client.delete(f"/api/todos/{body['id']}")
    assert client.get(f"/api/todos/{body['id']}").status_code == 404


def test_delete_unknown_id_returns_404(client):
    response = client.delete("/api/todos/404")
    assert (response.status_code, response.json()) == (404, NOT_FOUND)
