import pytest

from tesla_dashcam.tesla_dashcam import Cross


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
    def test_camera_layout(self, layout, config, expected, verify_camera_layout):
        verify_camera_layout(layout=layout, config=config, expected=expected)
