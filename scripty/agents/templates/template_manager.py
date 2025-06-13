import os
import glob
import jinja2
from agents import Agent, RunContextWrapper
from scripty.schemas import ScriptyContext

CURRENT_FILE_PATH = os.path.dirname(os.path.abspath(__file__))

class TemplateManager:
    """
    A manager for templates.
    It will load all the templates in the given directory and make them available to render.
    The templates are expected to be in the format of <name>.j2.
    The manager will load all the templates in the directory and make them available to render.
    The manager will also make the templates available to the templates themselves.
    The manager will also make the templates available to the templates themselves.
    """
    def __init__(self, template_dir: str = CURRENT_FILE_PATH):
        self.templates = {}
        for template in glob.glob(os.path.join(template_dir, "*.j2")):
            with open(template, encoding="utf-8") as f:
                self.templates[os.path.basename(template).replace(".j2", "")] = jinja2.Template(f.read())

    def render(self, name: str, wrapper: RunContextWrapper[ScriptyContext], agent: Agent[ScriptyContext]) -> str:
        """
        Render a template with the given name and kwargs.
        Args:
            name: The name of the template to render.
            **kwargs: The kwargs to pass to the template.
        Returns:
            The rendered template.
        """
        return self.templates[name].render(context=wrapper.context, agent=agent)

template_manager = TemplateManager()
