from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, PropertyMock

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
    Mosaic,
    MovieLayout,
    escape_drawtext_literals,
)


def verify_camera_layout(layout, config, expected):
    # Apply camera inclusion settings
    for key, val in config.items():
        if isinstance(val, bool):
            layout.cameras(key).include = val
        elif isinstance(val, dict):
            for sub_key, sub_val in val.items():
                layout.cameras(sub_key).scale = sub_val
        else:
            layout.cameras(key).scale = val

    # Assert positions
    for cam, (x, y) in expected["positions"].items():
        assert layout.cameras(cam).xpos == x
        assert layout.cameras(cam).ypos == y

    # Assert camera dimensions if provided
    if "dimensions" in expected:
        for cam, (w, h) in expected["dimensions"].items():
            assert layout.cameras(cam).width == w
            assert layout.cameras(cam).height == h

    # Assert video dimensions
    assert layout.video_width == expected["video"][0]
    assert layout.video_height == expected["video"][1]

    # Optional: scale check
    if "scale" in expected:
        assert round(layout.scale, 2) == round(expected["scale"], 2)


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


class TestFullScreen:
    @pytest.fixture
    def layout(self):
        return FullScreen()

    def test_init(self, layout):
        """Test FullScreen initialization"""
        assert layout.scale == 1.5

    @pytest.mark.parametrize(
        "config, expected",
        [
            # Default
            (
                {},
                {
                    "positions": {
                        "left_pillar": (0, 0),
                        "front": (640, 0),
                        "right_pillar": (1280, 0),
                        "left": (0, 480),
                        "rear": (640, 480),
                        "right": (1280, 480),
                    },
                    "video": (1920, 960),
                },
            ),
            # left_pillar_only_off
            (
                {"left_pillar": False},
                {
                    "positions": {
                        "left_pillar": (0, 0),
                        "front": (320, 0),
                        "right_pillar": (960, 0),
                        "left": (0, 480),
                        "rear": (640, 480),
                        "right": (1280, 480),
                    },
                    "video": (1920, 960),
                },
            ),
            # left_pillar_and_front_off
            (
                {"left_pillar": False, "front": False},
                {
                    "positions": {
                        "left_pillar": (0, 0),
                        "front": (0, 0),
                        "right_pillar": (640, 0),
                        "left": (0, 480),
                        "rear": (640, 480),
                        "right": (1280, 480),
                    },
                    "video": (1920, 960),
                },
            ),
            # front_off_only
            (
                {"front": False},
                {
                    "positions": {
                        "left_pillar": (320, 0),
                        "front": (0, 0),
                        "right_pillar": (960, 0),
                        "left": (0, 480),
                        "rear": (640, 480),
                        "right": (1280, 480),
                    },
                    "video": (1920, 960),
                },
            ),
            # pillars_off
            (
                {"left_pillar": False, "right_pillar": False},
                {
                    "positions": {
                        "left_pillar": (0, 0),
                        "front": (640, 0),
                        "right_pillar": (0, 0),
                        "left": (0, 480),
                        "rear": (640, 480),
                        "right": (1280, 480),
                    },
                    "video": (1920, 960),
                    "scale": 1.5,
                },
            ),
            # front_and_pillars_off
            (
                {"front": False, "left_pillar": False, "right_pillar": False},
                {
                    "positions": {
                        "left_pillar": (0, 0),
                        "front": (0, 0),
                        "right_pillar": (0, 0),
                        "left": (0, 0),
                        "rear": (640, 0),
                        "right": (1280, 0),
                    },
                    "video": (1920, 480),
                    "scale": 0.75,
                },
            ),
            # left_off
            (
                {"left": False},
                {
                    "positions": {
                        "left_pillar": (0, 0),
                        "front": (640, 0),
                        "right_pillar": (1280, 0),
                        "left": (0, 0),
                        "rear": (320, 480),
                        "right": (960, 480),
                    },
                    "video": (1920, 960),
                },
            ),
            # left_and_rear_off
            (
                {"left": False, "rear": False},
                {
                    "positions": {
                        "left_pillar": (0, 0),
                        "front": (640, 0),
                        "right_pillar": (1280, 0),
                        "left": (0, 0),
                        "rear": (0, 0),
                        "right": (640, 480),
                    },
                    "video": (1920, 960),
                },
            ),
            # rear_off
            (
                {"rear": False},
                {
                    "positions": {
                        "left_pillar": (0, 0),
                        "front": (640, 0),
                        "right_pillar": (1280, 0),
                        "left": (320, 480),
                        "rear": (0, 0),
                        "right": (960, 480),
                    },
                    "video": (1920, 960),
                },
            ),
            # left_and_right_off
            (
                {"left": False, "right": False},
                {
                    "positions": {
                        "left_pillar": (0, 0),
                        "front": (640, 0),
                        "right_pillar": (1280, 0),
                        "left": (0, 0),
                        "rear": (640, 480),
                        "right": (0, 0),
                    },
                    "video": (1920, 960),
                    "scale": 1.5,
                },
            ),
            # front_and_rear_only
            (
                {
                    "left_pillar": False,
                    "right_pillar": False,
                    "left": False,
                    "right": False,
                },
                {
                    "positions": {
                        "left_pillar": (0, 0),
                        "front": (0, 0),
                        "right_pillar": (0, 0),
                        "left": (0, 0),
                        "rear": (0, 480),
                        "right": (0, 0),
                    },
                    "video": (640, 960),
                },
            ),
            # left_pillar_scaled_full
            (
                {"left_pillar": 1},
                {
                    "positions": {
                        "left_pillar": (0, 0),
                        "front": (1280, 240),
                        "right_pillar": (1920, 240),
                        "left": (320, 960),
                        "rear": (960, 960),
                        "right": (1600, 960),
                    },
                    "dimensions": {
                        "left_pillar": (1280, 960),
                    },
                    "video": (2560, 1440),
                    "scale": 3,
                },
            ),
            # front_scaled_full
            (
                {"front": 1},
                {
                    "positions": {
                        "left_pillar": (0, 240),
                        "front": (640, 0),
                        "right_pillar": (1920, 240),
                        "left": (320, 960),
                        "rear": (960, 960),
                        "right": (1600, 960),
                    },
                    "video": (2560, 1440),
                    "scale": 3,
                },
            ),
            # right_pillar_scaled_full
            (
                {"right_pillar": 1},
                {
                    "positions": {
                        "left_pillar": (0, 240),
                        "front": (640, 240),
                        "right_pillar": (1280, 0),
                        "left": (320, 960),
                        "rear": (960, 960),
                        "right": (1600, 960),
                    },
                    "video": (2560, 1440),
                    "scale": 3,
                },
            ),
            # left_scaled_full
            (
                {"left": 1},
                {
                    "positions": {
                        "left_pillar": (320, 0),
                        "front": (960, 0),
                        "right_pillar": (1600, 0),
                        "left": (0, 480),
                        "rear": (1280, 720),
                        "right": (1920, 720),
                    },
                    "video": (2560, 1440),
                    "scale": 3,
                },
            ),
            # rear_scaled_full
            (
                {"rear": 1},
                {
                    "positions": {
                        "left_pillar": (320, 0),
                        "front": (960, 0),
                        "right_pillar": (1600, 0),
                        "left": (0, 720),
                        "rear": (640, 480),
                        "right": (1920, 720),
                    },
                    "video": (2560, 1440),
                    "scale": 3,
                },
            ),
            # right_scaled_full
            (
                {"right": 1},
                {
                    "positions": {
                        "left_pillar": (320, 0),
                        "front": (960, 0),
                        "right_pillar": (1600, 0),
                        "left": (0, 720),
                        "rear": (640, 720),
                        "right": (1280, 480),
                    },
                    "video": (2560, 1440),
                    "scale": 3,
                },
            ),
        ],
        ids=[
            "default",
            "left_pillar_only_off",
            "left_pillar_and_front_off",
            "front_off_only",
            "pillars_off",
            "front_and_pillars_off",
            "left_off",
            "left_and_rear_off",
            "rear_off",
            "left_and_right_off",
            "front_and_rear_only",
            "left_pillar_scaled_full",
            "front_scaled_full",
            "right_pillar_scaled_full",
            "left_scaled_full",
            "rear_scaled_full",
            "right_scaled_full",
        ],
    )
    def test_camera_layout(self, layout, config, expected):
        verify_camera_layout(layout=layout, config=config, expected=expected)


