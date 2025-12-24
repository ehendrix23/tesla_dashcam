from __future__ import annotations

from typing import TYPE_CHECKING

from ..constants import (
    DEFAULT_FONT,
    DEFAULT_FONT_HALIGN,
    DEFAULT_FONT_VALIGN,
    FFMPEG_LEFT_PERSPECTIVE,
    FFMPEG_RIGHT_PERSPECTIVE,
    HALIGN,
    PLATFORM,
    VALIGN,
)
from ..models.event import Event

if TYPE_CHECKING:
    pass


class Font(object):
    """Font Class"""

    def __init__(
        self,
        layout: MovieLayout,
        font: str | None = None,
        size: int | None = None,
        color: str | None = None,
    ):
        self._layout: MovieLayout = layout
        self._font: str | None = font or DEFAULT_FONT.get(PLATFORM, None)
        self._size: int | None = size
        self._color: str | None = color
        self._halign: str = DEFAULT_FONT_HALIGN
        self._valign: str = DEFAULT_FONT_VALIGN
        self._xpos: int | None = None
        self._ypos: int | None = None

    @property
    def font(self) -> str | None:
        return self._font

    @font.setter
    def font(self, value: str) -> None:
        self._font = value

    @property
    def size(self) -> int:
        if (overriden := self._get_overridden("font_size")) is not None:
            return int(overriden)

        return (
            int(max(16, 16 * self._layout.scale)) if self._size is None else self._size
        )

    @size.setter
    def size(self, value: int) -> None:
        self._size = value

    @property
    def color(self) -> str | None:
        return self._color

    @color.setter
    def color(self, value: str) -> None:
        self._color = value

    @property
    def halign(self) -> str:
        if (overriden := self._get_overridden("font_halign")) is not None:
            return str(overriden)

        return HALIGN.get(self._halign, HALIGN[DEFAULT_FONT_HALIGN])

    @halign.setter
    def halign(self, value: str) -> None:
        self._halign = value

    @property
    def valign(self) -> str:
        if (overriden := self._get_overridden("font_valign")) is not None:
            return str(overriden)
        return VALIGN.get(self._valign, VALIGN[DEFAULT_FONT_VALIGN])

    @valign.setter
    def valign(self, value: str) -> None:
        self._valign = value

    @property
    def xpos(self) -> int | None:
        return self._xpos

    @xpos.setter
    def xpos(self, value: int | None) -> None:
        self._xpos = value

    @property
    def ypos(self) -> int | None:
        return self._ypos

    @ypos.setter
    def ypos(self, value: int | None) -> None:
        self._ypos = value

    def _get_overridden(self, attr) -> str | int | None:
        try:
            return getattr(self._layout, f"{attr}", None)()  # type: ignore[misc]
        except (AttributeError, TypeError):
            return None


