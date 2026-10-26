from pathlib import Path
from ai_edge_litert.interpreter import Interpreter

# Find the trained model in the BuggyBot repository
model_path = (
    Path.home()
    / "Projects"
    / "BuggyBot"
    / "Model Training"
    / "models"
    / "combined_model.tflite"
)

# Check whether the file exists
if not model_path.exists():
    print("ERROR: Model file not found.")
    raise SystemExit(1)

print("Model file found!")

# Load the model
interpreter = Interpreter(model_path=str(model_path))

# Allocate memory for the model
interpreter.allocate_tensors()

print("TensorFlow Lite model loaded successfully!")

# Get model information
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

print("\nModel Input:")
print(input_details[0]["shape"])

print("\nModel Output:")
print(output_details[0]["shape"])