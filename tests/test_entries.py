def test_delete_entries(client, mock_db):
    mock_db.delete.return_value = 2

    response = client.request("DELETE", "/entries", json={
        "entry_ids": [
            "019abc00-0000-7000-8000-000000000001",
            "019abc00-0000-7000-8000-000000000002",
        ]
    })
    assert response.status_code == 200
    assert response.json() == {"deleted": 2}
    mock_db.delete.assert_awaited_once_with([
        "019abc00-0000-7000-8000-000000000001",
        "019abc00-0000-7000-8000-000000000002",
    ])


def test_delete_empty_list(client, mock_db):
    mock_db.delete.return_value = 0

    response = client.request("DELETE", "/entries", json={"entry_ids": []})
    assert response.status_code == 200
    assert response.json() == {"deleted": 0}
