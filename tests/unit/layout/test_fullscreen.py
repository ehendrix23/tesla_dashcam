import pytest

from tesla_dashcam.tesla_dashcam import FullScreen


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
    def test_camera_layout(self, layout, config, expected, verify_camera_layout):
        verify_camera_layout(layout=layout, config=config, expected=expected)
