from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tesla_dashcam.models.video import Camera_Clip, Chapter, Clip, Video_Metadata


class TestChapter:
    def test_properties_roundtrip(self):
        ch = Chapter(start=1.0, end=2.5, title="A")
        assert ch.start == 1.0
        assert ch.end == 2.5
        assert ch.title == "A"

        ch.start = 3.0
        ch.end = 4.0
        ch.title = "B"
        assert (ch.start, ch.end, ch.title) == (3.0, 4.0, "B")


class TestVideoMetadata:
    def test_ratio_defaults_to_4_3_when_missing_dimensions(self):
        md = Video_Metadata(filename="x.mp4")
        assert md.ratio == 4 / 3

    def test_ratio_uses_width_height_when_present(self):
        md = Video_Metadata(filename="x.mp4", width=1920, height=1080)
        assert md.ratio == 1920 / 1080

    def test_add_chapter_deduplicates_by_identity(self):
        md = Video_Metadata(filename="x.mp4")
        ch = Chapter(start=0.0, end=1.0, title="c")
        md.add_chapter(ch)
        md.add_chapter(ch)
        assert md.chapters is not None
        assert len(md.chapters) == 1

    def test_include_property_is_always_true_current_behavior(self):
        # NOTE: Current implementation returns self._include or True
        # which evaluates to True regardless of the stored value.
        md = Video_Metadata(filename="x.mp4", include=False)
        assert md.include is True
        md.include = False
        assert md.include is True


class TestCameraClip:
    def test_end_timestamp_adds_duration(self):
        t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
        c = Camera_Clip(filename="a.mp4", timestmp=t0, duration=2.5, include=True)
        assert c.start_timestamp == t0
        assert c.end_timestamp == t0 + timedelta(seconds=2.5)

    def test_dimensions_from_video_metadata(self):
        t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
        md = Video_Metadata(filename="a.mp4", width=1280, height=960)
        c = Camera_Clip(filename="a.mp4", timestmp=t0, video_metadata=md)
        assert c.width == 1280
        assert c.height == 960
        assert c.ratio == 1280 / 960


class TestClip:
    def test_start_timestamp_prefers_earliest_included_camera(self):
        t0 = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        clip = Clip(timestmp=t0)

        # earlier but excluded
        left = Camera_Clip(
            filename="left.mp4",
            timestmp=t0 + timedelta(seconds=1),
            duration=10,
            include=False,
        )
        # later but included
        front = Camera_Clip(
            filename="front.mp4",
            timestmp=t0 + timedelta(seconds=2),
            duration=10,
            include=True,
        )

        clip.set_camera("left", left)
        clip.set_camera("front", front)

        assert clip.start_timestamp == front.start_timestamp

    def test_start_timestamp_falls_back_to_clip_timestamp_if_none_included(self):
        t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
        clip = Clip(timestmp=t0)
        clip.set_camera(
            "front",
            Camera_Clip("front.mp4", timestmp=t0 + timedelta(seconds=2), include=False),
        )
        assert clip.start_timestamp == t0

    def test_end_timestamp_is_max_end_of_included_cameras(self):
        t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
        clip = Clip(timestmp=t0)

        c1 = Camera_Clip("a.mp4", timestmp=t0, duration=2, include=True)
        c2 = Camera_Clip(
            "b.mp4", timestmp=t0 + timedelta(seconds=1), duration=10, include=True
        )
        c3 = Camera_Clip(
            "c.mp4", timestmp=t0 + timedelta(seconds=100), duration=1, include=False
        )

        clip.set_camera("a", c1)
        clip.set_camera("b", c2)
        clip.set_camera("c", c3)

        assert clip.end_timestamp == c2.end_timestamp
        assert clip.duration == pytest.approx(
            (c2.end_timestamp - clip.start_timestamp).total_seconds()
        )

    def test_sorted_orders_cameras_by_start_timestamp(self):
        t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
        clip = Clip(timestmp=t0)

        clip.set_camera("b", Camera_Clip("b.mp4", timestmp=t0 + timedelta(seconds=2)))
        clip.set_camera("a", Camera_Clip("a.mp4", timestmp=t0 + timedelta(seconds=1)))

        assert clip.sorted == ["a", "b"]
