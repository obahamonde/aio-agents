from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound
from pydantic import BaseConfig  # pylint: disable=no-name-in-module
from pydantic import BaseModel, Field


class Prompt(BaseModel):
    """Class to generate prompts for OpenAI's API."""

    template: str = Field(description="Jinja2 Template to render.")
    environ: Optional[Path] = Field(
        default=None, description="Jinja2 Templates Directory."
    )

    class Config(BaseConfig):
        allow_mutation = False
        validate_assignment = True
        arbitrary_types_allowed = True

    @property
    def template_(self) -> Template:
        """Get the Jinja2 template."""
        try:
            if self.environ is not None:
                return Environment(loader=FileSystemLoader(self.environ)).get_template(
                    self.template
                )
            return Template(self.template)
        except TemplateNotFound:
            raise FileNotFoundError("Template %s not found." % self.template)

    def render(self) -> str:
        """Render the template with the given context."""
        return self.template_.render(**self.dict())
