def test_ingest_single_entry(client, mock_db):
    response = client.post("/ingest", json={
        "entries": [{
            "id": "019abc00-0000-7000-8000-000000000001",
            "content": "We decided to use pgvector for the memory service.",
            "memory_type": "daily",
            "date": "2026-04-15",
            "workspace_id": None,
            "metadata": {},
        }]
    })
    assert response.status_code == 200
    assert response.json() == {"ingested": 1}
    mock_db.upsert.assert_awaited_once()

    records = mock_db.upsert.call_args[0][0]
    assert len(records) == 1
    assert records[0]["entry_id"] == "019abc00-0000-7000-8000-000000000001"
    assert records[0]["memory_type"] == "daily"


def test_ingest_multiple_entries(client, mock_db):
    response = client.post("/ingest", json={
        "entries": [
            {"id": "019abc00-0000-7000-8000-000000000001", "content": "First entry", "date": "2026-04-15"},
            {"id": "019abc00-0000-7000-8000-000000000002", "content": "Second entry", "date": "2026-04-15"},
        ]
    })
    assert response.status_code == 200
    assert response.json() == {"ingested": 2}

    records = mock_db.upsert.call_args[0][0]
    assert len(records) == 2


def test_ingest_empty_entries(client, mock_db):
    response = client.post("/ingest", json={"entries": []})
    assert response.status_code == 200
    assert response.json() == {"ingested": 0}
