class MockSpeechEngine:
    def __init__(self):
        self.response_buffer = []

    def speak(self, text):
        self.response_buffer.append(text)

    def get_response(self):
        return " ".join(self.response_buffer)
