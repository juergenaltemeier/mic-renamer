import os
from mic_renamer.logic.renamer import Renamer
from mic_renamer.logic.settings import ItemSettings
from mic_renamer.logic.rename_config import RenameConfig

def test_build_mapping_with_tags(tmp_path):
    # Create dummy files
    img_a_path = tmp_path / "a.jpg"
    img_a_path.write_bytes(b"x")

    # Create ItemSettings
    item = ItemSettings(original_path=str(img_a_path))
    item.tags.add("tag1")
    item.tags.add("tag2")

    # Create Renamer instance
    renamer = Renamer(project="PROJ1", items=[item], config=RenameConfig())

    # Build the mapping
    mapping = renamer.build_mapping()

    # Get the new path
    new_path = mapping[0][2]

    # Verify the new filename
    new_filename = os.path.basename(new_path)
    assert "PROJ1" in new_filename
    assert "tag1" in new_filename
    assert "tag2" in new_filename
    assert new_filename.endswith(".jpg")
