from __future__ import annotations

from .base import MovieLayout


class FullScreen(MovieLayout):
    """FullScreen Movie Layout

    [LEFT-PILLAR_CAMERA][FRONT_CAMERA][RIGHT-PILLAR_CAMERA]
    [   LEFT_CAMERA    ][REAR_CAMERA ][   RIGHT_CAMERA    ]
    """

    def __init__(self) -> None:
        super().__init__()
        self.scale = 1 / 2

    @property
    def _top_row_width(self) -> int:
        return (
            self.cameras("left_pillar").width
            + self.cameras("front").width
            + self.cameras("right_pillar").width
        )

    @property
    def _bottom_row_width(self) -> int:
        return (
            self.cameras("left").width
            + self.cameras("rear").width
            + self.cameras("right").width
        )

    @property
    def _row_width(self) -> int:
        # Use the maximum of the top and bottom row width.
        return max(self._top_row_width, self._bottom_row_width)

    @property
    def _top_row_xpos(self) -> int:
        # Make sure that top row is centered.
        return int(self._row_width / 2) - int(self._top_row_width / 2)

    @property
    def _bottom_row_xpos(self) -> int:
        # Make sure that bottom row is centered.
        return int(self._row_width / 2) - int(self._bottom_row_width / 2)

    @property
    def _top_row_height(self) -> int:
        return max(
            self.cameras("left_pillar").height,
            self.cameras("front").height,
            self.cameras("right_pillar").height,
        )

    @property
    def _bottom_row_height(self) -> int:
        return max(
            self.cameras("left").height,
            self.cameras("rear").height,
            self.cameras("right").height,
        )

    @property
    def _row_height(self) -> int:
        # Use the maximum of the top and bottom row height.
        return self._top_row_height + self._bottom_row_height

    @property
    def _top_row_ypos(self) -> int:
        # Make sure that top row is centered.
        return 0

    @property
    def _bottom_row_ypos(self) -> int:
        # Make sure that bottom row is centered.
        return self._top_row_height

    # We can't use video width or center_xpos as they use the positions to calculate.
    def left_pillar_xpos(self) -> int:
        # left_pillar is put on the left but ensuring that the row is centered
        return self._top_row_xpos

    def front_xpos(self) -> int:
        # front is placed next to left_pillar, we need to use width as left pillar
        # might not be included
        return self._top_row_xpos + self.cameras("left_pillar").width

    def right_pillar_xpos(self) -> int:
        # right_pillar is placed next to front, we need to use width as left pillar or
        # front might not be included
        return (
            self._top_row_xpos
            + self.cameras("left_pillar").width
            + self.cameras("front").width
        )

    # We can't use video width or center_xpos as they use the positions to calculate.
    def left_xpos(self) -> int:
        # left is put on the left but ensuring that the row is centered
        return self._bottom_row_xpos

    def rear_xpos(self) -> int:
        # rear is placed next to left, we need to use width as left might not be
        # included
        return self._bottom_row_xpos + self.cameras("left").width

    def right_xpos(self) -> int:
        # right is placed next to rear, we need to use width as left and rear might not
        # be included
        return (
            self._bottom_row_xpos
            + self.cameras("left").width
            + self.cameras("rear").width
        )

    def front_height(self) -> int:
        # For height keep same ratio as original clip
        return int(self.cameras("front").width / self.cameras("front").ratio)

    def left_pillar_ypos(self) -> int:
        return self._top_row_ypos + int(
            (self._top_row_height - self.cameras("left_pillar").height) / 2
        )

    def front_ypos(self) -> int:
        return self._top_row_ypos + int(
            (self._top_row_height - self.cameras("front").height) / 2
        )

    def right_pillar_ypos(self) -> int:
        return self._top_row_ypos + int(
            (self._top_row_height - self.cameras("right_pillar").height) / 2
        )

    def left_ypos(self) -> int:
        return self._bottom_row_ypos + int(
            (self._bottom_row_height - self.cameras("left").height) / 2
        )

    def rear_ypos(self) -> int:
        return self._bottom_row_ypos + int(
            (self._bottom_row_height - self.cameras("rear").height) / 2
        )

    def right_ypos(self) -> int:
        return self._bottom_row_ypos + int(
            (self._bottom_row_height - self.cameras("right").height) / 2
        )


