from unittest.mock import MagicMock, Mock

import pytest

from tesla_dashcam.tesla_dashcam import (
    FFMPEG_LEFT_PERSPECTIVE,
    FFMPEG_RIGHT_PERSPECTIVE,
    HALIGN,
    VALIGN,
    Camera,
    Cross,
    Diamond,
    Font,
    FullScreen,
    MovieLayout,
    WideScreen,
)


class TestCamera:
    @pytest.fixture
    def layout(self):
        layout = MagicMock(spec=MovieLayout)

        return layout

    @pytest.fixture
    def camera(self, layout):
        return Camera(layout, "front")

    def test_camera_init(self, camera):
        """Test camera initialization with default values"""
        assert camera.camera == "front"
        assert camera.include is True
        assert camera.width == 0
        assert camera.height == 0
        assert camera.xpos == 0
        assert camera.ypos == 0
        assert camera.scale == 0
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

        camera.include = False
        assert camera.include is False
        assert camera.width == 0
        assert camera.height == 0

        setattr(camera.layout, f"_{camera.camera}_width", Mock(return_value=2560))
        assert camera.width == 2560
        setattr(camera.layout, f"_{camera.camera}_height", Mock(return_value=1440))
        assert camera.height == 1440

        camera.include = True

        setattr(camera.layout, f"_{camera.camera}_xpos", Mock(return_value=320))
        assert camera.xpos == 320
        setattr(camera.layout, f"_{camera.camera}_ypos", Mock(return_value=240))
        assert camera.ypos == 240

        camera.xpos = 100
        assert camera.xpos == 100
        camera.xpos = None
        camera.ypos = 100
        assert camera.ypos == 100
        camera.ypos = None


class TestMovieLayout:
    @pytest.fixture
    def layout(self):
        return MovieLayout()

    def test_movielayout_init(self, layout):
        """Test MovieLayout initialization"""
        assert isinstance(layout, MovieLayout)
        # Test cameras dictionary has exact set of keys
        expected_cameras = {
            "front",
            "left",
            "right",
            "rear",
            "left_pillar",
            "right_pillar",
        }
        assert layout.cameras("").keys() == expected_cameras

        # Test clip order (assuming this is a list property)
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

        assert layout.video_width == 0
        assert layout.video_height == 0

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


