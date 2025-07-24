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


def verify_camera_layout(layout, config, expected):
    # Apply camera inclusion settings
    for cam, val in config.items():
        if isinstance(val, bool):
            layout.cameras(cam).include = val
        elif isinstance(val, dict):
            for sub_key, sub_val in val.items():
                layout.cameras(sub_key).scale = sub_val
        else:
            layout.cameras(cam).scale = val

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


class TestWideScreen:
    @pytest.fixture
    def layout(self):
        return WideScreen()

    def test_init(self, layout):
        """Test WideScreen initialization"""
        assert layout.scale == 1.5

    @pytest.mark.parametrize(
        "config, expected",
        [
            # default_layout
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
            # front_widescreen
            (
                {"left": 1, "rear": 1, "right": 1},
                {
                    "positions": {
                        "left_pillar": (0, 0),
                        "front": (640, 0),
                        "right_pillar": (3200, 0),
                        "left": (0, 480),
                        "rear": (1280, 480),
                        "right": (2560, 480),
                    },
                    "video": (3840, 1440),
                    "scale": 4.5,
                    "dimensions": {
                        "front": (2560, 480),
                    },
                },
            ),
            # rear_widescreen
            (
                {"left_pillar": 1, "front": 1, "right_pillar": 1},
                {
                    "positions": {
                        "left_pillar": (0, 0),
                        "front": (1280, 0),
                        "right_pillar": (2560, 0),
                        "left": (0, 960),
                        "rear": (640, 960),
                        "right": (3200, 960),
                    },
                    "video": (3840, 1440),
                    "scale": 4.5,
                    "dimensions": {
                        "rear": (2560, 480),
                    },
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