class Mosaic(FullScreen):
    """Mosaic Movie Layout

    [LEFT-PILLAR_CAMERA][           FRONT_CAMERA             ][RIGHT-PILLAR_CAMERA]
    [       LEFT_CAMERA        ][    REAR_CAMERA     ][       RIGHT_CAMERA        ]

    or

    [LEFT-PILLAR_CAMERA][FRONT_CAMERA][RIGHT-PILLAR_CAMERA]
    [LEFT_CAMERA][       REAR_CAMERA        ][RIGHT_CAMERA]
    """

    def __init__(self) -> None:
        """Initialize Mosaic Layout."""
        super().__init__()
        self.scale = 1 / 2
        # Set front scale to None so we know if it was overriden or not.
        self.cameras("front").scale = None
        self.cameras("rear").scale = None
        # Boost factor to emphasize front/rear when pillars and sides present
        self._front_rear_boost: float = 1.3

    @property
    def front_rear_boost(self) -> float:
        return self._front_rear_boost

    @front_rear_boost.setter
    def front_rear_boost(self, value: float) -> None:
        self._front_rear_boost = max(1.0, float(value))

    def _boost_active(self) -> bool:
        # Always apply boost to keep front/rear emphasized consistently
        return True

    @property
    def _front_normal_scale(self) -> int:
        scale = self.cameras("front").scale or 0.5
        return int(self.cameras("front").width_fixed * scale)

    @property
    def _min_top_row_width(self) -> int:
        return (
            self.cameras("left_pillar").width
            + self._front_normal_scale
            + self.cameras("right_pillar").width
        )

    @property
    def _rear_normal_scale(self) -> int:
        scale = self.cameras("rear").scale or 0.5
        return int(self.cameras("rear").width_fixed * scale)

    @property
    def _min_bottom_row_width(self) -> int:
        return int(
            self.cameras("left").width
            + self._rear_normal_scale
            + self.cameras("right").width
        )

    # Adjust front width if bottom row is wider then top row
    def front_width(self) -> int:
        if self.cameras("front").scale is None:
            # Front width should be:
            #  max(bottom_row_width, min_top_width) - pillar_widths
            base_target = max(self._min_bottom_row_width, self._min_top_row_width)
            target_width = (
                int(base_target * self._front_rear_boost)
                if self._boost_active()
                else base_target
            )
            return max(
                self._front_normal_scale,
                target_width
                - self.cameras("left_pillar").width
                - self.cameras("right_pillar").width,
            )
        else:
            # Use normal scale calculation if front camera scale was explicitly set
            return self._front_normal_scale

    def front_height(self) -> int:
        # Preserve aspect ratio: if width is dynamically set (scale None),
        # derive height from width and clip ratio.
        if self.cameras("front").scale is None:
            return int(self.cameras("front").width / self.cameras("front").ratio)
        # Otherwise use explicit scale on original height.
        scale = self.cameras("front").scale or 1
        return int(self.cameras("front").height_fixed * scale)

    # Adjust rear width if bottom row is wider then top row
    def rear_width(self) -> int:
        if self.cameras("rear").scale is None:
            # Rear width should be:
            #  max(bottom_row_width, min_top_width) - left/right widths
            base_target = max(self._min_bottom_row_width, self._min_top_row_width)
            target_width = (
                int(base_target * self._front_rear_boost)
                if self._boost_active()
                else base_target
            )
            return max(
                self._rear_normal_scale,
                target_width - self.cameras("left").width - self.cameras("right").width,
            )
        else:
            # Use normal scale calculation if front camera scale was explicitly set
            return self._rear_normal_scale

    def rear_height(self) -> int:
        # Preserve aspect ratio: if width is dynamically set (scale None),
        # derive height from width and clip ratio.
        if self.cameras("rear").scale is None:
            return int(self.cameras("rear").width / self.cameras("rear").ratio)
        # Otherwise use explicit scale on original height.
        scale = self.cameras("rear").scale or 1
        return int(self.cameras("rear").height_fixed * scale)


