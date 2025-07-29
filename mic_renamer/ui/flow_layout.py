"""
This module implements a custom `FlowLayout` for PyQt/PySide applications.

`FlowLayout` is a layout manager that arranges child widgets horizontally
and automatically wraps them to the next row when the available width is exceeded.
This is particularly useful for dynamic content like tag displays where the number
and size of items can vary.
"""

from PySide6.QtWidgets import QLayout, QWidgetItem, QWidget
from PySide6.QtCore import QRect, QSize, Qt
import logging

from .constants import DEFAULT_MARGIN, DEFAULT_SPACING

logger = logging.getLogger(__name__)


class FlowLayout(QLayout):
    """
    A custom layout manager that arranges widgets in a flow-like manner.

    Widgets are laid out horizontally until the available width is filled,
    then they wrap to the next line. This provides a flexible and responsive
    layout for varying numbers and sizes of child widgets.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        margin: int = DEFAULT_MARGIN,
        spacing: int | None = DEFAULT_SPACING,
    ) -> None:
        """
        Initializes the FlowLayout.

        Args:
            parent (QWidget | None): The parent widget of this layout. Defaults to None.
            margin (int): The margin around the contents of the layout. Defaults to `DEFAULT_MARGIN`.
            spacing (int | None): The spacing between items in the layout. Defaults to `DEFAULT_SPACING`.
        """
        super().__init__(parent)
        self._items: list[QWidgetItem] = [] # List to hold QWidgetItem objects managed by this layout.
        
        # Set content margins if a parent widget is provided.
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
            logger.debug(f"FlowLayout margins set to {margin}.")
        
        # Set spacing between items.
        if spacing is not None:
            self.setSpacing(spacing)
            logger.debug(f"FlowLayout spacing set to {spacing}.")
        logger.info("FlowLayout initialized.")

    # QLayout API Overrides -----------------------------------------------------

    def addItem(self, item: QWidgetItem) -> None:
        """
        Adds an item to the layout.

        This method is part of the QLayout API and is called when a widget or
        another layout is added to this flow layout.

        Args:
            item (QWidgetItem): The item to add to the layout.
        """
        self._items.append(item)
        logger.debug(f"Item added to FlowLayout: {item.widget().objectName() if item.widget() else 'unknown'}")

    def count(self) -> int:
        """
        Returns the number of items in the layout.

        Returns:
            int: The total number of QWidgetItem objects currently managed by this layout.
        """
        return len(self._items)

    def itemAt(self, index: int) -> QWidgetItem | None:
        """
        Returns the item at the given index.

        Args:
            index (int): The zero-based index of the item to retrieve.

        Returns:
            QWidgetItem | None: The QWidgetItem at the specified index, or None if the index is out of bounds.
        """
        if 0 <= index < len(self._items):
            return self._items[index]
        logger.debug(f"Attempted to access item at invalid index: {index}. Layout has {len(self._items)} items.")
        return None

    def takeAt(self, index: int) -> QWidgetItem | None:
        """
        Removes the item at the given index from the layout and returns it.

        Args:
            index (int): The zero-based index of the item to remove.

        Returns:
            QWidgetItem | None: The removed QWidgetItem, or None if the index is out of bounds.
        """
        if 0 <= index < len(self._items):
            item = self._items.pop(index)
            logger.debug(f"Item removed from FlowLayout at index {index}: {item.widget().objectName() if item.widget() else 'unknown'}")
            return item
        logger.debug(f"Attempted to remove item at invalid index: {index}. Layout has {len(self._items)} items.")
        return None

    def expandingDirections(self) -> Qt.Orientations:
        """
        Returns the directions in which this layout can expand.

        FlowLayout does not expand in any particular direction beyond its contents,
        so it returns Qt.Orientations(0).

        Returns:
            Qt.Orientations: A bitwise OR of Qt.Orientation values indicating expansion capabilities.
        """
        return Qt.Orientations(0)

    def hasHeightForWidth(self) -> bool:
        """
        Indicates whether this layout's preferred height depends on its width.

        FlowLayout's height changes based on its width (as items wrap),
        so this method returns True.

        Returns:
            bool: True if the height depends on the width, False otherwise.
        """
        return True

    def heightForWidth(self, width: int) -> int:
        """
        Calculates the preferred height for a given width.

        This method is crucial for layouts that wrap content. It performs a layout
        simulation (`_do_layout` with `test_only=True`) to determine the required height.

        Args:
            width (int): The available width for the layout.

        Returns:
            int: The calculated preferred height.
        """
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QRect) -> None:
        """
        Sets the geometry of the layout and arranges its items.

        This method is called by the parent widget to inform the layout of its
        available space. It then triggers the actual arrangement of child widgets.

        Args:
            rect (QRect): The rectangle defining the available geometry for the layout.
        """
        super().setGeometry(rect)
        self._do_layout(rect, False)
        logger.debug(f"FlowLayout geometry set to {rect.width()}x{rect.height()}.")

    def sizeHint(self) -> QSize:
        """
        Returns the recommended size for the layout.

        For a flow layout, the size hint is typically its minimum size, as it can
        adapt to various sizes by wrapping.

        Returns:
            QSize: The recommended size.
        """
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        """
        Calculates the minimum size required by the layout.

        This is determined by the largest minimum size hint of its child items,
        plus the layout's margins.

        Returns:
            QSize: The minimum size the layout can take while still displaying all its contents.
        """
        size = QSize()
        # Expand the size to accommodate the largest minimum size hint of any item.
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        
        # Add content margins to the calculated size.
        left, top, right, bottom = self.getContentsMargins()
        size += QSize(left + right, top + bottom)
        logger.debug(f"FlowLayout minimum size calculated: {size.width()}x{size.height()}")
        return size

    # Internal Layout Logic --------------------------------------------------------

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        """
        Performs the actual layout of items within the given rectangle.

        This is a core internal method that calculates the position and size of each
        child widget. It simulates the flow layout behavior, wrapping items to new
        lines when they exceed the available width.

        Args:
            rect (QRect): The rectangle representing the available space for layout.
            test_only (bool): If True, only calculates the required height without
                              actually setting the geometry of the items. This is used
                              by `heightForWidth`.

        Returns:
            int: The total height required by the layout for the given width.
        """
        left, top, right, bottom = self.getContentsMargins()
        # Calculate the effective rectangle where items can be placed, considering margins.
        effective_rect = rect.adjusted(left, top, -right, -bottom)
        
        x = effective_rect.x() # Current X position for placing items.
        y = effective_rect.y() # Current Y position for placing items (current row's top).
        line_height = 0 # Tracks the maximum height of items in the current line.

        for item in self._items:
            item_widget = item.widget()
            if item_widget is None or not item_widget.isVisible():
                continue # Skip invisible or None widgets

            hint = item.sizeHint() # Get the preferred size of the current item.
            space_x = self.spacing() # Horizontal spacing between items.
            space_y = self.spacing() # Vertical spacing between lines.
            
            # Calculate the potential X position for the next item.
            next_x = x + hint.width() + space_x
            
            # Check if the current item would exceed the effective right boundary
            # and if there's already content on the current line (line_height > 0).
            # If so, wrap to the next line.
            if next_x - space_x > effective_rect.right() and line_height > 0:
                x = effective_rect.x() # Reset X to the beginning of the effective rectangle.
                y = y + line_height + space_y # Move Y down to the next line.
                next_x = x + hint.width() + space_x # Recalculate next X for the new line.
                line_height = 0 # Reset line height for the new line.
                logger.debug(f"FlowLayout: Wrapped to new line at Y={y}")

            # If not in test-only mode, set the actual geometry of the item.
            if not test_only:
                item.setGeometry(QRect(x, y, hint.width(), hint.height()))
                logger.debug(f"FlowLayout: Set geometry for item at ({x},{y}) with size {hint.width()}x{hint.height()}")
            
            x = next_x # Advance X position for the next item.
            line_height = max(line_height, hint.height()) # Update max height for the current line.

        # Calculate the total height used by the layout.
        # This includes the Y position of the last line, its height, and the bottom margin.
        total_height = y + line_height - rect.y() + top + bottom
        logger.debug(f"FlowLayout: _do_layout finished. Total height: {total_height}")
        return total_height
