from aiohttp import web

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    html_page = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>File Store Bot Status</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background-color: #f0f2f5;
                color: #333;
            }
            .container {
                text-align: center;
                padding: 40px;
                border-radius: 12px;
                background-color: #ffffff;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            }
            h1 {
                font-size: 2.5em;
                color: #2c3e50;
            }
            p {
                font-size: 1.2em;
                color: #555;
            }
            .status {
                font-weight: bold;
                color: #27ae60;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>File Store Bot</h1>
            <p>The bot is up and <span class="status">running</span>!</p>
            <p>This web page confirms that the service is active.</p>
        </div>
    </body>
    </html>
    """
    return web.Response(text=html_page, content_type="text/html")
