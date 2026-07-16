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
        subs = []
        for attr_name in dir(self):
            if attr_name.startswith("func_"):
                fn = getattr(self, attr_name)
                doc = fn.__doc__ or ""
                subs.append(f"  {attr_name.replace('func_','')} — {doc.strip()}")
        lines = [
            f"name: {self.name}",
            f"description: {self.description}",
            f"when: {self.when}",
            f"until: {self.until}",
            "sub_functions:",
        ]
        lines.extend(subs)
        return "\n".join(lines)

    def execute(self, ctx, func_name, params=None):
        fn = getattr(self, f"func_{func_name}", None)
        if not fn:
            return f"unknown sub_function: {func_name}"
        act = fn(ctx, **(params or {}))
        return act

    def get_sub_functions(self):
        result = {}
        for attr_name in dir(self):
            if attr_name.startswith("func_"):
                name = attr_name.replace("func_", "")
                fn = getattr(self, attr_name)
                result[name] = fn.__doc__ or ""
        return result
