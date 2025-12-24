from __future__ import annotations

import re

from tesla_dashcam import utils


def test_get_current_timestamp_disabled_by_default():
    assert utils.DISPLAY_TS is False
    assert utils.get_current_timestamp() == ""


def test_get_current_timestamp_enabled(monkeypatch):
    monkeypatch.setattr(utils, "DISPLAY_TS", True)
    ts = utils.get_current_timestamp()

    assert isinstance(ts, str)
    assert ts.endswith(" - ")
    assert re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} - $", ts)
