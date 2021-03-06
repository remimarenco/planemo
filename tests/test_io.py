from .test_utils import io


def test_io_capture():
    with io.conditionally_captured_io(True, tee=False) as capture:
        io.warn("Problem...")
    assert capture[0]["data"] == "Problem..."

    with io.conditionally_captured_io(True, tee=False) as capture:
        io.shell("echo 'Problem...'")
    assert capture[0]["data"] == "echo 'Problem...'"
    assert capture[1]["data"] == "Problem..."

    with io.conditionally_captured_io(True, tee=False) as capture:
        io.communicate("echo 'Problem...'")
    assert capture[0]["data"] == "echo 'Problem...'"
    assert capture[1]["data"] == "Problem..."

    with io.conditionally_captured_io(False, tee=False) as capture:
        io.communicate("echo 'Test...'")

    assert capture is None
