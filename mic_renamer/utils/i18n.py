from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

current_language = "en"

TRANSLATIONS: dict[str, dict[str, str]] = {
    'en': {
        'app_title': 'Micavac Renamer',
        'restore_session': 'Restore Session',
        'restore_session_msg': 'A previous session was found. Do you want to restore it?',
        'session_saved': 'Session saved',
        'session_not_saved': 'Session not saved',
        'edit_menu': 'Edit',
        'tip_restore_session': 'Restore the last saved session',
        'no_session_to_restore': 'No session to restore.',
        'session_restored_successfully': 'Session restored successfully.',
        'session_restore_failed': 'Failed to restore session.',
        'project_number_label': 'MC-No.:',
        'project_number_placeholder': 'C123456',
        'selected_file_label': 'Selected File:',
        'custom_suffix_label': 'Custom Suffix for this file:',
        'custom_suffix_placeholder': 'e.g. DSC00138',
        'select_tags_label': 'Select Tags for this file:',
        'add_menu': 'Add',
        'add_files': 'Add Files...', 
        'add_folder': 'Add Folder...', 
        'add_folder_recursive': 'Add Folder and Subfolders...', 
        'preview_rename': 'Preview Rename',
        'rename_all': 'Rename All',
        'rename_selected': 'Rename Selected Only',
        'clear_list': 'Clear List',
        'compress': 'Compress',
        'convert_heic': 'Convert to JPEG',
        'missing_project': 'Missing Project Number',
        'missing_project_msg': 'Please enter MC-No. (C followed by 6 digits).',
        'no_files': 'No Files',
        'no_files_msg': 'No files to rename.',
        'confirm_rename': 'Confirm Rename',
        'confirm_rename_msg': 'Rename without preview?',
        'rename_failed': 'Rename Failed',
        'partial_rename': 'Partial Rename',
        'partial_rename_msg': 'Canceled: {done} of {total} files renamed.',
        'done': 'Done',
        'rename_done': 'All files renamed.',
        'settings_title': 'Settings',
        'compression_settings': 'Compression',
        'max_size_label': 'Max Size (KB):',
        'max_size_desc': 'Target maximum file size after compression',
        'quality_label': 'JPEG Quality:',
        'quality_desc': 'JPEG quality percentage',
        'reduce_resolution_label': 'Reduce resolution if needed',
        'reduce_resolution_desc': 'Lower image resolution if needed',
        'resize_only_label': 'Resize only',
        'resize_only_desc': 'Resize images without recompressing',
        'max_width_label': 'Max Width (px):',
        'max_width_desc': 'Resize images wider than this width (0 = no limit)',
        'max_height_label': 'Max Height (px):',
        'max_height_desc': 'Resize images taller than this height (0 = no limit)',
        'compression_done': 'Compression finished.',
        'rename_options_title': 'Rename Options',
        'compression_window_title': 'Compression Preview',
        'compression_ok_info': 'Images will be compressed after clicking OK.',
        'file': 'File',
        'old_size': 'Old Size',
        'new_size': 'New Size',
        'reduction': 'Reduction',
        'video_unsupported': 'Videos not supported',
        'video_unsupported_msg': 'Selected videos cannot be compressed.',
        'heic_convert_title': 'Convert HEIC',
        'heic_convert_msg': 'Convert HEIC images to JPEG before compressing?',
        'show_tags': 'Show tags',
        'hide_tags': 'Hide tags',
        'accepted_ext_label': 'Accepted File Extensions (comma separated):',
        'accepted_ext_desc': 'File types to show in the file browser',
        'language_label': 'Language:',
        'language_desc': 'Language for interface texts',
        'tags_label': 'Tags',
        'restore_defaults': 'Restore Defaults',
        'reset_tag_usage': 'Reset Tag Usage',
        'remove_selected': 'Remove Selected',
        'clear_suffix': 'Clear Suffix',
        'tip_add_files': 'Add files to the list',
        'tip_add_folder': 'Add all supported files from a folder',
        'tip_add_folder_recursive': 'Add all supported files from a folder and its subfolders',
        'add_untagged_folder': 'Add untagged files from folder',
        'tip_add_untagged_folder': 'Add files from a folder that do not have tags in the filename.',
        'add_untagged_folder_recursive': 'Add untagged files from folder (recursive)',
        'tip_add_untagged_folder_recursive': 'Add files from a folder and all subfolders that do not have tags in the filename.',
        'tip_preview_rename': 'Show a preview of the new file names',
        'tip_compress': 'Compress selected images',
        'tip_convert_heic': 'Convert HEIC files to JPEG',
        'tip_undo_rename': 'Undo the last rename operation',
        'tip_remove_selected': 'Remove selected rows from the table',
        'tip_clear_suffix': 'Clear the suffix of selected rows',
        'tip_clear_list': 'Remove all rows from the table',
        'tip_settings': 'Open the settings dialog',
        'tip_add_menu': 'Add files or folders',
        'config_path_label': 'Configuration folder',
        'config_path_desc': 'Location of the configuration files',
        'default_save_dir_label': 'Default save directory',
        'default_save_dir_desc': 'Folder used when saving renamed files',
        'default_import_dir_label': 'Default import directory',
        'default_import_dir_desc': 'Folder used when importing files',
        'use_import_dir': 'Use default import directory',
        'use_import_dir_desc': 'Automatically open the default import directory',
        'use_text_menu': 'Text-only toolbar',
        'use_text_menu_desc': 'Show text instead of icons in the toolbar',
        'use_original_directory': 'Use current folder?',
        'use_original_directory_msg': 'Save renamed files in their current folder?',
        'compress_after_rename': 'Compress images after renaming',
        'current_name': 'Current Name',
        'proposed_new_name': 'Proposed New Name',
        'renaming_files': 'Renaming files...', 
        'compressing_files': 'Compressing files...', 
        'abort': 'Abort',
        'no_tags_configured': 'No tags configured',
        'undo_rename': 'Undo Rename',
        'undo_nothing_title': 'Nothing to Undo',
        'undo_nothing_msg': 'There are no renames to undo.',
        'undo_done': 'Renames reverted.',
        'mode_normal': 'Normal',
        'mode_position': 'Pos',
        'mode_pa_mat': 'PA_MAT',
        'status_selected': '{current} of {total} selected',
        'status_loading': 'Loading...', 
        'invalid_tags_title': 'Invalid Tags',
        'invalid_tags_msg': 'Invalid tags: {tags}',
        'invalid_date_title': 'Invalid Date',
        'invalid_date_msg': 'Date must be YYMMDD',
        'open_file': 'Open File',
        'add_tags_for_selected': 'Add Tags for Selected',
        'add_suffix_for_selected': 'Add Suffix for Selected',
        'add_tags': 'Add Tags',
        'enter_comma_separated_tags': 'Enter comma-separated tags:',
        'add_suffix': 'Add Suffix',
        'enter_suffix': 'Enter suffix:',
        'remove_tags_for_selected': 'Remove Tags for Selected',
        'remove_tags': 'Remove Tags',
        'remove_tags_question': 'Do you want to remove specific tags or clear all tags?',
        'remove_specific_tags': 'Remove Specific Tags',
        'clear_all_tags': 'Clear All Tags',
        'set_import_directory': 'Set Import Directory',
        'tip_set_import_directory': 'Set the default directory for importing files',
        'restore_session_title': 'Restore Session',
        'restore_session_msg': 'A previous session was found. Do you want to restore it?',
        'session_saved': 'Session saved',
        'session_not_saved': 'Session not saved',
        'edit_menu': 'Edit',
        'tip_restore_session': 'Restore the last saved session',
        'no_session_to_restore': 'No session to restore.',
        'session_restored_successfully': 'Session restored successfully.',
        'session_restore_failed': 'Failed to restore session.',
        'help_title': 'Help',
        'tip_help': 'Show help',
        'help_content_html': '''            <h2>How to Use the Renamer</h2>
            <p>This application helps you rename image and video files based on a project number and descriptive tags.</p>
            <h3>Steps:</h3>
            <ol>
                <li><b>Set Project Number:</b> Enter the project number (e.g., C123456) in the \"MC-No.\" field.</li>
                <li><b>Add Files:</b> Use the \"Add\" menu to add files or folders to the list.</li>
                <li><b>Select Tags:</b> For each file, select one or more tags that describe its content. You can also add a custom suffix.</li>
                <li><b>Preview:</b> Click \"Preview Rename\" to see the proposed new filenames.</li>
                <li><b>Rename:</b> Click \"Rename All\" or \"Rename Selected\" to perform the renaming.</li>
            </ol>
            <h3>Modes:</h3>
            <ul>
                <li><b>Normal Mode:</b> In this mode, you can add tags to your files. The filename will be constructed using the project number, tags, and an optional suffix.</li>
                <li><b>Position Mode:</b> This mode is designed for specific workflows where files are assigned a position. The filename will be constructed using the project number and the position.</li>
                <li><b>PA MAT Mode:</b> This mode is for another specific workflow. The filename will be constructed using the project number and the PA_MAT value.</li>
            </ul>
            <h3>Additional Features:</h3>
            <ul>
                <li><b>Compression:</b> Compress images to reduce their file size.</li>
                <li><b>HEIC Conversion:</b> Convert HEIC files to JPEG format.</li>
                <li><b>Undo:</b> Revert the last renaming operation.</li>
                <li><b>Settings:</b> Customize application settings, such as language and accepted file types.</li>
            </ul>
        ''', 
        'search_tags': 'Search tags...', 
        'delete_selected_files': 'Delete Files',
        'tip_delete_selected_files': 'Delete selected files from disk',
        'delete_files_title': 'Delete Files',
        'delete_files_msg': 'Are you sure you want to delete {count} selected files from disk? This action cannot be undone.',
        'delete_failed_title': 'Delete Failed',
        'delete_failed_msg': 'Failed to delete {path}: {error}',
        'remove_suffix_for_selected': 'Remove Suffix for Selected',
        'update_tags_from_github': 'Update Tags from GitHub',
        'update_tags_from_github_desc': 'Download the latest tags.json from the GitHub repository.',
        'tags_download_failed': 'Failed to download tags from GitHub: {error}',
        'tags_parse_failed': 'Failed to parse tags from GitHub: {error}',
        'update_tags': 'Update Tags',
        'confirm_update_tags': 'This will overwrite your local tags.json with the version from GitHub. Are you sure?',
        'success': 'Success',
        'tags_update_success': 'Tags have been updated successfully. Please restart the application for the changes to take full effect.',
        'tags_write_failed': 'Failed to write updated tags to {file}: {error}'
    },
    'de': {
        'app_title': 'Micavac Renamer',
        'project_number_label': 'MC-Nr.:',
        'project_number_placeholder': 'C123456',
        'selected_file_label': 'Ausgewählte Datei:',
        'custom_suffix_label': 'Individueller Suffix für diese Datei:',
        'custom_suffix_placeholder': 'z.B. DSC00138',
        'select_tags_label': 'Tags für diese Datei wählen:',
        'add_menu': 'Hinzufügen',
        'add_files': 'Dateien hinzufügen...', 
        'add_folder': 'Ordner hinzufügen...', 
        'add_folder_recursive': 'Ordner und Unterordner hinzufügen...', 
        'preview_rename': 'Umbenennen Vorschau',
        'rename_all': 'Alle umbenennen',
        'rename_selected': 'Nur Auswahl umbenennen',
        'clear_list': 'Liste leeren',
        'compress': 'Komprimieren',
        'convert_heic': 'Zu JPEG konvertieren',
        'missing_project': 'Fehlende Projektnummer',
        'missing_project_msg': 'Bitte MC-Nr. eingeben (C gefolgt von 6 Ziffern).',
        'no_files': 'Keine Dateien',
        'no_files_msg': 'Keine Dateien zum Umbenennen.',
        'confirm_rename': 'Umbenennen bestätigen',
        'confirm_rename_msg': 'Ohne Vorschau umbenennen?',
        'rename_failed': 'Fehler beim Umbenennen',
        'partial_rename': 'Teilweises Umbenennen',
        'partial_rename_msg': 'Abgebrochen: {done} von {total} Dateien umbenannt.',
        'done': 'Fertig',
        'rename_done': 'Alle Dateien wurden umbenannt.',
        'settings_title': 'Einstellungen',
        'compression_settings': 'Kompression',
        'max_size_label': 'Maximale Größe (KB):',
        'max_size_desc': 'Ziel für maximale Dateigröße nach Komprimierung',
        'quality_label': 'JPEG-Qualität:',
        'quality_desc': 'JPEG-Qualität in Prozent',
        'reduce_resolution_label': 'Auflösung reduzieren falls nötig',
        'reduce_resolution_desc': 'Bildauflösung bei Bedarf verringern',
        'resize_only_label': 'Nur Größe anpassen',
        'resize_only_desc': 'Bilder nur skalieren ohne neue Komprimierung',
        'max_width_label': 'Maximale Breite (px):',
        'max_width_desc': 'Bilder breiter als diese Pixelzahl verkleinern (0 = kein Limit)',
        'max_height_label': 'Maximale Höhe (px):',
        'max_height_desc': 'Bilder höher als diese Pixelzahl verkleinern (0 = kein Limit)',
        'compression_done': 'Komprimierung abgeschlossen.',
        'rename_options_title': 'Optionen für Umbenennen',
        'compression_window_title': 'Komprimierungsvorschau',
        'compression_ok_info': 'Die Bilder werden erst nach Klick auf OK komprimiert.',
        'file': 'Datei',
        'old_size': 'Vorher',
        'new_size': 'Neu',
        'reduction': 'Reduktion',
        'video_unsupported': 'Videos nicht unterstützt',
        'video_unsupported_msg': 'Ausgewählte Videos können nicht komprimiert werden.',
        'heic_convert_title': 'HEIC umwandeln',
        'heic_convert_msg': 'HEIC-Bilder vor dem Komprimieren in JPEG konvertieren?',
        'accepted_ext_label': 'Erlaubte Dateiendungen (durch Komma getrennt):',
        'accepted_ext_desc': 'Dateitypen, die im Dateidialog angezeigt werden',
        'language_label': 'Sprache:',
        'language_desc': 'Sprache der Benutzeroberfläche',
        'tags_label': 'Tags',
        'restore_defaults': 'Standardeinstellungen wiederherstellen',
        'reset_tag_usage': 'Tag-Nutzung zurücksetzen',
        'remove_selected': 'Auswahl entfernen',
        'clear_suffix': 'Suffix entfernen',
        'tip_add_files': 'Dateien zur Liste hinzufügen',
        'tip_add_folder': 'Alle unterstützten Dateien aus einem Ordner hinzufügen',
        'tip_add_folder_recursive': 'Alle unterstützten Dateien aus einem Ordner und seinen Unterordnern hinzufügen',
        'add_untagged_folder': 'Ungetaggte Dateien aus Ordner hinzufügen',
        'tip_add_untagged_folder': 'Dateien aus einem Ordner hinzufügen, die keine Tags im Dateinamen haben.',
        'add_untagged_folder_recursive': 'Ungetaggte Dateien aus Ordner (rekursiv) hinzufügen',
        'tip_add_untagged_folder_recursive': 'Dateien aus einem Ordner und allen Unterordnern hinzufügen, die keine Tags im Dateinamen haben.',
        'tip_preview_rename': 'Vorschau der neuen Dateinamen anzeigen',
        'tip_compress': 'Ausgewählte Bilder komprimieren',
        'tip_convert_heic': 'HEIC-Dateien in JPEG umwandeln',
        'tip_undo_rename': 'Letzte Umbenennung rückgängig machen',
        'tip_remove_selected': 'Ausgewählte Zeilen aus der Tabelle entfernen',
        'tip_clear_suffix': 'Suffix der ausgewählten Zeilen löschen',
        'tip_clear_list': 'Alle Zeilen aus der Tabelle entfernen',
        'tip_settings': 'Einstellungen öffnen',
        'tip_add_menu': 'Dateien oder Ordner hinzufügen',
        'show_tags': 'Tags anzeigen',
        'hide_tags': 'Tags ausblenden',
        'current_name': 'Aktueller Name',
        'proposed_new_name': 'Vorgeschlagener neuer Name',
        'renaming_files': 'Dateien werden umbenannt...', 
        'compressing_files': 'Bilder werden komprimiert...', 
        'abort': 'Abbrechen',
        'no_tags_configured': 'Keine Tags konfiguriert',
        'undo_rename': 'Umbenennung rückgängig',
        'undo_nothing_title': 'Nichts rückgängig',
        'undo_nothing_msg': 'Keine Umbenennungen zum Rückgängigmachen.',
        'undo_done': 'Umbenennungen zurückgesetzt.',
        'config_path_label': 'Konfigurationsordner',
        'config_path_desc': 'Speicherort der Konfigurationsdateien',
        'default_save_dir_label': 'Standard-Speicherordner',
        'default_save_dir_desc': 'Ordner zum Speichern umbenannter Dateien',
        'default_import_dir_label': 'Standard-Importordner',
        'default_import_dir_desc': 'Ordner zum Importieren von Dateien',
        'use_import_dir': 'Standard-Importordner verwenden',
        'use_import_dir_desc': 'Standard-Importordner automatisch öffnen',
        'use_text_menu': 'Nur Text in der Werkzeugleiste',
        'use_text_menu_desc': 'Nur Text statt Symbole in der Werkzeugleiste',
        'use_original_directory': 'Aktuellen Ordner verwenden?',
        'use_original_directory_msg': 'Umbenannte Dateien im aktuellen Ordner speichern?',
        'compress_after_rename': 'Nach dem Umbenennen komprimieren',
        'mode_normal': 'Normal',
        'mode_position': 'Pos Modus Andi',
        'mode_pa_mat': 'PA_MAT Mode Andi',
        'status_selected': '{current} von {total} ausgewählt',
        'status_loading': 'Laden...', 
        'invalid_tags_title': 'Ungültige Tags',
        'invalid_tags_msg': 'Ungültige Tags: {tags}',
        'invalid_date_title': 'Ungültiges Datum',
        'invalid_date_msg': 'Datum muss JJMMTT sein',
        'open_file': 'Datei öffnen',
        'add_tags_for_selected': 'Tags für Auswahl hinzufügen',
        'add_suffix_for_selected': 'Suffix für Auswahl hinzufügen',
        'add_tags': 'Tags hinzufügen',
        'enter_comma_separated_tags': 'Tags komma-getrennt eingeben:',
        'add_suffix': 'Suffix hinzufügen',
        'enter_suffix': 'Suffix eingeben:',
        'remove_tags_for_selected': 'Tags von Auswahl entfernen',
        'remove_tags': 'Tags entfernen',
        'remove_tags_question': 'Möchten Sie bestimmte Tags entfernen oder alle Tags löschen?',
        'remove_specific_tags': 'Bestimmte Tags entfernen',
        'clear_all_tags': 'Alle Tags löschen',
        'set_import_directory': 'Importverzeichnis festlegen',
        'tip_set_import_directory': 'Standardverzeichnis für den Dateiimport festlegen',
        'restore_session_title': 'Sitzung wiederherstellen',
        'restore_session_msg': 'Eine vorherige Sitzung wurde gefunden. Möchten Sie sie wiederherstellen?',
        'session_saved': 'Sitzung gespeichert',
        'session_not_saved': 'Sitzung nicht gespeichert',
        'edit_menu': 'Bearbeiten',
        'tip_restore_session': 'Letzte gespeicherte Sitzung wiederherstellen',
        'no_session_to_restore': 'Keine Sitzung zum Wiederherstellen vorhanden.',
        'session_restored_successfully': 'Sitzung erfolgreich wiederhergestellt.',
        'session_restore_failed': 'Fehler beim Wiederherstellen der Sitzung.',
        'help_title': 'Hilfe',
        'tip_help': 'Hilfe anzeigen',
        'help_content_html': '''            <h2>Anleitung zum Renamer</h2>
            <p>Diese Anwendung hilft Ihnen, Bild- und Videodateien basierend auf einer Projektnummer und beschreibenden Tags umzubenennen.</p>
            <h3>Schritte:</h3>
            <ol>
                <li><b>Projektnummer festlegen:</b> Geben Sie die Projektnummer (z. B. C123456) in das Feld \"MC-Nr.\" ein.</li>
                <li><b>Dateien hinzufügen:</b> Verwenden Sie das Menü \"Hinzufügen\", um Dateien oder Ordner zur Liste hinzuzufügen.</li>
                <li><b>Tags auswählen:</b> Wählen Sie für jede Datei ein oder mehrere Tags aus, die den Inhalt beschreiben. Sie können auch einen benutzerdefinierten Suffix hinzufügen.</li>
                <li><b>Vorschau:</b> Klicken Sie auf \"Umbenennen Vorschau\", um die vorgeschlagenen neuen Dateinamen anzuzeigen.</li>
                <li><b>Umbenennen:</b> Klicken Sie auf \"Alle umbenennen\" oder \"Nur Auswahl umbenennen\", um die Umbenennung durchzuführen.</li>
            </ol>
            <h3>Modi:</h3>
            <ul>
                <li><b>Normal-Modus:</b> In diesem Modus können Sie Tags zu Ihren Dateien hinzufügen. Der Dateiname wird aus der Projektnummer, den Tags und einem optionalen Suffix zusammengesetzt.</li>
                <li><b>Positions-Modus:</b> Dieser Modus ist für spezielle Arbeitsabläufe gedacht, bei denen Dateien eine Position zugewiesen wird. Der Dateiname wird aus der Projektnummer und der Position zusammengesetzt.</li>
                <li><b>PA-MAT-Modus:</b> Dieser Modus ist für einen weiteren speziellen Arbeitsablauf vorgesehen. Der Dateiname wird aus der Projektnummer und dem PA_MAT-Wert zusammengesetzt.</li>
            </ul>
            <h3>Zusätzliche Funktionen:</h3>
            <ul>
                <li><b>Komprimierung:</b> Komprimieren Sie Bilder, um deren Dateigröße zu reduzieren.</li>
                <li><b>HEIC-Konvertierung:</b> Konvertieren Sie HEIC-Dateien in das JPEG-Format.</li>
                <li><b>Rückgängig:</b> Machen Sie die letzte Umbenennungsoperation rückgängig.</li>
                <li><b>Einstellungen:</b> Passen Sie die Anwendungseinstellungen an, wie z. B. die Sprache und die akzeptierten Dateitypen.</li>
            </ul>
        ''', 
        'search_tags': 'Tags suchen...', 
        'delete_selected_files': 'Dateien löschen',
        'tip_delete_selected_files': 'Ausgewählte Dateien von der Festplatte löschen',
        'delete_files_title': 'Dateien löschen',
        'delete_files_msg': 'Möchten Sie {count} ausgewählte Dateien von der Festplatte löschen? Diese Aktion kann nicht rückgängig gemacht werden.',
        'delete_failed_title': 'Löschen fehlgeschlagen',
        'delete_failed_msg': 'Fehler beim Löschen von {path}: {error}',
        'remove_suffix_for_selected': 'Suffix für Auswahl entfernen',
        'update_tags_from_github': 'Tags von GitHub aktualisieren',
        'update_tags_from_github_desc': 'Die aktuelle tags.json vom GitHub-Repository herunterladen.',
        'tags_download_failed': 'Fehler beim Herunterladen der Tags von GitHub: {error}',
        'tags_parse_failed': 'Fehler beim Parsen der Tags von GitHub: {error}',
        'update_tags': 'Tags aktualisieren',
        'confirm_update_tags': 'Dies überschreibt Ihre lokale tags.json mit der Version von GitHub. Sind Sie sicher?',
        'success': 'Erfolg',
        'tags_update_success': 'Die Tags wurden erfolgreich aktualisiert. Bitte starten Sie die Anwendung neu, damit die Änderungen wirksam werden.',
        'tags_write_failed': 'Fehler beim Schreiben der aktualisierten Tags nach {file}: {error}',
        'cert_install_title': 'Install Certificate',
        'cert_install_message': 'To prevent future security warnings, would you like to install the application\'s self-signed certificate? This requires administrator privileges.',
        'cert_install_error_title': 'Certificate Installation Error',
        'cert_install_error_message': 'Failed to launch certificate installation script: {error}'
    }
}

