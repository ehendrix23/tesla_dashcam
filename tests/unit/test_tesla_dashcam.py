from pathlib import Path
from types import SimpleNamespace

import pytest

from tesla_dashcam.tesla_dashcam import (
    FullScreen,
    Movie,
    create_movie,
    create_movie_ffmpeg,
    escape_drawtext_literals,
    get_metadata,
)


class TestDrawtextEscaping:
    def test_escapes_colons_outside_expansion(self):
        raw_text = "Countdown: %{pts\:hms\:603}"
        assert escape_drawtext_literals(raw_text) == r"Countdown\: %{pts\:hms\:603}"

    def test_keeps_colons_inside_expansion(self):
        raw_text = "%{pts\:localtime\:1234\:%a, %d %b %Y at %I:%M:%S%p}"
        assert escape_drawtext_literals(raw_text) == raw_text

    def test_does_not_double_escape(self):
        raw_text = r"Event\: %{pts\:hms\:10}"
        assert escape_drawtext_literals(raw_text) == raw_text

    def test_convert_timestamp(self):
        timestamp_format = "%a, %d %b %Y at %I:%M:%S%p"
        convert1 = escape_drawtext_literals(timestamp_format)
        assert convert1 == "%a, %d %b %Y at %I\:%M\:%S%p"
        pts_time = f"%{{pts\\:localtime\\:0\\:{convert1}}}"
        assert escape_drawtext_literals(pts_time) == pts_time