class TestFullScreen:
    @pytest.fixture
    def layout(self):
        return FullScreen()

    def test_init(self, layout):
        """Test FullScreen initialization"""
        assert layout.scale == 1.5

    def test_default(self, layout):
        """Test video dimensions with default camera sizes"""
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("front").xpos == 640
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("right_pillar").xpos == 1280
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 480
        assert layout.cameras("rear").xpos == 640
        assert layout.cameras("rear").ypos == 480
        assert layout.cameras("right").xpos == 1280
        assert layout.cameras("right").ypos == 480
        assert layout.video_width == 1920
        assert layout.video_height == 960

    def test_excluded_cameras_top_row(self, layout):
        """Test video dimensions with cameras excluded in top row"""
        layout.cameras("left_pillar").include = False
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("front").xpos == 320
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("right_pillar").xpos == 960
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 480
        assert layout.cameras("rear").xpos == 640
        assert layout.cameras("rear").ypos == 480
        assert layout.cameras("right").xpos == 1280
        assert layout.cameras("right").ypos == 480
        assert layout.video_width == 1920
        assert layout.video_height == 960

        layout.cameras("front").include = False
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("front").xpos == 0
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("right_pillar").xpos == 640
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 480
        assert layout.cameras("rear").xpos == 640
        assert layout.cameras("rear").ypos == 480
        assert layout.cameras("right").xpos == 1280
        assert layout.cameras("right").ypos == 480
        assert layout.video_width == 1920
        assert layout.video_height == 960

        layout.cameras("left_pillar").include = True
        assert layout.cameras("left_pillar").xpos == 320
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("front").xpos == 0
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("right_pillar").xpos == 960
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 480
        assert layout.cameras("rear").xpos == 640
        assert layout.cameras("rear").ypos == 480
        assert layout.cameras("right").xpos == 1280
        assert layout.cameras("right").ypos == 480
        assert layout.video_width == 1920
        assert layout.video_height == 960

        layout.cameras("left_pillar").include = False
        layout.cameras("right_pillar").include = False
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("front").xpos == 0
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("right_pillar").xpos == 0
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 0
        assert layout.cameras("rear").xpos == 640
        assert layout.cameras("rear").ypos == 0
        assert layout.cameras("right").xpos == 1280
        assert layout.cameras("right").ypos == 0
        assert layout.video_width == 1920
        assert layout.video_height == 480
        assert layout.scale == 0.75

    def test_excluded_cameras_bottom_row(self, layout):
        """Test video dimensions with cameras excluded in bottom row"""
        layout.cameras("left").include = False
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("front").xpos == 640
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("right_pillar").xpos == 1280
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 0
        assert layout.cameras("rear").xpos == 320
        assert layout.cameras("rear").ypos == 480
        assert layout.cameras("right").xpos == 960
        assert layout.cameras("right").ypos == 480
        assert layout.video_width == 1920
        assert layout.video_height == 960

        layout.cameras("rear").include = False
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("front").xpos == 640
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("right_pillar").xpos == 1280
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 0
        assert layout.cameras("rear").xpos == 0
        assert layout.cameras("rear").ypos == 0
        assert layout.cameras("right").xpos == 640
        assert layout.cameras("right").ypos == 480
        assert layout.video_width == 1920
        assert layout.video_height == 960

        layout.cameras("left").include = True
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("front").xpos == 640
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("right_pillar").xpos == 1280
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 320
        assert layout.cameras("left").ypos == 480
        assert layout.cameras("rear").xpos == 0
        assert layout.cameras("rear").ypos == 0
        assert layout.cameras("right").xpos == 960
        assert layout.cameras("right").ypos == 480
        assert layout.video_width == 1920
        assert layout.video_height == 960

        layout.cameras("left").include = False
        layout.cameras("right").include = False
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("front").xpos == 640
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("right_pillar").xpos == 1280
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 0
        assert layout.cameras("rear").xpos == 0
        assert layout.cameras("rear").ypos == 0
        assert layout.cameras("right").xpos == 0
        assert layout.cameras("right").ypos == 0
        assert layout.video_width == 1920
        assert layout.video_height == 480
        assert layout.scale == 0.75

    def test_scaling_cameras_top_row(self, layout):
        """Test video dimensions with cameras scaled in top row"""
        layout.cameras("left_pillar").scale = 1
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("left_pillar").width == 1280
        assert layout.cameras("left_pillar").height == 960
        assert layout.cameras("front").xpos == 1280
        assert layout.cameras("front").ypos == 240
        assert layout.cameras("right_pillar").xpos == 1920
        assert layout.cameras("right_pillar").ypos == 240
        assert layout.cameras("left").xpos == 320
        assert layout.cameras("left").ypos == 960
        assert layout.cameras("rear").xpos == 960
        assert layout.cameras("rear").ypos == 960
        assert layout.cameras("right").xpos == 1600
        assert layout.cameras("right").ypos == 960
        assert layout.video_width == 2560
        assert layout.video_height == 1440
        assert layout.scale == 3

        layout.cameras("left_pillar").scale = 0.5
        layout.cameras("front").scale = 1
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 240
        assert layout.cameras("front").xpos == 640
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("right_pillar").xpos == 1920
        assert layout.cameras("right_pillar").ypos == 240
        assert layout.cameras("left").xpos == 320
        assert layout.cameras("left").ypos == 960
        assert layout.cameras("rear").xpos == 960
        assert layout.cameras("rear").ypos == 960
        assert layout.cameras("right").xpos == 1600
        assert layout.cameras("right").ypos == 960
        assert layout.video_width == 2560
        assert layout.video_height == 1440
        assert layout.scale == 3

        layout.cameras("front").scale = 0.5
        layout.cameras("right_pillar").scale = 1
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 240
        assert layout.cameras("front").xpos == 640
        assert layout.cameras("front").ypos == 240
        assert layout.cameras("right_pillar").xpos == 1280
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 320
        assert layout.cameras("left").ypos == 960
        assert layout.cameras("rear").xpos == 960
        assert layout.cameras("rear").ypos == 960
        assert layout.cameras("right").xpos == 1600
        assert layout.cameras("right").ypos == 960
        assert layout.video_width == 2560
        assert layout.video_height == 1440
        assert layout.scale == 3

    def test_scaling_cameras_bottom_row(self, layout):
        """Test video dimensions with cameras scaled in bottom row"""
        layout.cameras("left").scale = 1
        assert layout.cameras("left_pillar").xpos == 320
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("front").xpos == 960
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("right_pillar").xpos == 1600
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 480
        assert layout.cameras("rear").xpos == 1280
        assert layout.cameras("rear").ypos == 720
        assert layout.cameras("right").xpos == 1920
        assert layout.cameras("right").ypos == 720
        assert layout.video_width == 2560
        assert layout.video_height == 1440
        assert layout.scale == 3

        layout.cameras("left").scale = 0.5
        layout.cameras("rear").scale = 1
        assert layout.cameras("left_pillar").xpos == 320
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("front").xpos == 960
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("right_pillar").xpos == 1600
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 720
        assert layout.cameras("rear").xpos == 640
        assert layout.cameras("rear").ypos == 480
        assert layout.cameras("right").xpos == 1920
        assert layout.cameras("right").ypos == 720
        assert layout.video_width == 2560
        assert layout.video_height == 1440
        assert layout.scale == 3

        layout.cameras("rear").scale = 0.5
        layout.cameras("right").scale = 1
        assert layout.cameras("left_pillar").xpos == 320
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("front").xpos == 960
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("right_pillar").xpos == 1600
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 720
        assert layout.cameras("rear").xpos == 640
        assert layout.cameras("rear").ypos == 720
        assert layout.cameras("right").xpos == 1280
        assert layout.cameras("right").ypos == 480
        assert layout.video_width == 2560
        assert layout.video_height == 1440
        assert layout.scale == 3


