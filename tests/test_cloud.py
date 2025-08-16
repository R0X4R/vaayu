from vaayu.cloud import detect_scheme, is_cloud_uri


def test_cloud_detect():
    assert detect_scheme("s3://bucket/key") == "s3"
    assert detect_scheme("gcs://bucket/key") == "gcs"
    assert detect_scheme("ftp://host/file") == "ftp"
    assert detect_scheme("/local/path") == ""


def test_cloud_is_cloud_uri():
    assert is_cloud_uri("s3://bucket/key")
    assert not is_cloud_uri("/local")
