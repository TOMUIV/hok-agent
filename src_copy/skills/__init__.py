import importlib, pkgutil
from skill_base import SKILL_REGISTRY, Skill, register_skill

for importer, modname, ispkg in pkgutil.iter_modules(__path__):
    if modname.startswith("_"):
        continue
    importlib.import_module(f".{modname}", __package__)