class TestWideScreen:
    @pytest.fixture
    def layout(self):
        return WideScreen()

    def test_init(self, layout):
        """Test WideScreen initialization"""
        assert layout.scale == 1.5

    def test_default(self, layout):
        """Test video dimensions with default camera sizes"""
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("front").xpos == 640
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("right_pillar").xpos == 1280
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 480
        assert layout.cameras("rear").xpos == 640
        assert layout.cameras("rear").ypos == 480
        assert layout.cameras("right").xpos == 1280
        assert layout.cameras("right").ypos == 480
        assert layout.video_width == 1920
        assert layout.video_height == 960

    def test_front_widescreen(self, layout):
        """Test video dimensions with front camera widescreen"""
        layout.cameras("left").scale = 1
        layout.cameras("rear").scale = 1
        layout.cameras("right").scale = 1
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("front").xpos == 640
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("front").width == 2560
        assert layout.cameras("right_pillar").xpos == 3200
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 480
        assert layout.cameras("rear").xpos == 1280
        assert layout.cameras("rear").ypos == 480
        assert layout.cameras("right").xpos == 2560
        assert layout.cameras("right").ypos == 480
        assert layout.video_width == 3840
        assert layout.video_height == 1440
        assert layout.scale == 4.5

    def test_rear_widescreen(self, layout):
        """Test video dimensions with rear camera widescreen"""
        layout.cameras("left_pillar").scale = 1
        layout.cameras("front").scale = 1
        layout.cameras("right_pillar").scale = 1
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("front").xpos == 1280
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("right_pillar").xpos == 2560
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 960
        assert layout.cameras("rear").xpos == 640
        assert layout.cameras("rear").ypos == 960
        assert layout.cameras("rear").width == 2560
        assert layout.cameras("right").xpos == 3200
        assert layout.cameras("right").ypos == 960
        assert layout.video_width == 3840
        assert layout.video_height == 1440
        assert layout.scale == 4.5


