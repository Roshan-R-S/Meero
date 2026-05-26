import os
from scripts import train_and_package


def test_dataset_hash_matches_file():
    intents_path = os.path.join(os.path.dirname(__file__), os.pardir, "intents.json")
    intents_path = os.path.normpath(intents_path)
    expected = train_and_package.compute_dataset_hash(intents_path)
    # compute again to ensure function is stable
    actual = train_and_package.compute_dataset_hash(intents_path)
    assert expected is not None
    assert expected == actual
