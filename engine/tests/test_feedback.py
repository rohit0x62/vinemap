from vinemap.feedback import open_feedback


def test_open_feedback_builds_url():
    url = open_feedback("great tool", open_browser=False)
    assert "github.com" in url
    assert "great" in url
