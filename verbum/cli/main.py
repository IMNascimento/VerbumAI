"""
verbum/cli/main.py
==================
Interface de linha de comando do verbumAI.
Usa Typer (comandos) + Rich (output estilizado).
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from verbum import __version__
from verbum.config import cfg

app = typer.Typer(
    name="verbum",
    help=" verbumAI — Busca semântica na Bíblia com RAG",
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()


class Provider(str, Enum):
    claude = "claude"
    openai = "openai"
    ollama = "ollama"


# ─── Helpers de UI ───────────────────────────────────────────────────────────

def _print_header():
    console.print()
    console.print(
        Panel.fit(
            "[bold gold1]  verbumAI[/bold gold1]\n"
            "[dim]Busca semântica na Bíblia • RAG sem alucinação[/dim]",
            border_style="gold1",
        )
    )
    console.print()


def _print_result(result) -> None:
    """Renderiza um QueryResult no terminal com Rich."""

    # ── Versículos encontrados ────────────────────────────────────────────────
    console.print(Rule(f"[bold] Versículos recuperados[/bold]", style="gold1"))

    table = Table(
        show_header=True,
        header_style="bold gold1",
        box=box.SIMPLE_HEAD,
        expand=True,
        show_lines=False,
    )
    table.add_column("Ref.", style="bold cyan", no_wrap=True, width=22)
    table.add_column("Versículo", style="white")
    table.add_column("Score", style="dim", width=7, justify="right")

    for v in result.verses:
        score_color = (
            "green" if v.similarity > 0.7
            else "yellow" if v.similarity > 0.5
            else "red"
        )
        table.add_row(
            v.reference,
            escape(v.text),
            f"[{score_color}]{v.similarity:.2f}[/{score_color}]",
        )

    console.print(table)

    # ── Resposta do LLM ────────────────────────────────────────────────────────
    console.print()
    console.print(Rule(f"[bold] Análise — {escape(result.provider_name)}[/bold]", style="gold1"))
    console.print()

    for paragraph in result.answer.split("\n"):
        if paragraph.strip():
            console.print(f"  {escape(paragraph)}")
        else:
            console.print()

    console.print()
    console.print(Rule(style="dim"))
    console.print()


# ─── Comandos ────────────────────────────────────────────────────────────────

@app.command()
def setup(
    force: bool = typer.Option(
        False, "--force", "-f", help="Re-indexa mesmo que o banco já exista"
    ),
):
    """
    [bold]Baixa a Bíblia e indexa no banco vetorial.[/bold]

    Execute este comando uma única vez antes de usar o verbumAI.
    """
    _print_header()

    from verbum.indexer import run_setup

    console.print("[bold]Passo 1 de 3[/bold] — Verificando Bíblia ACF (domínio público)...")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Baixando / verificando Bíblia...", total=None)
        from verbum.indexer import download_bible, parse_verses

        raw = download_bible(force=force)
        verses = parse_verses(raw)

    console.print(f"[green]{len(verses):,} versículos encontrados[/green]")

    console.print("\n[bold]Passo 2 de 3[/bold] — Carregando modelo de embedding...")
    console.print(f"  ℹ  Modelo: [cyan]{cfg.embedding_model}[/cyan]")
    console.print("  ℹ  Primeira execução baixa ~420 MB. Aguarde...\n")

    from verbum.indexer import build_index

    build_index(verses, force=force)

    console.print(f"\n[bold]Passo 3 de 3[/bold] — Concluído!")
    console.print(
        Panel(
            f"[bold green]{len(verses):,} versículos indexados com sucesso![/bold green]\n\n"
            "Agora você pode consultar a Bíblia:\n"
            "  [cyan]verbum query[/cyan]                         -> modo interativo\n"
            '  [cyan]verbum ask "cura de doenças"[/cyan]         -> consulta direta',
            title="verbumAI pronto",
            border_style="green",
        )
    )


@app.command()
def ask(
    query: str = typer.Argument(..., help="Tema ou pergunta para consultar na Bíblia"),
    provider: Optional[Provider] = typer.Option(
        None, "--provider", "-p", help="Provider LLM (padrão: .env)"
    ),
    top_k: int = typer.Option(cfg.top_k_context, "--top-k", "-k", help="Versículos no contexto"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Mostra scores de similaridade"),
):
    """
    [bold]Consulta a Bíblia por tema ou pergunta.[/bold]

    Exemplos:
      verbum ask "o que Deus fala sobre saúde e cura"
      verbum ask "amor ao próximo" --provider openai
      verbum ask "perdão" --provider ollama --top-k 10
    """
    from verbum import retriever
    from verbum.pipeline import ask as pipeline_ask

    _print_header()

    prov = provider.value if provider else None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task(f'Buscando versículos sobre "{query}"...', total=None)
        retriever.preload()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Gerando análise com o modelo...", total=None)
        result = pipeline_ask(query, provider=prov, top_k_context=top_k)

    _print_result(result)


@app.command()
def query(
    provider: Optional[Provider] = typer.Option(
        None, "--provider", "-p", help="Provider LLM (padrão: .env)"
    ),
    top_k: int = typer.Option(cfg.top_k_context, "--top-k", "-k", help="Versículos no contexto"),
):
    """
    [bold]Modo interativo[/bold] — faça múltiplas perguntas sem reiniciar.

    Comandos especiais no modo interativo:
      :sair / :quit  -> encerra
      :provider X    -> troca o provider (claude, openai, ollama)
      :ajuda         -> mostra ajuda
    """
    from verbum import retriever
    from verbum.pipeline import ask as pipeline_ask

    _print_header()

    active_provider = provider.value if provider else cfg.provider

    # Pré-carrega modelo (evita delay na primeira pergunta)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Carregando modelos...", total=None)
        retriever.preload()

    console.print(
        Panel(
            f"Provider ativo: [bold cyan]{active_provider.upper()}[/bold cyan] "
            f"({cfg.active_model_name() if not provider else ''})\n"
            "Comandos: [dim]:sair[/dim]  [dim]:provider claude|openai|ollama[/dim]  [dim]:ajuda[/dim]",
            border_style="gold1",
        )
    )
    console.print()

    while True:
        try:
            raw = console.input("[bold gold1] Tema ou pergunta:[/bold gold1] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n\n[dim]Até logo! [/dim]")
            break

        if not raw:
            continue

        # ── Comandos especiais ────────────────────────────────────────────────
        if raw.startswith(":"):
            parts = raw[1:].split()
            cmd = parts[0].lower()

            if cmd in ("sair", "quit", "exit", "q"):
                console.print("\n[dim]Até logo! [/dim]")
                break

            elif cmd == "provider" and len(parts) > 1:
                new_p = parts[1].lower()
                if new_p in ("claude", "openai", "ollama"):
                    active_provider = new_p
                    console.print(f"Provider trocado para [cyan]{active_provider}[/cyan]\n")
                else:
                    console.print(" Provider inválido. Use: claude, openai, ollama\n")

            elif cmd == "ajuda":
                console.print(
                    Panel(
                        ":sair         -> encerra o modo interativo\n"
                        ":provider X   -> troca o provider (claude, openai, ollama)\n"
                        ":ajuda        -> mostra esta mensagem",
                        title="Ajuda",
                        border_style="dim",
                    )
                )

            else:
                console.print(f" Comando desconhecido: {raw}\n")

            continue

        # ── Consulta normal ───────────────────────────────────────────────────
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task("Gerando análise...", total=None)
                result = pipeline_ask(raw, provider=active_provider, top_k_context=top_k)

            _print_result(result)

        except (ValueError, ConnectionError) as e:
            console.print(f"\n  [red] Erro:[/red] {e}\n")
        except Exception as e:
            console.print(f"\n  [red] Erro inesperado:[/red] {e}\n")


@app.command()
def version():
    """Exibe a versão do verbumAI."""
    console.print(f"verbumAI v{__version__}")


# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
