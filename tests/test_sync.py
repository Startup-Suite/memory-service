def test_sync_returns_entry_ids(client, mock_db):
    mock_db.list_since.return_value = [
        "019abc00-0000-7000-8000-000000000001",
        "019abc00-0000-7000-8000-000000000002",
    ]

    response = client.get("/sync?since=2026-04-01T00:00:00Z")
    assert response.status_code == 200
    assert response.json() == {
        "entry_ids": [
            "019abc00-0000-7000-8000-000000000001",
            "019abc00-0000-7000-8000-000000000002",
        ]
    }


def test_sync_empty(client, mock_db):
    mock_db.list_since.return_value = []

    response = client.get("/sync?since=2026-04-15T00:00:00Z")
    assert response.status_code == 200
    assert response.json() == {"entry_ids": []}