class TestCross:
    @pytest.fixture
    def layout(self):
        return Cross()

    def test_init(self, layout):
        """Test Cross initialization"""
        assert layout.scale == 2

    def test_default(self, layout):
        """Test video dimensions with default camera sizes"""
        assert layout.cameras("front").xpos == 320
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 480
        assert layout.cameras("right_pillar").xpos == 640
        assert layout.cameras("right_pillar").ypos == 480
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 960
        assert layout.cameras("right").xpos == 640
        assert layout.cameras("right").ypos == 960
        assert layout.cameras("rear").xpos == 320
        assert layout.cameras("rear").ypos == 1440
        assert layout.video_width == 1280
        assert layout.video_height == 1920

    def test_excluded_rows(self, layout):
        """Test video dimensions with default camera sizes"""
        layout.cameras("front").include = False
        assert layout.cameras("front").xpos == 0
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("right_pillar").xpos == 640
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 480
        assert layout.cameras("right").xpos == 640
        assert layout.cameras("right").ypos == 480
        assert layout.cameras("rear").xpos == 320
        assert layout.cameras("rear").ypos == 960
        assert layout.video_width == 1280
        assert layout.video_height == 1440

        layout.cameras("front").include = True
        layout.cameras("left_pillar").include = False
        layout.cameras("right_pillar").include = False
        assert layout.cameras("front").xpos == 320
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("right_pillar").xpos == 0
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 480
        assert layout.cameras("right").xpos == 640
        assert layout.cameras("right").ypos == 480
        assert layout.cameras("rear").xpos == 320
        assert layout.cameras("rear").ypos == 960
        assert layout.video_width == 1280
        assert layout.video_height == 1440

        layout.cameras("left_pillar").include = True
        layout.cameras("right_pillar").include = True
        layout.cameras("left").include = False
        layout.cameras("right").include = False
        assert layout.cameras("front").xpos == 320
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 480
        assert layout.cameras("right_pillar").xpos == 640
        assert layout.cameras("right_pillar").ypos == 480
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 0
        assert layout.cameras("right").xpos == 0
        assert layout.cameras("right").ypos == 0
        assert layout.cameras("rear").xpos == 320
        assert layout.cameras("rear").ypos == 960
        assert layout.video_width == 1280
        assert layout.video_height == 1440

    def test_scaling_rows(self, layout):
        """Test video dimensions with default camera sizes"""
        layout.cameras("front").scale = 2
        assert layout.cameras("front").xpos == 0
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("front").width == 2560
        assert layout.cameras("front").height == 1920
        assert layout.cameras("left_pillar").xpos == 640
        assert layout.cameras("left_pillar").ypos == 1920
        assert layout.cameras("right_pillar").xpos == 1280
        assert layout.cameras("right_pillar").ypos == 1920
        assert layout.cameras("left").xpos == 640
        assert layout.cameras("left").ypos == 2400
        assert layout.cameras("right").xpos == 1280
        assert layout.cameras("right").ypos == 2400
        assert layout.cameras("rear").xpos == 960
        assert layout.cameras("rear").ypos == 2880
        assert layout.video_width == 2560
        assert layout.video_height == 3360

        layout.cameras("front").scale = 1 / 2
        layout.cameras("left_pillar").scale = 1
        assert layout.cameras("front").xpos == 640
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 480
        assert layout.cameras("left_pillar").width == 1280
        assert layout.cameras("left_pillar").height == 960
        assert layout.cameras("right_pillar").xpos == 1280
        assert layout.cameras("right_pillar").ypos == 720
        assert layout.cameras("left").xpos == 320
        assert layout.cameras("left").ypos == 1440
        assert layout.cameras("right").xpos == 960
        assert layout.cameras("right").ypos == 1440
        assert layout.cameras("rear").xpos == 640
        assert layout.cameras("rear").ypos == 1920
        assert layout.video_width == 1920
        assert layout.video_height == 2400

        layout.cameras("left_pillar").scale = 1 / 2
        layout.cameras("right").scale = 1
        assert layout.cameras("front").xpos == 640
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("left_pillar").xpos == 320
        assert layout.cameras("left_pillar").ypos == 480
        assert layout.cameras("right_pillar").xpos == 960
        assert layout.cameras("right_pillar").ypos == 480
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 1200
        assert layout.cameras("right").xpos == 640
        assert layout.cameras("right").ypos == 960
        assert layout.cameras("right").width == 1280
        assert layout.cameras("right").height == 960
        assert layout.cameras("rear").xpos == 640
        assert layout.cameras("rear").ypos == 1920
        assert layout.video_width == 1920
        assert layout.video_height == 2400

        layout.cameras("front").scale = 1
        layout.cameras("left_pillar").scale = 1 / 4
        layout.cameras("right_pillar").scale = 1 / 4
        layout.cameras("left").scale = 1 / 4
        layout.cameras("right").scale = 1 / 4
        layout.cameras("rear").scale = 1
        assert layout.cameras("front").xpos == 0
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("front").width == 1280
        assert layout.cameras("front").height == 960
        assert layout.cameras("left_pillar").xpos == 320
        assert layout.cameras("left_pillar").ypos == 960
        assert layout.cameras("left_pillar").width == 320
        assert layout.cameras("left_pillar").height == 240
        assert layout.cameras("right_pillar").xpos == 640
        assert layout.cameras("right_pillar").ypos == 960
        assert layout.cameras("right_pillar").width == 320
        assert layout.cameras("right_pillar").height == 240
        assert layout.cameras("left").xpos == 320
        assert layout.cameras("left").ypos == 1200
        assert layout.cameras("left").width == 320
        assert layout.cameras("left").height == 240
        assert layout.cameras("right").xpos == 640
        assert layout.cameras("right").ypos == 1200
        assert layout.cameras("right").width == 320
        assert layout.cameras("right").height == 240
        assert layout.cameras("rear").xpos == 0
        assert layout.cameras("rear").ypos == 1440
        assert layout.cameras("rear").width == 1280
        assert layout.cameras("rear").height == 960
        assert layout.video_width == 1280
        assert layout.video_height == 2400