class TestMosaic:
    @pytest.fixture
    def layout(self):
        return Mosaic()

    def test_init(self, layout):
        """Test Mosaic initialization"""
        # Mosaic initializes with scale = 0.5 and aspect ratio preservation
        # which results in dynamic scale calculation based on video dimensions
        assert layout.scale != 1.5  # Different from FullScreen

    @pytest.mark.parametrize(
        "config, expected",
        [
            # default_layout
            (
                {},
                {
                    "positions": {
                        "left_pillar": (0, 216),
                        "front": (640, 0),
                        "right_pillar": (1856, 216),
                        "left": (0, 1128),
                        "rear": (640, 912),
                        "right": (1856, 1128),
                    },
                    "video": (2496, 1824),
                },
            ),
            # front_widescreen
            (
                {"left": 1, "rear": 1, "right": 1},
                {
                    "positions": {
                        "left_pillar": (0, 1152),
                        "front": (640, 0),
                        "right_pillar": (4352, 1152),
                        "left": (576, 2784),
                        "rear": (1856, 2784),
                        "right": (3136, 2784),
                    },
                    "video": (4992, 3744),
                },
            ),
            # rear_widescreen
            (
                {"left_pillar": 1, "front": 1, "right_pillar": 1},
                {
                    "positions": {
                        "left_pillar": (576, 0),
                        "front": (1856, 0),
                        "right_pillar": (3136, 0),
                        "left": (0, 2112),
                        "rear": (640, 960),
                        "right": (4352, 2112),
                    },
                    "video": (4992, 3744),
                },
            ),
        ],
        ids=[
            "default_layout",
            "front_widescreen",
            "rear_widescreen",
        ],
    )
    def test_camera_layout(self, layout, config, expected):
        verify_camera_layout(layout=layout, config=config, expected=expected)


