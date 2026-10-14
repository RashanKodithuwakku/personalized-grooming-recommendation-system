from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Component 4 Backend Running"}