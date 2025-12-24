import pytest

from tesla_dashcam.tesla_dashcam import Diamond


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
    def test_camera_layout(self, layout, config, expected, verify_camera_layout):
        verify_camera_layout(layout=layout, config=config, expected=expected)