class Cross(MovieLayout):
    """Cross Movie Layout

               [   FRONT_CAMERA    ]
    [LEFT-PILLAR_CAMERA][RIGHT-PILLAR_CAMERA]
    [   LEFT_CAMERA    ][   RIGHT_CAMERA    ]
               [   REAR_CAMERA    ]
    """

    def __init__(self) -> None:
        super().__init__()
        self.scale = 1 / 2

    @property
    def _pillar_row_width(self) -> int:
        return self.cameras("left_pillar").width + self.cameras("right_pillar").width

    @property
    def _repeater_row_width(self) -> int:
        return self.cameras("left").width + self.cameras("right").width

    @property
    def _row_width(self) -> int:
        return max(
            self.cameras("front").width,
            self._pillar_row_width,
            self._repeater_row_width,
            self.cameras("rear").width,
        )

    @property
    def _pillar_row_xpos(self) -> int:
        return int(self._row_width / 2) - int(self._pillar_row_width / 2)

    @property
    def _repeater_row_xpos(self) -> int:
        return int(self._row_width / 2) - int(self._repeater_row_width / 2)

    @property
    def _pillar_row_height(self) -> int:
        return max(
            self.cameras("left_pillar").height, self.cameras("right_pillar").height
        )

    @property
    def _repeater_row_height(self) -> int:
        return max(self.cameras("left").height, self.cameras("right").height)

    @property
    def _pillar_row_ypos(self) -> int:
        return self.cameras("front").height

    @property
    def _repeater_row_ypos(self) -> int:
        return self.cameras("front").height + self._pillar_row_height

    def front_xpos(self) -> int:
        return int(self._row_width / 2) - int(self.cameras("front").width / 2)

    def left_pillar_xpos(self) -> int:
        return self._pillar_row_xpos

    def right_pillar_xpos(self) -> int:
        return self._pillar_row_xpos + self.cameras("left_pillar").width

    def left_xpos(self) -> int:
        return self._repeater_row_xpos

    def right_xpos(self) -> int:
        return self._repeater_row_xpos + self.cameras("left").width

    def rear_xpos(self) -> int:
        return int(self._row_width / 2) - int(self.cameras("rear").width / 2)

    def left_pillar_ypos(self) -> int:
        return self._pillar_row_ypos + int(
            (self._pillar_row_height - self.cameras("left_pillar").height) / 2
        )

    def right_pillar_ypos(self) -> int:
        return self._pillar_row_ypos + int(
            (self._pillar_row_height - self.cameras("right_pillar").height) / 2
        )

    def left_ypos(self) -> int:
        return self._repeater_row_ypos + int(
            (self._repeater_row_height - self.cameras("left").height) / 2
        )

    def right_ypos(self) -> int:
        return self._repeater_row_ypos + int(
            (self._repeater_row_height - self.cameras("right").height) / 2
        )

    def rear_ypos(self) -> int:
        return (
            self.cameras("front").height
            + self._pillar_row_height
            + self._repeater_row_height
        )


