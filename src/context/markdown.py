from markdown_it import MarkdownIt
from markdown_it.renderer import RendererHTML
from markdown_it.rules_inline.linkify import linkify
from pygments import highlight
from pygments.formatters import HtmlFormatter  # pylint: disable=no-name-in-module
from pygments.lexers import get_lexer_by_name
from pygments.styles import get_style_by_name


def highlight_code(code: str, lang: str, _options: dict) -> str:
    if not lang:
        lexer = get_lexer_by_name("md")
    lexer = get_lexer_by_name(lang)
    style = get_style_by_name("monokai")
    formatter = HtmlFormatter(style=style)
    return highlight(code, lexer, formatter)


def render_markdown(markdown: str) -> str:
    markdownit = MarkdownIt(
        "js-default",
        {
            "html": True,
            "linkify": True,
            "typographer": True,
            "highlight": highlight_code,
            "renderer": RendererHTML(),
        },
    )
    return markdownit.render(markdown)
