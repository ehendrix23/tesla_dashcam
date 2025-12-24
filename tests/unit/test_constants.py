from __future__ import annotations

import sys

from tesla_dashcam import constants


def test_platform_matches_sys_platform():
    assert constants.PLATFORM == sys.platform


def test_alignment_maps_have_expected_keys():
    assert set(constants.HALIGN) == {"LEFT", "CENTER", "RIGHT"}
    assert set(constants.VALIGN) == {"TOP", "MIDDLE", "BOTTOM"}

    for value in constants.HALIGN.values():
        assert isinstance(value, str)
        assert value

    for value in constants.VALIGN.values():
        assert isinstance(value, str)
        assert value


def test_default_fonts_has_common_platforms():
    for platform_key in ("darwin", "win32", "linux"):
        assert platform_key in constants.DEFAULT_FONT
        assert isinstance(constants.DEFAULT_FONT[platform_key], str)
        assert constants.DEFAULT_FONT[platform_key]


def test_ffmpeg_perspective_strings_are_nonempty():
    assert isinstance(constants.FFMPEG_LEFT_PERSPECTIVE, str)
    assert isinstance(constants.FFMPEG_RIGHT_PERSPECTIVE, str)
    assert constants.FFMPEG_LEFT_PERSPECTIVE.strip() != ""
    assert constants.FFMPEG_RIGHT_PERSPECTIVE.strip() != ""


def test_module_all_exports_public_api():
    for name in (
        "DEFAULT_FONT",
        "DEFAULT_FONT_HALIGN",
        "DEFAULT_FONT_VALIGN",
        "FFMPEG_LEFT_PERSPECTIVE",
        "FFMPEG_RIGHT_PERSPECTIVE",
        "HALIGN",
        "PLATFORM",
        "VALIGN",
    ):
        assert name in constants.__all__
        assert hasattr(constants, name)