class Camera(object):
    """Camera Class"""

    def __init__(self, layout: MovieLayout, camera: str):
        self._layout: MovieLayout = layout
        self._camera: str = camera
        self._include: bool = True
        self._width: int = 1280
        self._height: int = 960
        self._clip_ratio: float = 4 / 3
        self._xpos: int = 0
        self._xpos_override: bool = False
        self._ypos: int = 0
        self._ypos_override: bool = False
        self._scale: float | None = 1
        self._mirror: bool = False
        self._options: str = ""

    @property
    def layout(self) -> MovieLayout:
        return self._layout

    @layout.setter
    def layout(self, value: MovieLayout) -> None:
        self._layout = value

    @property
    def camera(self) -> str:
        return self._camera

    @camera.setter
    def camera(self, value: str) -> None:
        self._camera = value

    @property
    def include(self) -> bool:
        # If we're supposed to include then check the event to see if it should be
        # included
        if not self._include:
            return False

        # Make sure layout has an event.
        if self._layout.event is not None:
            return self._layout.event.has_camera_clip(self.camera)

        return self._include

    @include.setter
    def include(self, value: bool) -> None:
        self._include = value

    @property
    def width_fixed(self) -> int:
        return self._width

    @property
    def height_fixed(self) -> int:
        return self._height

    @property
    def width(self) -> int:
        if (overriden := self._get_overridden("width")) is not None:
            return int(overriden) * self.include

        return int(self._width * (self.scale or 1)) * self.include

    @width.setter
    def width(self, value: int) -> None:
        self._width = value

    @property
    def scale_width(self) -> int:
        return self.width

    @property
    def height(self) -> int:
        perspective_adjustement: float = 1
        if self.layout.perspective and self.camera in [
            "left",
            "right",
            "left_pillar",
            "right_pillar",
        ]:
            # Adjust height for perspective cameras
            perspective_adjustement = 3 / 2
        return int(self.scale_height * perspective_adjustement)

    @height.setter
    def height(self, value: int) -> None:
        self._height = value

    @property
    def scale_height(self) -> int:
        if (overriden := self._get_overridden("height")) is not None:
            return int(overriden) * self.include

        return int(self._height * (self.scale or 1)) * self.include

    @property
    def ratio(self) -> float:
        width = self.width_fixed or 0
        height = self.height_fixed or 0
        if width != 0 and height != 0:
            return width / height
        return 4 / 3

    @property
    def clip_ratio(self) -> float:
        return self._clip_ratio or 4 / 3

    @clip_ratio.setter
    def clip_ratio(self, value: float) -> None:
        self._clip_ratio = value

    @property
    def xpos(self) -> int:
        if not self._xpos_override:
            if (overriden := self._get_overridden("xpos")) is not None:
                return int(overriden) * self.include
        return self._xpos * self.include

    @xpos.setter
    def xpos(self, value: int) -> None:
        if value is not None:
            self._xpos = int(value)
            self._xpos_override = True
        else:
            self._xpos_override = False

    @property
    def ypos(self) -> int:
        if not self._ypos_override:
            override = self._get_overridden("ypos")
            if override is not None:
                return int(override) * self.include
        return self._ypos * self.include

    @ypos.setter
    def ypos(self, value: int) -> None:
        if value is not None:
            self._ypos = int(value)
            self._ypos_override = True
        else:
            self._ypos_override = False

    @property
    def scale(self) -> float | None:
        return self._scale

    @scale.setter
    def scale(self, value: float | None) -> None:
        if value is None:
            self._scale = None
        elif len(str(value).split("x")) == 1:
            # Scale provided is a multiplier
            self._scale = float(str(value).split("x")[0])
        else:
            # Scale is a resolution.
            parts = str(value).split("x")
            if len(parts) != 2 or not parts[0] or not parts[1]:
                raise ValueError(
                    f"Invalid resolution format: '{value}'. Expected format: "
                    "WIDTHxHEIGHT (e.g., 1920x1080)"
                )
            self.width = int(parts[0])
            self.height = int(parts[1])
            self._scale = 1

    @property
    def options(self) -> str:
        return self._options

    @options.setter
    def options(self, value: str):
        self._options = value

    @property
    def mirror(self) -> bool:
        return self._mirror

    @mirror.setter
    def mirror(self, value: bool) -> None:
        self._mirror = value

    @property
    def mirror_text(self) -> str | None:
        return ", hflip" if self.mirror else ""

    def _get_overridden(self, attr) -> str | int | None:
        try:
            attr_func = getattr(self._layout, f"{self.camera}_{attr}", None)
            return attr_func() if attr_func is not None else None  # type: ignore[misc]
        except (AttributeError, TypeError):
            return None


