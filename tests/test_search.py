def test_search_returns_results(client, mock_db):
    mock_db.search.return_value = [
        {"entry_id": "019abc00-0000-7000-8000-000000000001", "score": 0.92},
        {"entry_id": "019abc00-0000-7000-8000-000000000002", "score": 0.85},
    ]

    response = client.post("/search", json={
        "query": "what did we decide about the database",
        "limit": 10,
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2
    assert data["results"][0]["entry_id"] == "019abc00-0000-7000-8000-000000000001"
    assert data["results"][0]["score"] == 0.92


def test_search_with_filters(client, mock_db):
    mock_db.search.return_value = []

    response = client.post("/search", json={
        "query": "auth decisions",
        "memory_type": "daily",
        "date_from": "2026-04-01",
        "date_to": "2026-04-15",
        "limit": 5,
    })
    assert response.status_code == 200

    call_kwargs = mock_db.search.call_args[1]
    assert call_kwargs["memory_type"] == "daily"
    assert call_kwargs["date_from"] == "2026-04-01"
    assert call_kwargs["date_to"] == "2026-04-15"
    assert call_kwargs["limit"] == 5


def test_search_empty_results(client, mock_db):
    mock_db.search.return_value = []

    response = client.post("/search", json={"query": "nonexistent topic"})
    assert response.status_code == 200
    assert response.json() == {"results": []}
