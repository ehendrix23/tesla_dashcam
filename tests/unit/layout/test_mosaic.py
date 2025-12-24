import pytest

from tesla_dashcam.tesla_dashcam import Mosaic


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
    def test_camera_layout(self, layout, config, expected, verify_camera_layout):
        verify_camera_layout(layout=layout, config=config, expected=expected)
