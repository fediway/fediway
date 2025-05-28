
from starlette.datastructures import URL

from config import config

def set_next_link(request, response, params):
    next_url = URL(
        f"{config.app.api_url}{request.url.path}"
    ).include_query_params(**params)

    response.headers["link"] = f'<{next_url}>; rel="next"'