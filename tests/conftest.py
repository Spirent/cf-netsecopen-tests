import pytest
import requests
import sys
import os

myPath = os.path.dirname(os.path.abspath(__file__))
print(f'myPath: {myPath}')
sys.path.insert(0, myPath + '/../')

@pytest.fixture(autouse=True)
def disable_network_calls(monkeypatch):
    def stunted_get():
        raise RuntimeError("Network access not allowed during testing!")
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: stunted_get())