class TestDiamond:
    @pytest.fixture
    def layout(self):
        return Diamond()

    def test_init(self, layout):
        """Test Diamond initialization"""
        assert layout.scale == 4
        assert layout.cameras("front").width == 1280
        assert layout.cameras("front").height == 960
        assert layout.cameras("left_pillar").width == 640
        assert layout.cameras("left_pillar").height == 480
        assert layout.cameras("right_pillar").width == 640
        assert layout.cameras("right_pillar").height == 480
        assert layout.cameras("left").width == 640
        assert layout.cameras("left").height == 480
        assert layout.cameras("right").width == 640
        assert layout.cameras("right").height == 480
        assert layout.cameras("rear").width == 1280
        assert layout.cameras("rear").height == 960

    def test_default(self, layout):
        """Test video dimensions with default camera sizes"""
        assert layout.cameras("front").xpos == 640
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 480
        assert layout.cameras("right_pillar").xpos == 1920
        assert layout.cameras("right_pillar").ypos == 480
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 960
        assert layout.cameras("right").xpos == 1920
        assert layout.cameras("right").ypos == 960
        assert layout.cameras("rear").xpos == 640
        assert layout.cameras("rear").ypos == 960
        assert layout.video_width == 2560
        assert layout.video_height == 1920

    def test_excluded_rows(self, layout):
        """Test video dimensions with default camera sizes"""
        layout.cameras("front").include = False
        assert layout.cameras("front").xpos == 0
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("right_pillar").xpos == 1920
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 480
        assert layout.cameras("right").xpos == 1920
        assert layout.cameras("right").ypos == 480
        assert layout.cameras("rear").xpos == 640
        assert layout.cameras("rear").ypos == 0
        assert layout.video_width == 2560
        assert layout.video_height == 960

        layout.cameras("front").include = True
        layout.cameras("left_pillar").include = False
        assert layout.cameras("front").xpos == 640
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("right_pillar").xpos == 1920
        assert layout.cameras("right_pillar").ypos == 480
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 720
        assert layout.cameras("right").xpos == 1920
        assert layout.cameras("right").ypos == 960
        assert layout.cameras("rear").xpos == 640
        assert layout.cameras("rear").ypos == 960
        assert layout.video_width == 2560
        assert layout.video_height == 1920

        layout.cameras("right_pillar").include = False
        assert layout.cameras("front").xpos == 640
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("right_pillar").xpos == 0
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 720
        assert layout.cameras("right").xpos == 1920
        assert layout.cameras("right").ypos == 720
        assert layout.cameras("rear").xpos == 640
        assert layout.cameras("rear").ypos == 960
        assert layout.video_width == 2560
        assert layout.video_height == 1920

        layout.cameras("left").include = False
        assert layout.cameras("front").xpos == 0
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("right_pillar").xpos == 0
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 0
        assert layout.cameras("right").xpos == 1280
        assert layout.cameras("right").ypos == 720
        assert layout.cameras("rear").xpos == 0
        assert layout.cameras("rear").ypos == 960
        assert layout.video_width == 1920
        assert layout.video_height == 1920

        layout.cameras("right").include = False
        assert layout.cameras("front").xpos == 0
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("right_pillar").xpos == 0
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 0
        assert layout.cameras("right").xpos == 0
        assert layout.cameras("right").ypos == 0
        assert layout.cameras("rear").xpos == 0
        assert layout.cameras("rear").ypos == 960
        assert layout.video_width == 1280
        assert layout.video_height == 1920

        layout.cameras("left").include = True
        assert layout.cameras("front").xpos == 640
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("right_pillar").xpos == 0
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 720
        assert layout.cameras("right").xpos == 0
        assert layout.cameras("right").ypos == 0
        assert layout.cameras("rear").xpos == 640
        assert layout.cameras("rear").ypos == 960
        assert layout.video_width == 1920
        assert layout.video_height == 1920

        layout.cameras("right_pillar").include = True
        assert layout.cameras("front").xpos == 640
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("right_pillar").xpos == 1920
        assert layout.cameras("right_pillar").ypos == 720
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 720
        assert layout.cameras("right").xpos == 0
        assert layout.cameras("right").ypos == 0
        assert layout.cameras("rear").xpos == 640
        assert layout.cameras("rear").ypos == 960
        assert layout.video_width == 2560
        assert layout.video_height == 1920

        layout.cameras("left_pillar").include = True
        layout.cameras("right").include = True
        layout.cameras("rear").include = False
        assert layout.cameras("front").xpos == 640
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("right_pillar").xpos == 1920
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 480
        assert layout.cameras("right").xpos == 1920
        assert layout.cameras("right").ypos == 480
        assert layout.cameras("rear").xpos == 0
        assert layout.cameras("rear").ypos == 0
        assert layout.video_width == 2560
        assert layout.video_height == 960

    def test_scaling_rows(self, layout):
        """Test video dimensions with default camera sizes"""
        layout.cameras("front").scale = 2
        assert layout.cameras("front").xpos == 640
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 960
        assert layout.cameras("right_pillar").xpos == 3200
        assert layout.cameras("right_pillar").ypos == 960
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 1440
        assert layout.cameras("right").xpos == 3200
        assert layout.cameras("right").ypos == 1440
        assert layout.cameras("rear").xpos == 1280
        assert layout.cameras("rear").ypos == 1920
        assert layout.video_width == 3840
        assert layout.video_height == 2880

        layout.cameras("front").scale = 1
        layout.cameras("left_pillar").scale = 1
        assert layout.cameras("front").xpos == 1280
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 240
        assert layout.cameras("right_pillar").xpos == 2560
        assert layout.cameras("right_pillar").ypos == 480
        assert layout.cameras("left").xpos == 640
        assert layout.cameras("left").ypos == 1200
        assert layout.cameras("right").xpos == 2560
        assert layout.cameras("right").ypos == 960
        assert layout.cameras("rear").xpos == 1280
        assert layout.cameras("rear").ypos == 960
        assert layout.video_width == 3200
        assert layout.video_height == 1920

        layout.cameras("right_pillar").scale = 1
        assert layout.cameras("front").xpos == 1280
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 240
        assert layout.cameras("right_pillar").xpos == 2560
        assert layout.cameras("right_pillar").ypos == 240
        assert layout.cameras("left").xpos == 640
        assert layout.cameras("left").ypos == 1200
        assert layout.cameras("right").xpos == 2560
        assert layout.cameras("right").ypos == 1200
        assert layout.cameras("rear").xpos == 1280
        assert layout.cameras("rear").ypos == 960
        assert layout.video_width == 3840
        assert layout.video_height == 1920

        layout.cameras("left").scale = 1
        assert layout.cameras("front").xpos == 1280
        assert layout.cameras("front").ypos == 0
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("right_pillar").xpos == 2560
        assert layout.cameras("right_pillar").ypos == 240
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 960
        assert layout.cameras("right").xpos == 2560
        assert layout.cameras("right").ypos == 1200
        assert layout.cameras("rear").xpos == 1280
        assert layout.cameras("rear").ypos == 960
        assert layout.video_width == 3840
        assert layout.video_height == 1920

        layout.cameras("left_pillar").scale = 1
        layout.cameras("right_pillar").scale = 1
        layout.cameras("left").scale = 1
        layout.cameras("right").scale = 1
        layout.cameras("front").scale = 1 / 2
        layout.cameras("rear").scale = 1 / 2
        assert layout.cameras("front").xpos == 1280
        assert layout.cameras("front").ypos == 480
        assert layout.cameras("left_pillar").xpos == 0
        assert layout.cameras("left_pillar").ypos == 0
        assert layout.cameras("right_pillar").xpos == 1920
        assert layout.cameras("right_pillar").ypos == 0
        assert layout.cameras("left").xpos == 0
        assert layout.cameras("left").ypos == 960
        assert layout.cameras("right").xpos == 1920
        assert layout.cameras("right").ypos == 960
        assert layout.cameras("rear").xpos == 1280
        assert layout.cameras("rear").ypos == 960
        assert layout.video_width == 3200
        assert layout.video_height == 1920
