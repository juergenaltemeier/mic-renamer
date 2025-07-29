"""
This module defines the `TagPanel` widget, which displays available tags as interactive
checkboxes. It allows users to filter tags via a search bar, and manage tag selection.
Tag usage statistics influence the display order, and the panel integrates with the
application's tag loading and internationalization features.
"""
import logging

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QScrollArea
from PySide6.QtCore import Signal, Qt, QEvent
from PySide6.QtGui import QKeyEvent
from ..components import TagBox
from ..constants import DEFAULT_MARGIN, DEFAULT_SPACING
from ..flow_layout import FlowLayout

from ...logic.tag_loader import load_tags
from ...logic.tag_usage import load_counts
from ...utils.i18n import tr

logger = logging.getLogger(__name__)


class TagPanel(QWidget):
    """
    A panel widget that displays available tags as a collection of checkboxes.

    It includes a search bar for filtering tags and allows for dynamic updates
    based on language changes or tag usage statistics. Tags can be toggled,
    and the panel emits signals when a tag's state changes or arrow keys are pressed.
    """

    # Signal emitted when a tag's checkbox is toggled.
    # Arguments: (tag_code: str, state: int (Qt.CheckState.Checked/Unchecked/PartiallyChecked))
    tagToggled = Signal(str, int)
    # Signal emitted when arrow keys (Up/Down) are pressed in the search bar.
    # Arguments: (key: int (Qt.Key_Up/Qt.Key_Down))
    arrowKeyPressed = Signal(int)

    def __init__(self, parent: QWidget | None = None, tags_info: dict | None = None):
        """
        Initializes the TagPanel.

        Args:
            parent (QWidget | None): The parent widget. Defaults to None.
            tags_info (dict | None): Optional initial dictionary of tags (code: description).
                                     If None, tags are loaded internally.
        """
        super().__init__(parent)
        self._log = logging.getLogger(__name__) # Use a dedicated logger for this class.
        self._preselected_tag: TagBox | None = None # Stores the currently preselected (highlighted) tag.
        logger.info("TagPanel initialized.")

        layout = QVBoxLayout(self) # Main vertical layout for the panel.
        layout.setContentsMargins(
            DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN
        )
        layout.setSpacing(DEFAULT_SPACING)

        # Search bar for filtering tags.
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(tr("search_tags")) # Set placeholder text from translations.
        self.search_bar.textChanged.connect(self._filter_tags) # Connect text changes to filter method.
        # Override keyPressEvent to handle Enter/Arrow keys for tag interaction.
        self.search_bar.keyPressEvent = self._handle_search_key_press # type: ignore
        layout.addWidget(self.search_bar)
        logger.debug("Search bar added to TagPanel.")

        # Container for tag checkboxes, using a FlowLayout.
        self.checkbox_container = QWidget()
        self.tag_layout = FlowLayout(self.checkbox_container) # Use FlowLayout for wrapping tags.
        # Remove margins and add minimal spacing to fit more tags tightly.
        self.tag_layout.setContentsMargins(0, 0, 0, 0)
        self.tag_layout.setSpacing(2)
        
        # Wrap tag container in a scroll area for overflow.
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.checkbox_container)
        self.scroll_area.setWidgetResizable(True) # Allow the widget inside to resize.
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        layout.addWidget(self.scroll_area)
        logger.debug("Tag checkbox container and scroll area added.")

        self.checkbox_map: dict[str, TagBox] = {} # Map tag codes to TagBox instances.
        self.tags_info: dict[str, str] | None = tags_info # Store initial tags info.
        self.rebuild() # Populate the tags initially.

    def _handle_search_key_press(self, event: QKeyEvent) -> None:
        """
        Custom key press event handler for the search bar.

        - On Enter/Return: Toggles the currently preselected tag.
        - On Down/Up arrow: Emits `arrowKeyPressed` signal for external handling (e.g., navigating main table).
        - Other keys: Pass to the default QLineEdit keyPressEvent.

        Args:
            event (QKeyEvent): The key press event.
        """
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self._preselected_tag:
                self._preselected_tag.toggle() # Toggle the preselected tag.
                logger.debug(f"Toggled preselected tag '{self._preselected_tag.code}' via Enter key.")
            event.accept() # Mark event as handled.
        elif event.key() == Qt.Key_Down:
            self.arrowKeyPressed.emit(Qt.Key_Down) # Emit signal for Down arrow.
            event.accept()
            logger.debug("Down arrow key pressed in search bar.")
        elif event.key() == Qt.Key_Up:
            self.arrowKeyPressed.emit(Qt.Key_Up) # Emit signal for Up arrow.
            event.accept()
            logger.debug("Up arrow key pressed in search bar.")
        else:
            # For all other keys, call the original QLineEdit keyPressEvent.
            QLineEdit.keyPressEvent(self.search_bar, event)

    def _move_preselection(self, direction: int) -> None:
        """
        Moves the preselection (highlight) to the next/previous visible tag.

        Args:
            direction (int): +1 for next, -1 for previous.
        """
        visible_tags = [cb for cb in self.checkbox_map.values() if cb.isVisible()] # Get only currently visible tags.
        if not visible_tags:
            logger.debug("No visible tags to move preselection.")
            return

        current_index = -1
        if self._preselected_tag and self._preselected_tag in visible_tags:
            current_index = visible_tags.index(self._preselected_tag)

        new_index = (current_index + direction) % len(visible_tags) # Calculate new index, wrapping around.
        self._update_preselection(visible_tags[new_index]) # Update the preselected tag.
        logger.debug(f"Moved preselection to index {new_index} (tag: {visible_tags[new_index].code}).")

    def _update_preselection(self, new_tag: TagBox | None) -> None:
        """
        Updates the currently preselected tag, removing highlight from the old one.

        Args:
            new_tag (TagBox | None): The new TagBox to preselect, or None to clear preselection.
        """
        if self._preselected_tag:
            self._preselected_tag.set_preselected(False) # Remove preselection from old tag.
        
        self._preselected_tag = new_tag # Set the new preselected tag.
        
        if self._preselected_tag:
            self._preselected_tag.set_preselected(True) # Apply preselection to new tag.
            logger.debug(f"Preselection updated to tag: {new_tag.code if new_tag else 'None'}")

    def _filter_tags(self, text: str) -> None:
        """
        Filters the displayed tag checkboxes based on the search bar text.

        Only tags whose code or description contains the search text (case-insensitive)
        are shown. The first visible tag is automatically preselected.

        Args:
            text (str): The text from the search bar.
        """
        text = text.lower() # Convert search text to lowercase for case-insensitive comparison.
        first_visible: TagBox | None = None
        logger.debug(f"Filtering tags with search text: '{text}'")

        for code, checkbox in self.checkbox_map.items():
            description = self.tags_info.get(code, "") # Get description for the tag.
            # Check if search text is in tag code or description.
            if text in code.lower() or text in description.lower():
                checkbox.show() # Show the checkbox.
                if first_visible is None:
                    first_visible = checkbox # Keep track of the first visible tag.
            else:
                checkbox.hide() # Hide the checkbox.
        
        self._update_preselection(first_visible) # Update preselection to the first visible tag.
        logger.debug("Tag filtering complete.")

    def rebuild(self, language: str | None = None) -> None:
        """
        Rebuilds the tag checkboxes in the panel.

        This method clears all existing tags, reloads them (optionally for a specific language),
        sorts them by usage count, and then recreates the `TagBox` widgets.

        Args:
            language (str | None): The language code to load tags for. If None, uses default.
        """
        logger.info(f"Rebuilding TagPanel for language: {language or 'default'}")
        # Clear any existing preselection to avoid operating on deleted widgets.
        self._preselected_tag = None
        
        # Clear existing checkboxes from the layout and the map.
        while self.tag_layout.count() > 0:
            item = self.tag_layout.takeAt(0)
            if item is None: # Add this check
                continue
            if item.widget():
                widget = item.widget()
                self.tag_layout.removeWidget(widget) # Remove from layout.
                widget.deleteLater() # Schedule for deletion.
        self.checkbox_map.clear() # Clear the map of checkboxes.

        # Always reload tags to pick up language or file changes.
        tags: dict
        try:
            tags = load_tags(language=language) # Load tags, potentially with language filter.
        except TypeError:
            # Fallback for load_tags mocks that do not accept parameters (e.g., during testing).
            tags = load_tags()
            self._log.warning("load_tags called without language parameter due to TypeError. Possibly a mock issue.")
        except Exception as e:
            self._log.error(f"Failed to load tags during rebuild: {e}. Using empty tags.")
            tags = {}
        
        if not isinstance(tags, dict):
            self._log.warning(f"Invalid tags info, expected dict but got {type(tags).__name__}. Using empty tags.")
            tags = {}
        self.tags_info = tags # Store the loaded tags information.
        
        if not self.tags_info: # If no tags are loaded, display a message.
            self.tag_layout.addWidget(QLabel(tr("no_tags_configured")))
            logger.info("No tags configured. Displaying message.")
            return
        
        usage = load_counts() # Load tag usage counts for sorting.
        
        # Ensure tags_info.items() is iterable before sorting.
        tags_info_items = self.tags_info.items() if isinstance(self.tags_info, dict) else []
        
        # Sort tags by usage count (most used first), then alphabetically by code.
        sorted_tags = sorted(
            tags_info_items, key=lambda kv: (usage.get(kv[0], 0), kv[0]), reverse=True
        )
        logger.debug(f"Loaded and sorted {len(sorted_tags)} tags.")
        
        # Create or update TagBox widgets for each sorted tag.
        for code, desc in sorted_tags:
            code_upper = code.upper()
            # Check if a TagBox for this code already exists (e.g., during language change).
            if code_upper in self.checkbox_map:
                cb = self.checkbox_map[code_upper]
                cb.set_text(code_upper, desc) # Update text if it exists.
                logger.debug(f"Updated existing TagBox for {code_upper}.")
            else:
                # Create a new TagBox.
                cb = TagBox(code_upper, desc)
                # Connect the toggled signal to emit our custom signal.
                cb.toggled.connect(
                    lambda state, c=code_upper: self.tagToggled.emit(c, state)
                )
                self.tag_layout.addWidget(cb) # Add to layout.
                self.checkbox_map[code_upper] = cb # Store in map.
                logger.debug(f"Created new TagBox for {code_upper}.")

    def retranslate_ui(self, language: str | None = None) -> None:
        """
        Retranslates the UI elements of the TagPanel when the application language changes.

        Args:
            language (str | None): The new language code. If None, uses the current language.
        """
        self.search_bar.setPlaceholderText(tr("search_tags")) # Update search bar placeholder.
        self.rebuild(language=language) # Rebuild tags to apply new language descriptions.
        logger.info(f"TagPanel UI retranslated for language: {language or 'current'}.")
