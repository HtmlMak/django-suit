from copy import deepcopy
import json
from django import forms
from django.urls import reverse
from django.forms.widgets import Widget
from django.forms import Textarea, TextInput, ClearableFileInput

from django.utils.safestring import mark_safe
from django.contrib.admin.options import FORMFIELD_FOR_DBFIELD_DEFAULTS
from .base import StreamObject
from .fields import StreamField
from .settings import (
    BLOCK_OPTIONS,
    SHOW_ADMIN_HELP_TEXT,
    DELETE_BLOCKS_FROM_DB,
)


class AutosizedTextarea(Textarea):
    """
    AutoSized TextArea - TextArea height dynamically grows based on user input
    """

    def __init__(self, attrs=None):
        new_attrs = _make_attrs(attrs, {"rows": 2}, "autosize form-control")
        super(AutosizedTextarea, self).__init__(new_attrs)

    @property
    def media(self):
        return forms.Media(js=('suit/js/autosize.min.js',))

    def render(self, name, value, attrs=None, renderer=None):
        output = super(AutosizedTextarea, self).render(name, value, attrs)
        output += mark_safe(
            "<script type=\"text/javascript\">django.jQuery(function () { autosize(document.getElementById('id_%s')); });</script>"
            % name)
        return output


class CharacterCountTextarea(AutosizedTextarea):
    """
    TextArea with character count. Supports also twitter specific count.
    """

    def render(self, name, value, attrs=None, renderer=None):
        output = super(CharacterCountTextarea, self).render(name, value, attrs, )
        output += mark_safe(
            "<script type=\"text/javascript\">django.jQuery(function () { django.jQuery('#id_%s').suitCharactersCount(); });</script>"
            % name)
        return output


class ImageWidget(ClearableFileInput):
    def render(self, name, value, attrs=None, renderer=None):
        html = super(ImageWidget, self).render(name, value, attrs, renderer)
        if not value or not hasattr(value, 'url') or not value.url:
            return html
        html = u'<div class="ImageWidget"><div class="float-xs-left">' \
               u'<a href="%s" target="_blank"><img src="%s" width="75"></a></div>' \
               u'%s</div>' % (value.url, value.url, html)
        return mark_safe(html)


class EnclosedInput(TextInput):
    """
    Widget for bootstrap appended/prepended inputs
    """

    def __init__(self, attrs=None, prepend=None, append=None, prepend_class='addon', append_class='addon',
                 onclick_append=None):
        """
        :param prepend_class|append_class: CSS class applied to wrapper element. Values: addon or btn
        """
        self.prepend = prepend
        self.prepend_class = prepend_class
        self.append = append
        self.append_class = append_class
        self.onclick_append = onclick_append
        super(EnclosedInput, self).__init__(attrs=attrs)

    def enclose_value(self, value, wrapper_class):
        if value.startswith("fa-"):
            value = '<i class="fa %s"></i>' % value
        return '<span class="input-group-text input-group-%s"%s>%s</span>' % (
            wrapper_class, "onclick=" + self.onclick_append if self.onclick_append else "", value)

    def render(self, name, value, attrs=None, renderer=None):
        output = super(EnclosedInput, self).render(name, value, attrs)
        if self.prepend:
            self.prepend = self.enclose_value(self.prepend, self.prepend_class)
            output = '<div class="input-group-prepend">%s</div>%s' % (self.prepend, output)
        if self.append:
            self.append = self.enclose_value(self.append, self.append_class)
            output = '%s<div class="input-group-append">%s</div>' % (output, self.append,)

        return mark_safe('<div class="input-group">%s</div>' % (output))


class StreamFieldWidget(Widget):
    template_name = 'suit/streamfield/streamfield_widget.html'

    def __init__(self, attrs=None):
        self.model_list = attrs.pop('model_list', [])

        model_list_info = {}
        for block in self.model_list:
            as_list = hasattr(block, "as_list") and block.as_list

            options = block.options if hasattr(block, "options") else BLOCK_OPTIONS
            if hasattr(block, "extra_options"):
                options = deepcopy(options)
                options.update(block.extra_options)

            model_doc = block._meta.verbose_name_plural if as_list else block._meta.verbose_name

            model_list_info[block.__name__] = {
                'model_doc': str(model_doc),
                'abstract': block._meta.abstract,
                'as_list': as_list,
                'options': options,
                'app': block._meta.app_label,
                'admin_url': reverse('admin:%s_%s_changelist' % (block._meta.app_label, block._meta.model_name))
            }

        attrs["model_list_info"] = json.dumps(model_list_info)
        attrs['show_admin_help_text'] = SHOW_ADMIN_HELP_TEXT
        attrs['delete_blocks_from_db'] = DELETE_BLOCKS_FROM_DB
        super().__init__(attrs)

    def format_value(self, value):
        if value != "" and not isinstance(value, StreamObject):
            value = StreamObject(value, self.model_list)
        return value

    class Media:
        js = (
            'suit/vendor/js/lodash.min.js',
            'suit/vendor/js/js.cookie.js',
            'suit/vendor/js/sortable.min.js',
            'suit/vendor/js/vuedraggable.umd.min.js',
            'suit/vendor/js/axios.min.js',
            'suit/js/suit.streamfield.widget.js',
        )


FORMFIELD_FOR_DBFIELD_DEFAULTS[StreamField] = {'widget': StreamFieldWidget}


def _make_attrs(attrs, defaults=None, classes=None):
    result = defaults.copy() if defaults else {}
    if attrs:
        result.update(attrs)
    if classes:
        result["class"] = " ".join((classes, result.get("class", "")))
    return result
