from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tesla_dashcam.models.event import Event
from tesla_dashcam.models.movie import Movie
from tesla_dashcam.models.video import Clip, Video_Metadata


class TestMovie:
    def test_set_event_keys_by_folder_or_filename(self):
        m = Movie()

        e1 = Event(folder="folder-a")
        e2 = Event(folder="folder-b", filename="file-b.mp4")

        m.set_event(e1)
        m.set_event(e2)

        assert m.event("folder-a") is e1
        assert m.event("file-b.mp4") is e2
        assert m.count == 2

    def test_sorted_orders_by_start_timestamp(self):
        m = Movie()
        t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)

        e_late = Event(folder="late")
        e_late.start_timestamp = t0 + timedelta(seconds=10)

        e_early = Event(folder="early")
        e_early.start_timestamp = t0 + timedelta(seconds=1)

        m.set_event(e_late)
        m.set_event(e_early)

        assert m.sorted == ["early", "late"]
        assert m.first_item is e_early

    def test_count_clips_sums_event_counts(self):
        m = Movie()
        t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)

        e1 = Event(folder="a")
        e1.set_clip(t0, Clip(timestmp=t0))

        e2 = Event(folder="b")
        e2.set_clip(t0, Clip(timestmp=t0))
        e2.set_clip(
            t0 + timedelta(seconds=60), Clip(timestmp=t0 + timedelta(seconds=60))
        )

        m.set_event(e1)
        m.set_event(e2)

        assert e1.count == 1
        assert e2.count == 2
        assert m.count_clips == 3

    def test_width_height_fall_back_to_max_event_video_metadata(self):
        m = Movie()

        e1 = Event(folder="a")
        e1.video_metadata = Video_Metadata(filename="a.mp4", width=1280, height=960)

        e2 = Event(folder="b")
        e2.video_metadata = Video_Metadata(filename="b.mp4", width=1920, height=1080)

        m.set_event(e1)
        m.set_event(e2)

        assert m.width == 1920
        assert m.height == 1080
        assert m.ratio == pytest.approx(1920 / 1080)

    def test_width_height_use_movie_video_metadata_when_present(self):
        m = Movie()
        m.video_metadata = Video_Metadata(filename="m.mp4", width=640, height=480)

        assert m.width == 640
        assert m.height == 480
        assert m.ratio == 640 / 480
