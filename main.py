from fastapi import FastAPI

# Create the FastAPI instance
app = FastAPI()

# Optional: Root endpoint for testing
@app.get("/")
def read_root():
    return {"message": "Hello from Render! 🎉"}