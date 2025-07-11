import webbrowser
from typing import Annotated

import typer

from cli.commons.decorators import add_verbose_option
from cli.pages.server import start_dev_server


app = typer.Typer(help="Tool for developing custom pages locally.")


@app.command(help="Start local development server with Ubidots context preview.", hidden=False)
@add_verbose_option()
def dev(
    port: Annotated[
        int,
        typer.Option(help="Port for the development server."),
    ] = 3000,
    iframe_port: Annotated[
        int,
        typer.Option(help="Port for the iframe content server."),
    ] = 3001,
    auto_open: Annotated[
        bool,
        typer.Option(help="Automatically open browser."),
    ] = True,
    verbose: Annotated[bool, typer.Option(hidden=True)] = False,
):
    typer.echo(f"🚀 Starting Ubidots Pages development server...")
    typer.echo(f"📱 Context preview: http://localhost:{port}")
    typer.echo(f"🔧 Your page: http://localhost:{iframe_port}")
    typer.echo(f"💡 Develop your custom page and it will appear in the iframe!")
    
    if auto_open:
        typer.echo(f"🌐 Opening browser...")
        webbrowser.open(f"http://localhost:{port}")
    
    try:
        start_dev_server(port, iframe_port)
    except KeyboardInterrupt:
        typer.echo("\n👋 Development server stopped.")
    except Exception as e:
        typer.echo(f"❌ Error starting server: {e}")
        raise typer.Exit(1)