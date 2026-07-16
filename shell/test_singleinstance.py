import threading
import time
import singleinstance as si

PORT = 51999  # 테스트 전용 포트


def test_server_collects_sibling_files():
    result = {}

    def server():
        result["files"] = si.coalesce(["/a.jpg"], port=PORT, window=0.6)

    t = threading.Thread(target=server)
    t.start()
    time.sleep(0.15)  # 서버가 바인드할 시간
    # 형제 두 개
    assert si.coalesce(["/b.jpg"], port=PORT, window=0.6) is None
    assert si.coalesce(["/c.jpg"], port=PORT, window=0.6) is None
    t.join(2.0)
    assert set(result["files"]) == {"/a.jpg", "/b.jpg", "/c.jpg"}


def test_no_server_returns_own_when_connect_fails():
    # 아무도 안 여는 포트로 connect 실패 -> 폴백(자기 파일)
    files = si.coalesce(["/solo.jpg"], port=51998, window=0.2)
    # 서버로 바인드 성공하면 리스트, 형제면 None. 단독 실행이므로 리스트여야 함.
    assert files == ["/solo.jpg"]
