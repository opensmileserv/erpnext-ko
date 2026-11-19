class _Database:
    def set_value(self, doctype: str, name: str, field: str, value: object) -> None: ...

db: _Database
