from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tesla_dashcam.models.event import Event, Event_Metadata
from tesla_dashcam.models.video import Clip, Video_Metadata


class TestEventMetadata:
    def test_properties_roundtrip(self):
        t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
        md = Event_Metadata(
            reason="SENTRY",
            timestmp=t0,
            city="X",
            street="Y",
            longitude=1.2,
            latitude=3.4,
        )

        assert md.reason == "SENTRY"
        assert md.timestamp == t0
        assert md.city == "X"
        assert md.street == "Y"
        assert md.longitude == 1.2
        assert md.latitude == 3.4

        md.reason = "USER"
        md.city = "A"
        md.street = "B"
        md.longitude = 9.8
        md.latitude = 7.6
        assert (md.reason, md.city, md.street, md.longitude, md.latitude) == (
            "USER",
            "A",
            "B",
            9.8,
            7.6,
        )


class TestEvent:
    def test_camera_clip_tracking_is_set_like(self):
        e = Event(folder="f")
        assert e.has_camera_clip("front") is False

        e.add_camera_clip("front")
        e.add_camera_clip("front")
        assert e.has_camera_clip("front") is True

    def test_width_height_fall_back_to_max_clip_video_metadata(self):
        e = Event(folder="f")

        t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
        c1 = Clip(timestmp=t0)
        c2 = Clip(timestmp=t0 + timedelta(seconds=60))

        c1.video_metadata = Video_Metadata(filename="a.mp4", width=1280, height=960)
        c2.video_metadata = Video_Metadata(filename="b.mp4", width=1920, height=1080)

        e.set_clip(t0, c1)
        e.set_clip(t0 + timedelta(seconds=60), c2)

        assert e.width == 1920
        assert e.height == 1080
        assert e.ratio == 1920 / 1080

    def test_width_height_use_event_video_metadata_when_present(self):
        e = Event(folder="f")
        e.video_metadata = Video_Metadata(filename="merged.mp4", width=640, height=480)

        assert e.width == 640
        assert e.height == 480
        assert e.ratio == 640 / 480

    def test_template_returns_empty_for_none_or_empty_template(self):
        e = Event(folder="f")
        assert e.template(None, "%Y", {"movie_layout": "X"}) == ""
        assert e.template("", "%Y", {"movie_layout": "X"}) == ""

    def test_template_substitution_with_fixed_timezone(self, monkeypatch):
        # Make timezone deterministic
        monkeypatch.setattr(
            "tesla_dashcam.models.event.get_localzone", lambda: timezone.utc
        )

        e = Event(
            folder="f",
            event_metadata=Event_Metadata(
                city="C", street="S", reason="R", latitude=1.0, longitude=2.0
            ),
        )
        t0 = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        e.start_timestamp = t0
        e.end_timestamp = t0 + timedelta(seconds=10)

        out = e.template(
            template="{layout} {start_timestamp} {end_timestamp} {event_city} {event_reason}",
            timestamp_format="%Y-%m-%dT%H:%M:%SZ",
            video_settings={"movie_layout": "LAYOUT"},
        )

        assert out == "LAYOUT 2020-01-01T00:00:00Z 2020-01-01T00:00:10Z C R"

    def test_template_invalid_key_prints_and_falls_back_to_date_range(
        self, monkeypatch, capsys
    ):
        # Make timezone deterministic and timestamp prefix stable
        monkeypatch.setattr(
            "tesla_dashcam.models.event.get_localzone", lambda: timezone.utc
        )
        monkeypatch.setattr(
            "tesla_dashcam.models.event.get_current_timestamp", lambda: ""
        )

        e = Event(folder="f")
        e.start_timestamp = datetime(2020, 1, 1, tzinfo=timezone.utc)
        e.end_timestamp = datetime(2020, 1, 1, 0, 0, 1, tzinfo=timezone.utc)

        out = e.template(
            template="{does_not_exist}",
            timestamp_format="%Y",
            video_settings={"movie_layout": "LAYOUT"},
        )
        captured = capsys.readouterr().out

        assert out == "2020 - 2020"
        assert "Bad string format for merge template" in captured
        assert "does_not_exist" in captured