class TestCross:
    @pytest.fixture
    def layout(self):
        return Cross()

    def test_init(self, layout):
        """Test Cross initialization"""
        assert layout.scale == 2

    @pytest.mark.parametrize(
        "config, expected",
        [
            # default
            (
                {},
                {
                    "positions": {
                        "front": (320, 0),
                        "left_pillar": (0, 480),
                        "right_pillar": (640, 480),
                        "left": (0, 960),
                        "right": (640, 960),
                        "rear": (320, 1440),
                    },
                    "video": (1280, 1920),
                },
            ),
            # excluded_front
            (
                {"front": False},
                {
                    "positions": {
                        "front": (0, 0),
                        "left_pillar": (0, 0),
                        "right_pillar": (640, 0),
                        "left": (0, 480),
                        "right": (640, 480),
                        "rear": (320, 960),
                    },
                    "video": (1280, 1440),
                },
            ),
            # excluded_row1
            (
                {"left_pillar": False, "right_pillar": False},
                {
                    "positions": {
                        "front": (320, 0),
                        "left_pillar": (0, 0),
                        "right_pillar": (0, 0),
                        "left": (0, 480),
                        "right": (640, 480),
                        "rear": (320, 960),
                    },
                    "video": (1280, 1440),
                },
            ),
            # excluded_row2
            (
                {
                    "left": False,
                    "right": False,
                },
                {
                    "positions": {
                        "front": (320, 0),
                        "left_pillar": (0, 480),
                        "right_pillar": (640, 480),
                        "left": (0, 0),
                        "right": (0, 0),
                        "rear": (320, 960),
                    },
                    "video": (1280, 1440),
                },
            ),
            # scale_front
            (
                {"front": 2},
                {
                    "positions": {
                        "front": (0, 0),
                        "left_pillar": (640, 1920),
                        "right_pillar": (1280, 1920),
                        "left": (640, 2400),
                        "right": (1280, 2400),
                        "rear": (960, 2880),
                    },
                    "dimensions": {
                        "front": (2560, 1920),
                    },
                    "video": (2560, 3360),
                    "scale": 7,
                },
            ),
            # scale_left_pillar
            (
                {"left_pillar": 1},
                {
                    "positions": {
                        "front": (640, 0),
                        "left_pillar": (0, 480),
                        "right_pillar": (1280, 720),
                        "left": (320, 1440),
                        "right": (960, 1440),
                        "rear": (640, 1920),
                    },
                    "dimensions": {
                        "left_pillar": (1280, 960),
                    },
                    "video": (1920, 2400),
                    "scale": 3.75,
                },
            ),
            # scale_right
            (
                {"right": 1},
                {
                    "positions": {
                        "front": (640, 0),
                        "left_pillar": (320, 480),
                        "right_pillar": (960, 480),
                        "left": (0, 1200),
                        "right": (640, 960),
                        "rear": (640, 1920),
                    },
                    "dimensions": {
                        "right": (1280, 960),
                    },
                    "video": (1920, 2400),
                    "scale": 3.75,
                },
            ),
            # quarter_scaled
            (
                {
                    "front": 1,
                    "left_pillar": 0.25,
                    "right_pillar": 0.25,
                    "left": 0.25,
                    "right": 0.25,
                    "rear": 1,
                },
                {
                    "positions": {
                        "front": (0, 0),
                        "left_pillar": (320, 960),
                        "right_pillar": (640, 960),
                        "left": (320, 1200),
                        "right": (640, 1200),
                        "rear": (0, 1440),
                    },
                    "dimensions": {
                        "front": (1280, 960),
                        "left_pillar": (320, 240),
                        "right_pillar": (320, 240),
                        "left": (320, 240),
                        "right": (320, 240),
                        "rear": (1280, 960),
                    },
                    "video": (1280, 2400),
                },
            ),
        ],
        ids=[
            "default",
            "excluded_front",
            "excluded_row1",
            "excluded_row2",
            "scale_front",
            "scale_left_pillar",
            "scale_right",
            "quarter_scaled",
        ],
    )
    def test_camera_layout(self, layout, config, expected):
        verify_camera_layout(layout=layout, config=config, expected=expected)


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

    @pytest.mark.parametrize(
        "config, expected",
        [
            # default
            (
                {},
                {
                    "positions": {
                        "front": (640, 0),
                        "left_pillar": (0, 480),
                        "right_pillar": (1920, 480),
                        "left": (0, 960),
                        "right": (1920, 960),
                        "rear": (640, 960),
                    },
                    "video": (2560, 1920),
                },
            ),
            # exclude_front
            (
                {"front": False},
                {
                    "positions": {
                        "front": (0, 0),
                        "left_pillar": (0, 0),
                        "right_pillar": (1920, 0),
                        "left": (0, 480),
                        "right": (1920, 480),
                        "rear": (640, 0),
                    },
                    "video": (2560, 960),
                },
            ),
            # exclude_left_pillar
            (
                {"front": True, "left_pillar": False},
                {
                    "positions": {
                        "front": (640, 0),
                        "left_pillar": (0, 0),
                        "right_pillar": (1920, 480),
                        "left": (0, 720),
                        "right": (1920, 960),
                        "rear": (640, 960),
                    },
                    "video": (2560, 1920),
                },
            ),
            # exclude_left_and_right_pillar
            (
                {"left_pillar": False, "right_pillar": False},
                {
                    "positions": {
                        "front": (640, 0),
                        "left_pillar": (0, 0),
                        "right_pillar": (0, 0),
                        "left": (0, 720),
                        "right": (1920, 720),
                        "rear": (640, 960),
                    },
                    "video": (2560, 1920),
                },
            ),
            # exclude_left_and_right_pillar_and_left
            (
                {"left_pillar": False, "right_pillar": False, "left": False},
                {
                    "positions": {
                        "front": (0, 0),
                        "left_pillar": (0, 0),
                        "right_pillar": (0, 0),
                        "left": (0, 0),
                        "right": (1280, 720),
                        "rear": (0, 960),
                    },
                    "video": (1920, 1920),
                },
            ),
            # exclude_left_and_right_pillar_and_left_and_right
            (
                {
                    "left": False,
                    "left_pillar": False,
                    "right": False,
                    "right_pillar": False,
                },
                {
                    "positions": {
                        "front": (0, 0),
                        "left_pillar": (0, 0),
                        "right_pillar": (0, 0),
                        "left": (0, 0),
                        "right": (0, 0),
                        "rear": (0, 960),
                    },
                    "video": (1280, 1920),
                },
            ),
            # exclude_left_and_right_pillar_and_right
            (
                {"left_pillar": False, "right_pillar": False, "right": False},
                {
                    "positions": {
                        "front": (640, 0),
                        "left_pillar": (0, 0),
                        "right_pillar": (0, 0),
                        "left": (0, 720),
                        "right": (0, 0),
                        "rear": (640, 960),
                    },
                    "video": (1920, 1920),
                },
            ),
            # exclude_left_pillar_and_right
            (
                {"left_pillar": False, "right": False},
                {
                    "positions": {
                        "front": (640, 0),
                        "left_pillar": (0, 0),
                        "right_pillar": (1920, 720),
                        "left": (0, 720),
                        "right": (0, 0),
                        "rear": (640, 960),
                    },
                    "video": (2560, 1920),
                },
            ),
            # exclude_rear
            (
                {"rear": False},
                {
                    "positions": {
                        "front": (640, 0),
                        "left_pillar": (0, 0),
                        "right_pillar": (1920, 0),
                        "left": (0, 480),
                        "right": (1920, 480),
                        "rear": (0, 0),
                    },
                    "video": (2560, 960),
                },
            ),
            # front_scaled
            (
                {"scale": {"front": 2}},
                {
                    "positions": {
                        "front": (640, 0),
                        "left_pillar": (0, 960),
                        "right_pillar": (3200, 960),
                        "left": (0, 1440),
                        "right": (3200, 1440),
                        "rear": (1280, 1920),
                    },
                    "video": (3840, 2880),
                },
            ),
            # left_pillar_scaled
            (
                {"scale": {"left_pillar": 1}},
                {
                    "positions": {
                        "front": (1280, 0),
                        "left_pillar": (0, 240),
                        "right_pillar": (2560, 480),
                        "left": (640, 1200),
                        "right": (2560, 960),
                        "rear": (1280, 960),
                    },
                    "video": (3200, 1920),
                },
            ),
            # left_and_right_pillar_scaled
            (
                {"scale": {"left_pillar": 1, "right_pillar": 1}},
                {
                    "positions": {
                        "front": (1280, 0),
                        "left_pillar": (0, 240),
                        "right_pillar": (2560, 240),
                        "left": (640, 1200),
                        "right": (2560, 1200),
                        "rear": (1280, 960),
                    },
                    "video": (3840, 1920),
                },
            ),
            # left_and_right_pillar_and_left_scaled
            (
                {"scale": {"left_pillar": 1, "right_pillar": 1, "left": 1}},
                {
                    "positions": {
                        "front": (1280, 0),
                        "left_pillar": (0, 0),
                        "right_pillar": (2560, 240),
                        "left": (0, 960),
                        "right": (2560, 1200),
                        "rear": (1280, 960),
                    },
                    "video": (3840, 1920),
                },
            ),
            # front_and_rear_half_size_and_all_others_scaled_up
            (
                {
                    "scale": {
                        "front": 0.5,
                        "rear": 0.5,
                        "left_pillar": 1,
                        "right_pillar": 1,
                        "left": 1,
                        "right": 1,
                    }
                },
                {
                    "positions": {
                        "front": (1280, 480),
                        "left_pillar": (0, 0),
                        "right_pillar": (1920, 0),
                        "left": (0, 960),
                        "right": (1920, 960),
                        "rear": (1280, 960),
                    },
                    "video": (3200, 1920),
                },
            ),
        ],
        ids=[
            "default",
            "exclude_front",
            "exclude_left_pillar",
            "exclude_left_and_right_pillar",
            "exclude_left_and_right_pillar_and_left",
            "exclude_left_and_right_pillar_and_left_and_right",
            "exclude_left_and_right_pillar_and_right",
            "exclude_left_pillar_and_right",
            "exclude_rear",
            "front_scaled",
            "left_pillar_scaled",
            "left_and_right_pillar_scaled",
            "left_and_right_pillar_and_left_scaled",
            "front_and_rear_half_size_and_all_others_scaled_up",
        ],
    )
    def test_camera_layout(self, layout, config, expected):
        verify_camera_layout(layout=layout, config=config, expected=expected)


class TestEdgeCases:
    def test_create_movie_no_clips_returns_false(self):
        from tesla_dashcam.tesla_dashcam import Movie, create_movie

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

        from tesla_dashcam.tesla_dashcam import create_movie_ffmpeg

        # Capture join file path written and prevent deletion
        removed_paths = []

        def fake_remove(path):
            removed_paths.append(path)
            # Do not actually delete; allow inspection

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
        # ffmpeg concat syntax requires closing+escaped apostrophe+reopen i.e. '\'\''
        assert "'\\''" in content, f"Join file not escaping apostrophes: {content}"
