current_language = 'en'

TRANSLATIONS = {
    'en': {
        'app_title': 'Micavac Renamer',
        'project_number_label': 'MC-No.:',
        'project_number_placeholder': 'C123456',
        'selected_file_label': 'Selected File:',
        'custom_suffix_label': 'Custom Suffix for this file:',
        'custom_suffix_placeholder': 'e.g. DSC00138',
        'select_tags_label': 'Select Tags for this file:',
        'add_menu': 'Add',
        'add_files': 'Add Files...',
        'add_folder': 'Add Folder...',
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
        'compression_window_title': 'Compression Results',
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
        'current_name': 'Current Name'
        , 'proposed_new_name': 'Proposed New Name'
        , 'renaming_files': 'Renaming files...'
        , 'abort': 'Abort'
        , 'no_tags_configured': 'No tags configured'
        , 'undo_rename': 'Undo Rename'
        , 'undo_nothing_title': 'Nothing to Undo'
        , 'undo_nothing_msg': 'There are no renames to undo.'
        , 'undo_done': 'Renames reverted.'
        , 'mode_normal': 'Normal'
        , 'mode_position': 'Pos Mode Andi'
        , 'mode_pa_mat': 'PA_MAT Mode Andi'
        , 'status_selected': '{current} of {total} selected'
        , 'status_loading': 'Loading...'
        , 'invalid_tags_title': 'Invalid Tags'
        , 'invalid_tags_msg': 'Invalid tags: {tags}'
        , 'invalid_date_title': 'Invalid Date'
        , 'invalid_date_msg': 'Date must be YYMMDD'
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
        'compression_window_title': 'Ergebnis der Komprimierung',
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
        'show_tags': 'Tags anzeigen',
        'hide_tags': 'Tags ausblenden'
        , 'current_name': 'Aktueller Name'
        , 'proposed_new_name': 'Vorgeschlagener neuer Name'
        , 'renaming_files': 'Dateien werden umbenannt...'
        , 'abort': 'Abbrechen'
        , 'no_tags_configured': 'Keine Tags konfiguriert'
        , 'undo_rename': 'Umbenennung rückgängig'
        , 'undo_nothing_title': 'Nichts rückgängig'
        , 'undo_nothing_msg': 'Keine Umbenennungen zum Rückgängigmachen.'
        , 'undo_done': 'Umbenennungen zurückgesetzt.'
        , 'config_path_label': 'Konfigurationsordner'
        , 'config_path_desc': 'Speicherort der Konfigurationsdateien'
        , 'default_save_dir_label': 'Standard-Speicherordner'
        , 'default_save_dir_desc': 'Ordner zum Speichern umbenannter Dateien'
        , 'default_import_dir_label': 'Standard-Importordner'
        , 'default_import_dir_desc': 'Ordner zum Importieren von Dateien'
        , 'use_import_dir': 'Standard-Importordner verwenden'
        , 'use_import_dir_desc': 'Standard-Importordner automatisch öffnen'
        , 'use_text_menu': 'Nur Text in der Werkzeugleiste'
        , 'use_text_menu_desc': 'Nur Text statt Symbole in der Werkzeugleiste'
        , 'use_original_directory': 'Aktuellen Ordner verwenden?'
        , 'use_original_directory_msg': 'Umbenannte Dateien im aktuellen Ordner speichern?'
        , 'mode_normal': 'Normal'
        , 'mode_position': 'Pos Modus Andi'
        , 'mode_pa_mat': 'PA_MAT Mode Andi'
        , 'status_selected': '{current} von {total} ausgewählt'
        , 'status_loading': 'Laden...'
        , 'invalid_tags_title': 'Ungültige Tags'
        , 'invalid_tags_msg': 'Ungültige Tags: {tags}'
        , 'invalid_date_title': 'Ungültiges Datum'
        , 'invalid_date_msg': 'Datum muss JJMMTT sein'
    }
}

def set_language(lang: str):
    global current_language
    if lang in TRANSLATIONS:
        current_language = lang


def tr(key: str) -> str:
    return TRANSLATIONS.get(current_language, {}).get(key, key)

