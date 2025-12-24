import pytest


@pytest.fixture
def verify_camera_layout():
    def _verify(layout, config, expected):
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

    return _verify
