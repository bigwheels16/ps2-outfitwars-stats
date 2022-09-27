import uvicorn
from fastapi import FastAPI
from uvicorn.middleware.wsgi import WSGIMiddleware

import config
import main


if __name__ == "__main__":
    dev = True

    if dev:
        # https://dash.plotly.com/devtools
        # `app.run_server(host='127.0.0.1', port='7080', proxy=None, debug=False, dev_tools_ui=None, dev_tools_props_check=None, dev_tools_serve_dev_bundles=None, dev_tools_hot_reload=None, dev_tools_hot_reload_interval=None, dev_tools_hot_reload_watch_interval=None, dev_tools_hot_reload_max_retry=None, dev_tools_silence_routes_logging=None, dev_tools_prune_errors=None, **flask_run_options)`
        main.app.run_server(host="0.0.0.0", port="8080", debug=True)
    else:
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