class TestEdgeCases:
    def test_create_movie_no_clips_returns_false(self):
        # Prepare minimal args; early return should only depend on movie.count
        movie = Movie()
        event_info = []
        video_settings = {
            "video_layout": SimpleNamespace(video_width=1280, video_height=960)
        }
        # Expectation: production behavior should signal failure on empty input
        result = create_movie(
            movie=movie,
            event_info=event_info,
            movie_filename="/tmp/output.mp4",
            video_settings=video_settings,
            chapter_offset=0,
            title_screen_map=False,
        )
        assert result is False

    def test_concat_joinfile_escapes_apostrophes(self, monkeypatch, tmp_path):
        from subprocess import CompletedProcess

        # Capture join file path written and prevent deletion
        removed_paths = []

        def fake_remove(path):
            removed_paths.append(path)

        monkeypatch.setattr("tesla_dashcam.tesla_dashcam.os.remove", fake_remove)

        # Stub subprocess.run to succeed without invoking ffmpeg
        def fake_run(cmd, capture_output=True, check=True, text=True):
            return CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        monkeypatch.setattr("tesla_dashcam.tesla_dashcam.run", fake_run)

        # Prepare inputs
        path_with_quote = tmp_path / "clip o'clock.mp4"
        path_with_quote.write_text("")

        file_content = [
            SimpleNamespace(filename=str(path_with_quote), width=1280, height=960)
        ]
        movie_scale = SimpleNamespace(width=1280, height=960)
        ffmpeg_params = []
        ffmpeg_meta = tmp_path / "meta.ffmetadata"
        ffmpeg_meta.write_text(";FFMETADATA1\n")
        ffmpeg_metadata = []
        video_settings = {
            "ffmpeg_exec": "ffmpeg",
            "ffmpeg_hwdev": [],
            "ffmpeg_hwout": [],
            "other_params": [],
        }

        # Execute
        create_movie_ffmpeg(
            movie_filename=str(tmp_path / "out.mp4"),
            video_settings=video_settings,
            movie_scale=movie_scale,
            ffmpeg_params=ffmpeg_params,
            complex_concat=False,
            file_content=file_content,
            ffmpeg_meta_filename=str(ffmpeg_meta),
            ffmpeg_metadata=ffmpeg_metadata,
        )

        # The join file should be the one attempted to be removed last
        assert removed_paths, "Expected a join file to be scheduled for deletion"
        joinfile = removed_paths[-1]
        content = Path(joinfile).read_text()
        # Expect proper escaping of inner apostrophes inside single-quoted path
        # ffmpeg concat syntax requires closing+escaped apostrophe+reopen i.e. '\'''
        assert "'\\''" in content, f"Join file not escaping apostrophes: {content}"

    def test_simple_concat_uses_stream_copy(self, monkeypatch, tmp_path):
        from subprocess import CompletedProcess

        captured_cmd = {"cmd": None}

        def fake_run(cmd, capture_output=True, check=True, text=True):
            captured_cmd["cmd"] = cmd
            return CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        monkeypatch.setattr("tesla_dashcam.tesla_dashcam.run", fake_run)

        fc = [SimpleNamespace(filename=str(tmp_path / "a.mp4"), width=1280, height=960)]
        (tmp_path / "a.mp4").write_text("")
        meta = tmp_path / "m.ffmetadata"
        meta.write_text(";FFMETADATA1\n")
        vs = {
            "ffmpeg_exec": "ffmpeg",
            "ffmpeg_hwdev": [],
            "ffmpeg_hwout": [],
            "other_params": [],
        }
        create_movie_ffmpeg(
            movie_filename=str(tmp_path / "out.mp4"),
            video_settings=vs,
            movie_scale=SimpleNamespace(width=1280, height=960),
            ffmpeg_params=[],
            complex_concat=False,
            file_content=fc,
            ffmpeg_meta_filename=str(meta),
            ffmpeg_metadata=[],
        )

        assert captured_cmd["cmd"] is not None
        # Expect stream copy for simple concat to avoid re-encoding
        assert "-c" in captured_cmd["cmd"] and "copy" in captured_cmd["cmd"], (
            captured_cmd["cmd"]
        )

    def test_complex_concat_includes_encoder_flags(self, monkeypatch, tmp_path):
        from subprocess import CompletedProcess

        captured_cmd = {"cmd": None}

        def fake_run(cmd, capture_output=True, check=True, text=True):
            captured_cmd["cmd"] = cmd
            return CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        monkeypatch.setattr("tesla_dashcam.tesla_dashcam.run", fake_run)

        # Two files same scale will still trigger complex when we force via flag
        fc = [
            SimpleNamespace(filename=str(tmp_path / "a.mp4"), width=1280, height=960),
            SimpleNamespace(filename=str(tmp_path / "b.mp4"), width=640, height=480),
        ]
        (tmp_path / "a.mp4").write_text("")
        (tmp_path / "b.mp4").write_text("")
        meta = tmp_path / "m.ffmetadata"
        meta.write_text(";FFMETADATA1\n")
        vs = {
            "ffmpeg_exec": "ffmpeg",
            "ffmpeg_hwdev": [],
            "ffmpeg_hwout": [],
            "other_params": ["-preset", "medium", "-crf", "23", "-c:v", "libx264"],
        }
        create_movie_ffmpeg(
            movie_filename=str(tmp_path / "out.mp4"),
            video_settings=vs,
            movie_scale=SimpleNamespace(width=1280, height=960),
            ffmpeg_params=[],
            complex_concat=True,
            file_content=fc,
            ffmpeg_meta_filename=str(meta),
            ffmpeg_metadata=[],
        )

        assert captured_cmd["cmd"] is not None
        # Expect encoder flags to be present for complex concat
        assert "-crf" in captured_cmd["cmd"] and "-c:v" in captured_cmd["cmd"], (
            captured_cmd["cmd"]
        )

    def test_complex_concat_maps_metadata_from_ffmetadata_input(
        self, monkeypatch, tmp_path
    ):
        from subprocess import CompletedProcess

        captured_cmd = {"cmd": None}

        def fake_run(cmd, capture_output=True, check=True, text=True):
            captured_cmd["cmd"] = cmd
            return CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        monkeypatch.setattr("tesla_dashcam.tesla_dashcam.run", fake_run)

        # Two inputs -> ffmetadata index should equal len(file_content)
        fc = [
            SimpleNamespace(filename=str(tmp_path / "a.mp4"), width=1280, height=960),
            SimpleNamespace(filename=str(tmp_path / "b.mp4"), width=640, height=480),
        ]
        (tmp_path / "a.mp4").write_text("")
        (tmp_path / "b.mp4").write_text("")
        meta = tmp_path / "m.ffmetadata"
        meta.write_text(";FFMETADATA1\n")
        vs = {
            "ffmpeg_exec": "ffmpeg",
            "ffmpeg_hwdev": [],
            "ffmpeg_hwout": [],
            "other_params": [],
        }
        create_movie_ffmpeg(
            movie_filename=str(tmp_path / "out.mp4"),
            video_settings=vs,
            movie_scale=SimpleNamespace(width=1280, height=960),
            ffmpeg_params=[],
            complex_concat=True,
            file_content=fc,
            ffmpeg_meta_filename=str(meta),
            ffmpeg_metadata=[],
        )

        assert captured_cmd["cmd"] is not None
        # Find the index of -map_metadata and read the following value
        cmd = captured_cmd["cmd"]
        idx = cmd.index("-map_metadata")
        meta_idx = int(cmd[idx + 1])
        assert meta_idx == len(fc), (
            f"Expected map_metadata to reference ffmetadata input ({len(fc)}), got {meta_idx}. Cmd: {cmd}"
        )

    def test_get_metadata_parses_fractional_seconds(self, monkeypatch, tmp_path):
        from subprocess import CompletedProcess

        # Create a temp file so get_metadata includes it
        f = tmp_path / "clip.mp4"
        f.write_text("")

        # Simulate ffmpeg stderr output with fractional seconds
        stderr = "\n".join(
            [
                "Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'clip.mp4':",
                "  Duration: 00:01:02.041, start: 0.000000, bitrate: 1234 kb/s",
                "    Stream #0:0: Video: h264 (High), yuv420p, 1280x960 [SAR 1:1 DAR 4:3], 29.97 fps, 29.97 tbr, 30k tbn, 59.94 tbc (default)",
            ]
        )

        def fake_run(cmd, capture_output=True, text=True, check=False):
            return CompletedProcess(args=cmd, returncode=0, stdout="", stderr=stderr)

        monkeypatch.setattr("tesla_dashcam.tesla_dashcam.run", fake_run)
        # Ensure os.path.isfile returns True for our temp file path
        monkeypatch.setattr(
            "tesla_dashcam.tesla_dashcam.os.path.isfile", lambda p: True
        )

        md = get_metadata("ffmpeg", [str(f)])
        assert md and md[0].duration is not None
        assert abs(md[0].duration - 62.041) < 1e-6
        # Verify fractional FPS is preserved
        assert md[0].fps is not None
        assert abs(md[0].fps - 29.97) < 1e-6

    def test_scale_setter_handles_malformed_resolution(self):
        """Test that scale setter handles malformed resolutions like '1920x' or 'x1080'."""
        layout = FullScreen()

        # Test missing height
        with pytest.raises(ValueError, match="Invalid resolution format"):
            layout.scale = "1920x"

        # Test missing width
        with pytest.raises(ValueError, match="Invalid resolution format"):
            layout.scale = "x1080"

        # Test empty string
        with pytest.raises(ValueError, match="Invalid resolution format"):
            layout.scale = "x"

        # Test completely malformed
        with pytest.raises(ValueError):
            layout.scale = "not_a_number"

        # Test valid formats work
        layout.scale = "1920x1080"
        assert layout.cameras("front").width == 1920
        assert layout.cameras("front").height == 1080

        layout.scale = "0.5"
        assert layout.cameras("front")._scale == 0.5

    def test_get_metadata_empty_list_safe(self, monkeypatch):
        """Test that get_metadata returns empty list for nonexistent files."""

        def fake_run(cmd, **kwargs):
            return SimpleNamespace(returncode=0, stderr="")

        monkeypatch.setattr("tesla_dashcam.tesla_dashcam.run", fake_run)
        monkeypatch.setattr(
            "tesla_dashcam.tesla_dashcam.os.path.isfile", lambda p: False
        )

        metadata = get_metadata("ffmpeg", ["/nonexistent/file.mp4"])
        assert metadata == []
