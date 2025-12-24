from unittest.mock import MagicMock, Mock, PropertyMock

import pytest

from tesla_dashcam.tesla_dashcam import (
    FFMPEG_LEFT_PERSPECTIVE,
    FFMPEG_RIGHT_PERSPECTIVE,
    HALIGN,
    VALIGN,
    Camera,
    Font,
    MovieLayout,
)


class TestCamera:
    @pytest.fixture
    def layout(self):
        layout = MagicMock(spec=MovieLayout)
        type(layout).event = PropertyMock(return_value=None)

        return layout

    @pytest.fixture
    def camera(self, layout):
        return Camera(layout, "front")

    def test_camera_init(self, camera):
        """Test camera initialization with default values"""
        assert camera.camera == "front"
        assert camera.include is True
        assert camera.width == 1280
        assert camera.height == 960
        assert camera.xpos == 0
        assert camera.ypos == 0
        assert camera.scale == 1
        assert camera.options == ""

    def test_camera_setters(self, camera, monkeypatch):
        """Test setting camera properties"""
        camera.camera = "rear"
        assert camera.camera == "rear"

        camera.scale = 1 / 2
        assert camera.scale == 0.5
        assert camera.width == 640  # Default width
        assert camera.height == 480  # Default height

        camera.scale = 1
        camera.width = 320
        assert camera.width == 320
        camera.height = 240
        assert camera.height == 240

        camera.xpos = 100
        assert camera.xpos == 100
        camera.xpos = None
        camera.ypos = 100
        assert camera.ypos == 100
        camera.ypos = None

    def test_camera_excluded(self, camera, monkeypatch):
        """Test that values return 0 when cameras is excluded."""
        camera.include = False
        camera.xpos = 100
        camera.ypos = 100

        assert camera.include is False
        assert camera.width == 0
        assert camera.height == 0
        assert camera.xpos == 0
        assert camera.ypos == 0

    def test_camera_override(self, camera, monkeypatch):
        """Test setting camera properties"""
        setattr(camera.layout, f"{camera.camera}_width", Mock(return_value=2560))
        setattr(camera.layout, f"{camera.camera}_height", Mock(return_value=1440))
        setattr(camera.layout, f"{camera.camera}_xpos", Mock(return_value=320))
        setattr(camera.layout, f"{camera.camera}_ypos", Mock(return_value=240))
        camera.include = False
        assert camera.include is False
        assert camera.width == 0
        assert camera.height == 0
        assert camera.xpos == 0
        assert camera.ypos == 0

        camera.include = True
        assert camera.width == 2560
        assert camera.height == 1440
        assert camera.xpos == 320
        assert camera.ypos == 240


class TestMovieLayout:
    @pytest.fixture
    def layout(self):
        return MovieLayout()

    def test_movielayout_init(self, layout):
        """Test MovieLayout initialization"""
        assert isinstance(layout, MovieLayout)
        # Test cameras dictionary has exact set of keys
        assert layout.cameras("front")
        assert layout.cameras("left")
        assert layout.cameras("right")
        assert layout.cameras("rear")
        assert layout.cameras("left_pillar")
        assert layout.cameras("right_pillar")

        expected_clip_order = [
            "left",
            "right",
            "front",
            "rear",
            "left_pillar",
            "right_pillar",
        ]

        assert layout.clip_order == expected_clip_order

        assert isinstance(layout.font, Font)
        assert layout.font.halign == HALIGN["CENTER"]
        assert layout.font.valign == VALIGN["BOTTOM"]

        assert layout.swap_left_right is False
        assert layout.swap_front_rear is False
        assert layout.perspective is False

        assert layout.video_width == 2560
        assert layout.video_height == 2880

    def test_movielayout_setters(self, layout, monkeypatch):
        """Test MovieLayout property setters"""
        layout = MovieLayout()

        expected_clip_order = set(
            [
                "left",
                "right",
                "front",
                "rear",
                "left_pillar",
                "right_pillar",
            ]
        )
        # Confirm all cameras are included in the clip order
        layout.clip_order = []
        assert set(layout.clip_order) == expected_clip_order
        # Only allowed cameras are to be included
        layout.clip_order = ["test"]
        assert set(layout.clip_order) == expected_clip_order

        # Test order provided is kept.
        expected_clip_order = [
            "left_pillar",
            "left",
            "front",
            "right_pillar",
            "rear",
            "right",
        ]

        layout.clip_order = expected_clip_order
        assert set(layout.clip_order) == set(expected_clip_order)

        layout.swap_front_rear = True
        assert layout.swap_front_rear is True
        layout.swap_left_right = True
        assert layout.swap_left_right is True

        layout.scale = 0.5
        assert layout.cameras("front").scale == 0.5
        assert layout.cameras("left").scale == 0.5
        assert layout.cameras("right").scale == 0.5
        assert layout.cameras("rear").scale == 0.5
        assert layout.cameras("left_pillar").scale == 0.5
        assert layout.cameras("right_pillar").scale == 0.5
        assert layout.video_width == 1280
        assert layout.video_height == 1440
        assert layout.center_xpos == 640
        assert layout.center_ypos == 720
        assert layout.scale == 1.5

        layout.perspective = True
        assert layout.perspective is True
        assert layout.cameras("left").options == FFMPEG_LEFT_PERSPECTIVE
        assert layout.cameras("right").options == FFMPEG_RIGHT_PERSPECTIVE
        assert layout.cameras("left_pillar").options == FFMPEG_LEFT_PERSPECTIVE
        assert layout.cameras("right_pillar").options == FFMPEG_RIGHT_PERSPECTIVE

        assert layout.video_width == 1280
        assert layout.video_height == 1920
        assert layout.center_xpos == 640
        assert layout.center_ypos == 960
