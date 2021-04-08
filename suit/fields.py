import json
from django.db.models import TextField
from .base import StreamObject


class StreamField(TextField):
    description = "StreamField"

    def __init__(self, *args, **kwargs):
        self.model_list = kwargs.pop('model_list', [])
        self.popup_size = kwargs.pop('popup_size', (1000, 500))
        kwargs['blank'] = True
        kwargs['default'] = "[]"
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        return self.to_python(json.loads(value))

    def to_python(self, value):
        if not value or isinstance(value, StreamObject):
            return value
        return StreamObject(value, self.model_list)

    def get_prep_value(self, value):
        return json.dumps(str(value))

    def formfield(self, **kwargs):
        from .widgets import StreamFieldWidget

        widget_class = kwargs.get('widget', StreamFieldWidget)
        attrs = {}
        attrs["model_list"] = self.model_list
        attrs["data-popup_size"] = list(self.popup_size)
        defaults = {
            'widget': widget_class(attrs=attrs),
        }
        return super().formfield(**defaults)
