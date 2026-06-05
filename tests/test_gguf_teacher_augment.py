from pathlib import Path

from scripts.gguf_teacher_augment import augment_intents_with_teachers, write_augmented_intents


class FakeTeacher:
    def __init__(self, response: str):
        self.response = response
        self.prompts = []

    def generate(self, prompt, max_tokens=None, temp=None):
        self.prompts.append((prompt, max_tokens, temp))
        return self.response


def test_augment_intents_with_teachers_adds_unique_paraphrases(tmp_path):
    intents = {
        "intents": [
            {
                "tag": "greeting",
                "patterns": ["Hi", "Hello"],
                "responses": ["Hello"],
                "context": [""],
            }
        ]
    }

    teacher_map = {
        "teacher-a.gguf": FakeTeacher('["Hey there", "Hello", "Greetings"]'),
        "teacher-b.gguf": FakeTeacher("How are you\nHi\nGood to see you"),
    }

    def teacher_factory(path: Path):
        return teacher_map[path.name]

    augmented, manifest = augment_intents_with_teachers(
        intents,
        [Path("teacher-a.gguf"), Path("teacher-b.gguf")],
        examples_per_model=2,
        temperature=0.1,
        max_tokens=64,
        teacher_factory=teacher_factory,
    )

    patterns = augmented["intents"][0]["patterns"]
    assert "Hey there" in patterns
    assert "Good to see you" in patterns
    assert "Hello" in patterns
    assert manifest["enabled"] is True
    assert manifest["examples_added"] >= 2
    assert len(manifest["teacher_models"]) == 2
    assert teacher_map["teacher-a.gguf"].prompts
    assert teacher_map["teacher-b.gguf"].prompts


def test_write_augmented_intents_writes_manifest(tmp_path):
    output = tmp_path / "intents.teacher_augmented.json"
    manifest = {"enabled": True, "examples_added": 1}
    payload = {"intents": []}

    data_path, manifest_path = write_augmented_intents(output, payload, manifest)

    assert Path(data_path).exists()
    assert Path(manifest_path).exists()