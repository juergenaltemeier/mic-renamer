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
        'add_files': 'Add Files...',
        'add_folder': 'Add Folder...',
        'preview_rename': 'Preview Rename',
        'rename_all': 'Rename All',
        'rename_selected': 'Rename Selected',
        'clear_list': 'Clear List',
        'compress': 'Compress',
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
        'max_size_label': 'Max Size (MB):',
        'quality_label': 'JPEG Quality:',
        'reduce_resolution_label': 'Reduce resolution if needed',
        'compression_done': 'Compression finished.',
        'rename_options_title': 'Rename Options',
        'compress_large_files': 'Compress files over {size} MB',
        'show_tags': 'Show tags',
        'hide_tags': 'Hide tags',
        'accepted_ext_label': 'Accepted File Extensions (comma separated):',
        'language_label': 'Language:',
        'tags_label': 'Tags',
        'restore_defaults': 'Restore Defaults',
        'reset_tag_usage': 'Reset Tag Usage',
        'remove_selected': 'Remove Selected',
        'config_path_label': 'Configuration folder',
        'default_save_dir_label': 'Default save directory',
        'use_original_directory': 'Use current folder?',
        'use_original_directory_msg': 'Save renamed files in their current folder?',
        'current_name': 'Current Name'
        , 'proposed_new_name': 'Proposed New Name'
        , 'renaming_files': 'Renaming files...'
        , 'abort': 'Abort'
        , 'no_tags_configured': 'No tags configured'
    },
    'de': {
        'app_title': 'Micavac Renamer',
        'project_number_label': 'MC-Nr.:',
        'project_number_placeholder': 'C123456',
        'selected_file_label': 'Ausgewählte Datei:',
        'custom_suffix_label': 'Individueller Suffix für diese Datei:',
        'custom_suffix_placeholder': 'z.B. DSC00138',
        'select_tags_label': 'Tags für diese Datei wählen:',
        'add_files': 'Dateien hinzufügen...',
        'add_folder': 'Ordner hinzufügen...',
        'preview_rename': 'Umbenennen Vorschau',
        'rename_all': 'Alle umbenennen',
        'rename_selected': 'Auswahl umbenennen',
        'clear_list': 'Liste leeren',
        'compress': 'Komprimieren',
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
        'max_size_label': 'Maximale Größe (MB):',
        'quality_label': 'JPEG-Qualität:',
        'reduce_resolution_label': 'Auflösung reduzieren falls nötig',
        'compression_done': 'Komprimierung abgeschlossen.',
        'rename_options_title': 'Optionen für Umbenennen',
        'compress_large_files': 'Dateien über {size} MB komprimieren',
        'accepted_ext_label': 'Erlaubte Dateiendungen (durch Komma getrennt):',
        'language_label': 'Sprache:',
        'tags_label': 'Tags',
        'restore_defaults': 'Standardeinstellungen wiederherstellen',
        'reset_tag_usage': 'Tag-Nutzung zurücksetzen',
        'remove_selected': 'Auswahl entfernen',
        'show_tags': 'Tags anzeigen',
        'hide_tags': 'Tags ausblenden'
        , 'current_name': 'Aktueller Name'
        , 'proposed_new_name': 'Vorgeschlagener neuer Name'
        , 'renaming_files': 'Dateien werden umbenannt...'
        , 'abort': 'Abbrechen'
        , 'no_tags_configured': 'Keine Tags konfiguriert'
        , 'config_path_label': 'Konfigurationsordner'
        , 'default_save_dir_label': 'Standard-Speicherordner'
        , 'use_original_directory': 'Aktuellen Ordner verwenden?'
        , 'use_original_directory_msg': 'Umbenannte Dateien im aktuellen Ordner speichern?'
    }
}

def set_language(lang: str):
    global current_language
    if lang in TRANSLATIONS:
        current_language = lang


def tr(key: str) -> str:
    return TRANSLATIONS.get(current_language, {}).get(key, key)

