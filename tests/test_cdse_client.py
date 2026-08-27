import io
import json
import os
import zipfile
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from backend.app.services.cdse_client import CDSEClient


def _minimal_safe_zip_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("S1D_IW_GRDH_1SDV_TEST.SAFE/manifest.safe", "<xfdu:XFDU/>")
        archive.writestr("S1D_IW_GRDH_1SDV_TEST.SAFE/measurement/vv.tiff", b"fake")
    return buffer.getvalue()


@pytest.fixture
def mock_credentials(monkeypatch):
    monkeypatch.setattr("backend.app.core.config.settings.CDSE_CLIENT_ID", "mock_id")
    monkeypatch.setattr("backend.app.core.config.settings.CDSE_CLIENT_SECRET", "mock_secret")

def test_search_sentinel1_invalid_coordinates(mock_credentials):
    client = CDSEClient(client_id="mock", client_secret="mock")
    # This might fail on the API side, so we mock httpx
    with patch("httpx.Client.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = Exception("400 Client Error")
        mock_get.return_value = mock_response

        # Some invalid bbox that would trigger 400 on real API
        result = client.search_sentinel1([200, 200, 210, 210], datetime.now(), datetime.now())
        assert result["data_mode"] == "UNAVAILABLE"

def test_search_sentinel1_zero_results(mock_credentials):
    client = CDSEClient(client_id="mock", client_secret="mock")
    with patch("httpx.Client.post") as mock_post:
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "mock_token"}
        mock_post.return_value = mock_token_resp

        with patch("httpx.Client.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"value": []}
            mock_get.return_value = mock_response

            result = client.search_sentinel1([0, 0, 1, 1], datetime.now(), datetime.now())
            assert result["data_mode"] == "LIVE_API"
            assert result["count"] == 0
            assert len(result["products"]) == 0

@pytest.mark.parametrize("status_code", [401, 403, 404, 500])
def test_search_sentinel1_http_errors(mock_credentials, status_code):
    client = CDSEClient(client_id="mock", client_secret="mock")
    import httpx
    with patch("httpx.Client.post") as mock_post:
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "mock_token"}
        mock_post.return_value = mock_token_resp
        
        with patch("httpx.Client.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = status_code
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("Error", request=MagicMock(), response=mock_response)
            mock_get.return_value = mock_response

            result = client.search_sentinel1([0, 0, 1, 1], datetime.now(), datetime.now())
            assert result["data_mode"] == "UNAVAILABLE"
            assert "HTTP error" in result["message"]

def test_search_sentinel1_success(mock_credentials):
    client = CDSEClient(client_id="mock", client_secret="mock")
    with patch("httpx.Client.post") as mock_post:
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "mock_token"}
        mock_post.return_value = mock_token_resp

        with patch("httpx.Client.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "value": [
                    {
                        "Id": "test-id-123",
                        "Name": "S1A_IW_GRDH_1SDV_2024...",
                        "ContentDate": {"Start": "2024-01-01T12:00:00Z"},
                        "GeoFootprint": {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]},
                        "S3Path": "s3://test-bucket/path",
                        "Attributes": [{"Name": "productType", "Value": "IW_GRDH_1S"}, {"Name": "polarisationChannels", "Value": "VV,VH"}]
                    }
                ]
            }
            mock_get.return_value = mock_response

            result = client.search_sentinel1([0, 0, 1, 1], datetime.now(), datetime.now())
            assert result["data_mode"] == "LIVE_API"
            assert result["count"] == 1
            assert result["products"][0]["id"] == "test-id-123"
            assert result["products"][0]["title"] == "S1A_IW_GRDH_1SDV_2024..."
            assert result["products"][0]["polarisation"] == "VV,VH"
            assert result["products"][0]["product_type"] == "GRD"
            assert result["products"][0]["s3_path"] == "s3://test-bucket/path"


@pytest.fixture
def mock_download_credentials(monkeypatch):
    monkeypatch.setattr("backend.app.core.config.settings.CDSE_USERNAME", "mock_user")
    monkeypatch.setattr("backend.app.core.config.settings.CDSE_PASSWORD", "mock_pass")


def test_sanitize_error_body_redacts_tokens():
    raw = json.dumps({"access_token": "secret-token", "error": "invalid_grant"})
    sanitized = CDSEClient.sanitize_error_body(raw)
    assert "secret-token" not in sanitized
    assert "[REDACTED]" in sanitized
    assert "invalid_grant" in sanitized


def test_request_download_token_reports_http_status(mock_download_credentials):
    client = CDSEClient()
    with patch("httpx.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = json.dumps({"error": "invalid_grant", "access_token": "should-not-leak"})
        mock_client.post.return_value = mock_response

        result = client.request_download_token()
        assert result["ok"] is False
        assert result["http_status"] == 401
        assert "should-not-leak" not in result["sanitized_body"]
        posted = mock_client.post.call_args
        assert posted.args[0] == CDSEClient.TOKEN_URL
        assert posted.kwargs["data"]["grant_type"] == "password"
        assert posted.kwargs["data"]["client_id"] == "cdse-public"


def test_download_product_streams_to_disk(mock_download_credentials, tmp_path):
    client = CDSEClient()
    product_id = "bd3012c2-2e52-4891-91fd-d6fc79084d37"
    zip_bytes = _minimal_safe_zip_bytes()

    token_result = {"ok": True, "http_status": 200, "access_token": "mock-token"}
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.is_redirect = False
    mock_response.headers = {"content-type": "application/zip"}
    mock_response.url = f"https://download.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
    mock_response.iter_bytes.return_value = [zip_bytes[:10], zip_bytes[10:]]

    mock_stream = MagicMock()
    mock_stream.__enter__.return_value = mock_response
    mock_stream.__exit__.return_value = False

    with patch.object(client, "request_download_token", return_value=token_result):
        with patch("httpx.Client") as mock_client_cls:
            mock_http = mock_client_cls.return_value.__enter__.return_value
            mock_http.stream.return_value = mock_stream
            result = client.download_product(
                product_id,
                str(tmp_path),
                product_name="S1D_IW_GRDH_1SDV_TEST.SAFE",
            )

    expected_url = CDSEClient.DOWNLOAD_URL_TEMPLATE.format(product_id=product_id)
    assert result["status"] == "COMPLETED"
    assert result["http_status"] == 200
    assert result["content_type"] == "application/zip"
    assert result["download_url"] == expected_url
    assert os.path.isfile(result["storage_path"])
    assert result["file_size"] > 0
    assert result["archive"]["valid"] is True
    stream_url = mock_http.stream.call_args.args[1]
    assert stream_url == expected_url
    auth_header = mock_http.stream.call_args.kwargs["headers"]["Authorization"]
    assert auth_header.startswith("Bearer ")


def test_verify_sentinel1_product_archive_rejects_non_zip(tmp_path):
    path = tmp_path / "not-a-product.bin"
    path.write_bytes(b"not a zip")
    result = CDSEClient.verify_sentinel1_product_archive(str(path))
    assert result["valid"] is False
    assert "ZIP" in result["reason"]
