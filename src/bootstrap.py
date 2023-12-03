import uvicorn
from fastapi import FastAPI
from uvicorn.middleware.wsgi import WSGIMiddleware

import config
import main


if __name__ == "__main__":
    server = FastAPI()

    BASE_URL_PATH = config.BASE_URL_PATH()

    server.mount(BASE_URL_PATH, WSGIMiddleware(main.app.server))

    # main.app.config.update({
    #     # as the proxy server will remove the prefix
    #     'routes_pathname_prefix': BASE_URL_PATH + "/",
    #
    #     # the front-end will prefix this string to the requests
    #     # that are made to the proxy server
    #     'requests_pathname_prefix': BASE_URL_PATH + "/"
    # })

    uvicorn.run(server, host='0.0.0.0', port=8080, debug=False)
