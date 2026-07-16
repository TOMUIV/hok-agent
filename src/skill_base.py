SKILL_REGISTRY = {}

def register_skill(cls):
    instance = cls()
    SKILL_REGISTRY[instance.name] = instance
    return cls

class Skill:
    name = ""
    description = ""
    when = ""
    until = ""

    def get_doc(self):
        lines = [
            f"# {self.name}",
            f"{self.description}",
            f"when: {self.when}",
            f"until: {self.until}",
            "",
            "## sub_functions",
        ]
        for attr_name in dir(self):
            if attr_name.startswith("func_"):
                func_name = attr_name.replace("func_", "")
                fn = getattr(self, attr_name)
                doc = fn.__doc__ or ""
                params = self._func_params(func_name)
                returns = self._func_returns(func_name)
                lines.append(f"### {func_name}({', '.join(params) if params else ''})")
                lines.append(f"  {doc.strip()}")
                if returns:
                    lines.append(f"  returns: {returns}")
                lines.append("")
        return "\n".join(lines)

    def _func_params(self, name):
        mapping = getattr(self, "sub_func_params", {})
        return mapping.get(name, [])

    def _func_returns(self, name):
        mapping = getattr(self, "sub_func_returns", {})
        return mapping.get(name, "")

    def execute(self, ctx, func_name, params=None):
        fn = getattr(self, f"func_{func_name}", None)
        if not fn:
            return f"unknown sub_function: {func_name}"
        result = fn(ctx, **(params or {}))
        return result

    def get_sub_functions(self):
        result = {}
        for attr_name in dir(self):
            if attr_name.startswith("func_"):
                name = attr_name.replace("func_", "")
                fn = getattr(self, attr_name)
                result[name] = fn.__doc__ or ""
        return result
