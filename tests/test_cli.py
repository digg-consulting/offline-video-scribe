from ovs.cli import resolve_transcribe_path


def test_resolve_transcribe_path_joins_shell_split_parts(tmp_path):
    video = tmp_path / "2026-05-20 13-00-53.mov"
    video.touch()
    parent = str(tmp_path)
    resolved = resolve_transcribe_path([parent, "2026-05-20 13-00-53.mov"])
    assert resolved == video.resolve()


def test_resolve_transcribe_path_single_quoted_part(tmp_path):
    video = tmp_path / "recording.mov"
    video.touch()
    resolved = resolve_transcribe_path([str(video)])
    assert resolved == video.resolve()