def set_language(lang: str) -> None:
    """
    Sets the current language for the application.

    Args:
        lang (str): The language code (e.g., "en", "de") to set as the current language.
                    If the language is not found in `TRANSLATIONS`, the language remains unchanged.
    """
    global current_language
    if lang in TRANSLATIONS:
        current_language = lang
        logger.info(f"Language set to: {current_language}")
    else:
        logger.warning(f"Attempted to set unsupported language: {lang}. Language remains {current_language}.")

def get_language() -> str:
    """
    Returns the currently active language code.

    Returns:
        str: The current language code (e.g., "en", "de").
    """
    return current_language

def tr(key: str) -> str:
    """
    Translates the given key into the current language.

    If the key is not found in the translations for the current language,
    it falls back to the English translation. If still not found, the key itself
    is returned as a fallback.

    Args:
        key (str): The translation key to look up.

    Returns:
        str: The translated string. If no translation is found, the original key is returned.
    """
    # Attempt to get the translation for the current language.
    # If not found, fall back to English. If still not found, return the key itself.
    translated_text = TRANSLATIONS.get(current_language, {}).get(key, TRANSLATIONS.get("en", {}).get(key, key))
    
    if translated_text == key:
        logger.warning(f"Translation key '{key}' not found in language '{current_language}' or 'en'.")
    
    return translated_text
