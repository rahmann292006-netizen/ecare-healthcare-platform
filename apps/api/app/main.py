from fastapi import FastAPI

app = FastAPI(title="ecare API")


@app.get("/health")
def health():
    return {"status": "ok"}
