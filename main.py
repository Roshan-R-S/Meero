
import sys
import logging
import argparse
from speech_engine import SpeechEngine
from actions import Actions
from neural_net import NeuralNet

logger = logging.getLogger(__name__)

def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Meero Personal Assistant")
    parser.add_argument("--mode", type=str, default="voice", choices=["voice", "text"], help="Input mode: 'voice' or 'text'")
    args = parser.parse_args()

    logger.info("Initializing Meero in %s mode...", args.mode)
    
    # Initialize components
    engine = SpeechEngine()
    actions = Actions(engine)
    try:
        brain = NeuralNet()
    except Exception as e:
        logger.error("Error loading model: %s", e)
        engine.speak("I am having trouble accessing my neural network. Please check if the model is trained.")
        return

    # Startup
    actions.wish_me()
    
    while True:
        query = engine.get_input(args.mode)
        
        if query == "None":
            continue

        # Logic delegated to Actions class
        result = actions.process_command(query, lambda: engine.get_input(args.mode), sys.exit)
        
        if result == "neural_net_fallback":
            # Fallback to Neural Network for conversation
            response = brain.predict(query)
            if response:
                engine.speak(response)

if __name__ == "__main__":
    main()