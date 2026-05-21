from pathlib import Path

from ovs.paths import (
    OutputMode,
    archive_dir_for,
    move_video_to_archive,
    output_paths_for,
    should_skip,
)


def test_beside_mode_paths(tmp_path: Path):
    video = tmp_path / "rec.mov"
    video.touch()
    paths = output_paths_for(
        video,
        output_mode=OutputMode.BESIDE,
        output_dir=tmp_path / "unused",
        formats=["txt", "srt"],
    )
    assert paths["txt"] == tmp_path / "rec.txt"
    assert paths["srt"] == tmp_path / "rec.srt"


def test_archive_mode_paths(tmp_path: Path):
    video = tmp_path / "incoming" / "rec.mov"
    video.parent.mkdir(parents=True)
    video.touch()
    out_root = tmp_path / "Transcripts"
    paths = output_paths_for(
        video,
        output_mode=OutputMode.ARCHIVE,
        output_dir=out_root,
        formats=["vtt", "txt"],
    )
    assert paths["vtt"] == out_root / "rec" / "rec.vtt"
    assert paths["txt"] == out_root / "rec" / "rec.txt"


def test_archive_dir_collision(tmp_path: Path):
    out_root = tmp_path / "Transcripts"
    (out_root / "rec").mkdir(parents=True)
    video = tmp_path / "rec.mov"
    video.touch()
    folder = archive_dir_for(video, out_root)
    assert folder == out_root / "rec-2"


def test_move_video_to_archive(tmp_path: Path):
    video = tmp_path / "incoming" / "rec.mov"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"video")
    out_root = tmp_path / "Transcripts"
    paths = output_paths_for(
        video,
        output_mode=OutputMode.ARCHIVE,
        output_dir=out_root,
        formats=["vtt"],
    )
    paths["vtt"].parent.mkdir(parents=True, exist_ok=True)
    paths["vtt"].write_text("WEBVTT\n", encoding="utf-8")
    dest = move_video_to_archive(video, paths)
    assert dest == out_root / "rec" / "rec.mov"
    assert dest.is_file()
    assert not video.exists()


def test_should_skip_archive_when_complete(tmp_path: Path):
    out_root = tmp_path / "Transcripts"
    archive = out_root / "rec"
    archive.mkdir(parents=True)
    video = archive / "rec.mov"
    video.write_bytes(b"x")
    (archive / "rec.vtt").write_text("WEBVTT\n", encoding="utf-8")
    paths = output_paths_for(
        video,
        output_mode=OutputMode.ARCHIVE,
        output_dir=out_root,
        formats=["vtt"],
    )
    assert should_skip(
        paths,
        formats=["vtt"],
        video_path=video,
        output_mode=OutputMode.ARCHIVE,
    ) is True


def test_mirror_mode_paths(tmp_path: Path):
    root = tmp_path / "videos"
    out_root = tmp_path / "transcripts"
    video = root / "nested" / "rec.mov"
    video.parent.mkdir(parents=True)
    video.touch()
    paths = output_paths_for(
        video,
        output_mode=OutputMode.MIRROR,
        output_dir=out_root,
        formats=["txt"],
        mirror_root=root,
    )
    assert paths["txt"] == out_root / "nested" / "rec.txt"


def test_flat_mode_paths(tmp_path: Path):
    video = tmp_path / "nested" / "rec.mov"
    video.parent.mkdir(parents=True)
    video.touch()
    flat = tmp_path / "flat"
    paths = output_paths_for(
        video,
        output_mode=OutputMode.FLAT,
        output_dir=flat,
        formats=["vtt"],
    )
    assert paths["vtt"] == flat / "rec.vtt"


def test_should_skip_when_txt_and_srt_exist(tmp_path: Path):
    video = tmp_path / "rec.mov"
    video.touch()
    (tmp_path / "rec.txt").write_text("done")
    (tmp_path / "rec.srt").write_text("done")
    paths = output_paths_for(
        video,
        output_mode=OutputMode.BESIDE,
        output_dir=tmp_path,
        formats=["txt", "srt"],
    )
    assert should_skip(paths, formats=["txt", "srt"]) is True


def test_should_not_skip_with_force(tmp_path: Path):
    video = tmp_path / "rec.mov"
    video.touch()
    (tmp_path / "rec.txt").write_text("done")
    paths = output_paths_for(
        video,
        output_mode=OutputMode.BESIDE,
        output_dir=tmp_path,
        formats=["txt"],
    )
    assert should_skip(paths, formats=["txt"], force=True) is False