class Diamond(MovieLayout):
    """Diamond Movie Layout

                        [            ]
    [LEFT-PILLAR_CAMERA][FRONT_CAMERA][RIGHT-PILLAR_CAMERA]
    [   LEFT_CAMERA    ][REAR_CAMERA ][   RIGHT_CAMERA    ]
                        [            ]
    """

    def __init__(self) -> None:
        super().__init__()
        self._font.valign = "MIDDLE"
        self.scale = 1 / 2
        self.cameras("front").scale = 1
        self.cameras("rear").scale = 1

    @property
    def _left_column_width(self) -> int:
        return max(self.cameras("left_pillar").width, self.cameras("left").width)

    @property
    def _front_rear_column_width(self) -> int:
        return max(self.cameras("front").width, self.cameras("rear").width)

    @property
    def _right_column_width(self) -> int:
        return max(self.cameras("right_pillar").width, self.cameras("right").width)

    @property
    def _pillar_row_height(self) -> int:
        return max(
            self.cameras("left_pillar").height, self.cameras("right_pillar").height
        )

    @property
    def _repeater_row_height(self) -> int:
        return max(self.cameras("left").height, self.cameras("right").height)

    @property
    def _pillar_repeater_row_height(self) -> int:
        return self._pillar_row_height + self._repeater_row_height

    @property
    def _left_column_height(self) -> int:
        return self.cameras("left_pillar").height + self.cameras("left").height

    @property
    def _front_rear_height(self) -> int:
        return self.cameras("front").height + self.cameras("rear").height

    @property
    def _right_column_height(self) -> int:
        return self.cameras("right_pillar").height + self.cameras("right").height

    def front_xpos(self) -> int:
        return self._left_column_width + int(
            (self._front_rear_column_width - self.cameras("front").width) / 2
        )

    def left_pillar_xpos(self) -> int:
        return self._left_column_width - self.cameras("left_pillar").width

    def left_xpos(self) -> int:
        return self._left_column_width - self.cameras("left").width

    def right_pillar_xpos(self) -> int:
        return self._left_column_width + self._front_rear_column_width

    def right_xpos(self) -> int:
        return self._left_column_width + self._front_rear_column_width

    def rear_xpos(self) -> int:
        return self._left_column_width + int(
            (self._front_rear_column_width - self.cameras("rear").width) / 2
        )

    def front_ypos(self) -> int:
        return int(
            max(
                0,
                (
                    max(self._left_column_height, self._right_column_height)
                    - self._front_rear_height
                )
                / 2,
            )
        )

    def left_pillar_ypos(self) -> int:
        return int(max(0, (self._front_rear_height - self._left_column_height) / 2))

    def left_ypos(self) -> int:
        return int(
            (
                max(0, (self._front_rear_height - self._left_column_height) / 2)
                + self.cameras("left_pillar").height
            )
        )

    def right_pillar_ypos(self) -> int:
        return int(max(0, (self._front_rear_height - self._right_column_height) / 2))

    def right_ypos(self) -> int:
        return int(
            max(0, (self._front_rear_height - self._right_column_height) / 2)
            + self.cameras("right_pillar").height
        )

    def rear_ypos(self) -> int:
        return int(
            max(
                0,
                (
                    max(self._left_column_height, self._right_column_height)
                    - self._front_rear_height
                )
                / 2,
            )
            + self.cameras("front").height
        )


class Horizontal(MovieLayout):
    """Horizontal Movie Layout

    [LEFT_CAMERA][LEFT_PILLAR][FRONT_CAMERA][REAR_CAMERA][RIGHT_PILLAR][RIGHT_CAMERA]
    """

    def __init__(self) -> None:
        """Initialize Horizontal Layout."""
        super().__init__()
        self.scale = 1 / 2

    @property
    def _row_height(self) -> int:
        return max(
            self.cameras("left").height,
            self.cameras("left_pillar").height,
            self.cameras("front").height,
            self.cameras("rear").height,
            self.cameras("right_pillar").height,
            self.cameras("right").height,
        )

    def left_ypos(self) -> int:
        return int((self._row_height - self.cameras("left").height) / 2)

    def left_pillar_xpos(self) -> int:
        return self.cameras("left").width

    def left_pillar_ypos(self) -> int:
        return int((self._row_height - self.cameras("left_pillar").height) / 2)

    def front_xpos(self) -> int:
        return self.cameras("left").width + self.cameras("left_pillar").width

    def front_ypos(self) -> int:
        return int((self._row_height - self.cameras("front").height) / 2)

    def rear_xpos(self) -> int:
        return (
            self.cameras("left").width
            + self.cameras("left_pillar").width
            + self.cameras("front").width
        )

    def rear_ypos(self) -> int:
        return int((self._row_height - self.cameras("rear").height) / 2)

    def right_pillar_xpos(self) -> int:
        return (
            self.cameras("left").width
            + self.cameras("left_pillar").width
            + self.cameras("front").width
            + self.cameras("rear").width
        )

    def right_pillar_ypos(self) -> int:
        return int((self._row_height - self.cameras("right_pillar").height) / 2)

    def right_xpos(self) -> int:
        return (
            self.cameras("left").width
            + self.cameras("left_pillar").width
            + self.cameras("front").width
            + self.cameras("rear").width
            + self.cameras("right_pillar").width
        )

    def right_ypos(self) -> int:
        return int((self._row_height - self.cameras("right").height) / 2)


__all__ = ["Cross", "Diamond", "FullScreen", "Horizontal", "Mosaic"]
