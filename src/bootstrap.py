import uvicorn
from fastapi import FastAPI
from uvicorn.middleware.wsgi import WSGIMiddleware

import main


if __name__ == "__main__":
    server = FastAPI()

    server.mount("/", WSGIMiddleware(main.app.server))

    uvicorn.run(server, host='0.0.0.0', port=8080)