class MovieLayout(object):
    """Main Layout class"""

    def __init__(self) -> None:
        self._cameras: dict[str, Camera] = {
            "front": Camera(layout=self, camera="front"),
            "left": Camera(layout=self, camera="left"),
            "right": Camera(layout=self, camera="right"),
            "rear": Camera(layout=self, camera="rear"),
            "left_pillar": Camera(layout=self, camera="left_pillar"),
            "right_pillar": Camera(layout=self, camera="right_pillar"),
        }
        self._clip_order: list[str] = [
            "left",
            "right",
            "front",
            "rear",
            "left_pillar",
            "right_pillar",
        ]
        self._font: Font = Font(layout=self)

        self._swap_left_right: bool = False
        self._swap_front_rear: bool = False
        self._swap_pillar: bool = False

        self._perspective: bool = False
        self._title_screen_map: bool = False
        self._event: Event | None = None

        self.background_color = "black"
        self._font.halign = "CENTER"
        self._font.valign = "BOTTOM"

    def cameras(self, camera: str) -> Camera:
        return self._cameras[camera]

    @property
    def clip_order(self) -> list[str]:
        return self._clip_order

    @clip_order.setter
    def clip_order(self, value: list[str]) -> None:
        self._clip_order = []
        for camera in value:
            camera = camera.lower().strip()
            if camera in [
                "front",
                "left",
                "right",
                "rear",
                "left_pillar",
                "right_pillar",
            ]:
                self._clip_order.append(camera)

        # Make sure we have all of them, if not then add based on default order.
        if "left" not in self._clip_order:
            self._clip_order.append("left")
        if "right" not in self._clip_order:
            self._clip_order.append("right")
        if "front" not in self._clip_order:
            self._clip_order.append("front")
        if "rear" not in self._clip_order:
            self._clip_order.append("rear")
        if "left_pillar" not in self._clip_order:
            self._clip_order.append("left_pillar")
        if "right_pillar" not in self._clip_order:
            self._clip_order.append("right_pillar")

    @property
    def font(self) -> Font:
        return self._font

    @font.setter
    def font(self, value: Font) -> None:
        self._font = value

    @property
    def swap_left_right(self) -> bool:
        return self._swap_left_right

    @swap_left_right.setter
    def swap_left_right(self, value: bool) -> None:
        self._swap_left_right = value

    @property
    def swap_front_rear(self) -> bool:
        return self._swap_front_rear

    @swap_front_rear.setter
    def swap_front_rear(self, value: bool) -> None:
        self._swap_front_rear = value

    @property
    def swap_pillar(self) -> bool:
        return self._swap_pillar

    @swap_pillar.setter
    def swap_pillar(self, value: bool) -> None:
        self._swap_pillar = value

    @property
    def perspective(self) -> bool:
        return self._perspective

    @perspective.setter
    def perspective(self, new_perspective: bool) -> None:
        self._perspective = new_perspective

        if self._perspective:
            self.cameras("left").options = FFMPEG_LEFT_PERSPECTIVE
            self.cameras("right").options = FFMPEG_RIGHT_PERSPECTIVE
            self.cameras("left_pillar").options = FFMPEG_LEFT_PERSPECTIVE
            self.cameras("right_pillar").options = FFMPEG_RIGHT_PERSPECTIVE
        else:
            self.cameras("left").options = ""
            self.cameras("right").options = ""
            self.cameras("left_pillar").options = ""
            self.cameras("right_pillar").options = ""

    @property
    def scale(self) -> float:
        # Return scale of new video based on 1280x960 video = scale:1
        return (self.video_height * self.video_width) / (1280 * 960)

    @scale.setter
    def scale(self, scale: float) -> None:
        self.cameras("front").scale = scale
        self.cameras("left").scale = scale
        self.cameras("right").scale = scale
        self.cameras("rear").scale = scale
        self.cameras("left_pillar").scale = scale
        self.cameras("right_pillar").scale = scale

    @property
    def event(self) -> Event | None:
        return self._event

    @event.setter
    def event(self, value: Event) -> None:
        self._event = value

    @property
    def title_screen_map(self) -> bool:
        return self._title_screen_map

    @title_screen_map.setter
    def title_screen_map(self, value: bool):
        self._title_screen_map = value

    @property
    def video_width(self) -> int:
        return int(
            max(
                self.cameras("front").xpos + self.cameras("front").width,
                self.cameras("right").xpos + self.cameras("right").width,
                self.cameras("left_pillar").xpos + self.cameras("left_pillar").width,
                self.cameras("right_pillar").xpos + self.cameras("right_pillar").width,
                self.cameras("left").xpos + self.cameras("left").width,
                self.cameras("rear").xpos + self.cameras("rear").width,
            )
        )

    @property
    def video_height(self) -> int:
        return int(
            max(
                self.cameras("front").ypos + self.cameras("front").height,
                self.cameras("rear").ypos + self.cameras("rear").height,
                self.cameras("left_pillar").ypos + self.cameras("left_pillar").height,
                self.cameras("right_pillar").ypos + self.cameras("right_pillar").height,
                self.cameras("left").ypos + self.cameras("left").height,
                self.cameras("right").ypos + self.cameras("right").height,
            )
        )

    @property
    def center_xpos(self) -> int:
        return int(self.video_width / 2)

    @property
    def center_ypos(self) -> int:
        return int(self.video_height / 2)

    def rear_xpos(self) -> int:
        return self.cameras("front").xpos + self.cameras("front").width

    def left_pillar_ypos(self) -> int:
        return max(
            self.cameras("front").ypos + self.cameras("front").height,
            self.cameras("rear").ypos + self.cameras("rear").height,
        )

    def right_pillar_xpos(self) -> int:
        return self.cameras("left_pillar").xpos + self.cameras("left_pillar").width

    def right_pillar_ypos(self) -> int:
        return self.cameras("left_pillar").ypos

    def left_ypos(self) -> int:
        return max(
            self.cameras("front").ypos + self.cameras("front").height,
            self.cameras("rear").ypos + self.cameras("rear").height,
            self.cameras("left_pillar").ypos + self.cameras("left_pillar").height,
            self.cameras("right_pillar").ypos + self.cameras("right_pillar").height,
        )

    def right_xpos(self) -> int:
        return self.cameras("left").xpos + self.cameras("left").width

    def right_ypos(self) -> int:
        return self.cameras("left").ypos


__all__ = ["Camera", "Font", "MovieLayout"]
