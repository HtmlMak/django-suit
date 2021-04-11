from django.contrib import admin
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.utils.safestring import mark_safe
import json
from importlib import import_module
from django.contrib.admin.options import TO_FIELD_VAR
from django.template.response import TemplateResponse
from django.conf import settings

try:
    from django.urls import reverse_lazy
except:
    from django.core.urlresolvers import reverse_lazy

"""
Adapted by using following examples:
https://djangosnippets.org/snippets/2887/
http://stackoverflow.com/a/7192721/641263
"""

link_to_prefix = 'link_to_'


def get_admin_url(instance, admin_prefix='admin', current_app=None):
    if not instance.pk:
        return
    return reverse_lazy(
        '%s:%s_%s_change' % (admin_prefix, instance._meta.app_label, instance._meta.model_name),
        args=(instance.pk,),
        current_app=current_app
    )


def get_related_field(name, short_description=None, admin_order_field=None, admin_prefix='admin'):
    """
    Create a function that can be attached to a ModelAdmin to use as a list_display field, e.g:
    client__name = get_related_field('client__name', short_description='Client')
    """
    as_link = name.startswith(link_to_prefix)
    if as_link:
        name = name[len(link_to_prefix):]
    related_names = name.split('__')

    def getter(self, obj):
        for related_name in related_names:
            if not obj:
                continue
            obj = getattr(obj, related_name)
        if obj and as_link:
            obj = mark_safe(u'<a href="%s" class="link-with-icon">%s<i class="fa fa-caret-right"></i></a>' % \
                            (get_admin_url(obj, admin_prefix, current_app=self.admin_site.name), obj))
        return obj

    getter.admin_order_field = admin_order_field or name
    getter.short_description = short_description or related_names[-1].title().replace('_', ' ')
    if as_link:
        getter.allow_tags = True
    return getter


class RelatedFieldAdminMetaclass(type(admin.ModelAdmin)):
    related_field_admin_prefix = 'admin'

    def __new__(cls, name, bases, attrs):
        new_class = super(RelatedFieldAdminMetaclass, cls).__new__(cls, name, bases, attrs)

        for field in new_class.list_display:
            if '__' in field or field.startswith(link_to_prefix):
                if not hasattr(new_class, field):
                    setattr(new_class, field, get_related_field(
                        field, admin_prefix=cls.related_field_admin_prefix))

        return new_class


class RelatedFieldAdmin(admin.ModelAdmin):
    """
    Version of ModelAdmin that can use linked and related fields in list_display, e.g.:
    list_display = ('link_to_user', 'address__city', 'link_to_address__city', 'address__country__country_code')
    """
    __metaclass__ = RelatedFieldAdminMetaclass

    def get_queryset(self, request):
        qs = super(RelatedFieldAdmin, self).get_queryset(request)

        # Include all related fields in queryset
        select_related = []
        for field in self.list_display:
            if '__' in field:
                if field.startswith(link_to_prefix):
                    field = field[len(link_to_prefix):]
                select_related.append(field.rsplit('__', 1)[0])

        # Include all foreign key fields in queryset.
        # This is based on ChangeList.get_query_set().
        # We have to duplicate it here because select_related() only works once.
        # Can't just use list_select_related because we might have multiple__depth__fields it won't follow.
        model = qs.model
        for field_name in self.list_display:
            try:
                field = model._meta.get_field(field_name)
            except FieldDoesNotExist:
                continue

            if isinstance(field.remote_field, models.ManyToOneRel):
                select_related.append(field_name)

        return qs.select_related(*select_related)


STREAMBLOCKS_MODELS = []

for app in settings.INSTALLED_APPS:
    try:
        module = import_module("%s.models" % app)

        if hasattr(module, 'STREAMBLOCKS_MODELS'):
            STREAMBLOCKS_MODELS.extend(module.STREAMBLOCKS_MODELS)
    except ModuleNotFoundError as e:
        pass


class StreamBlocksAdmin(admin.ModelAdmin):
    change_form_template = 'suit/streamfield/admin/change_form.html'
    popup_response_template = 'suit/streamfield/admin/streamfield_popup_response.html'

    def response_add(self, request, obj, post_url_continue=None):
        if "block_id" in request.POST:
            opts = obj._meta
            to_field = request.POST.get(TO_FIELD_VAR)
            attr = str(to_field) if to_field else opts.pk.attname
            value = obj.serializable_value(attr)
            popup_response_data = json.dumps({
                'app_id': request.POST.get("app_id"),
                'block_id': request.POST.get("block_id"),
                'instance_id': str(value),
            })
            return TemplateResponse(request, self.popup_response_template, {
                'popup_response_data': popup_response_data,
            })
        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        if "block_id" in request.POST:
            opts = obj._meta
            to_field = request.POST.get(TO_FIELD_VAR)
            attr = str(to_field) if to_field else opts.pk.attname
            value = request.resolver_match.kwargs['object_id']
            new_value = obj.serializable_value(attr)
            popup_response_data = json.dumps({
                'action': 'change',
                'app_id': request.POST.get("app_id"),
                'block_id': request.POST.get("block_id"),
                'instance_id': request.POST.get("instance_id"),
            })
            return TemplateResponse(request, self.popup_response_template, {
                'popup_response_data': popup_response_data,
            })

        return super().response_change(request, obj)

    def response_delete(self, request, obj_display, obj_id):
        if "block_id" in request.POST:
            popup_response_data = json.dumps({
                'action': 'delete',
                'value': str(obj_id),
                'app_id': request.POST.get("app_id"),
                'block_id': request.POST.get("block_id"),
                'instance_id': request.POST.get("instance_id"),
            })
            return TemplateResponse(request, self.popup_response_template, {
                'popup_response_data': popup_response_data,
            })

        return super().response_delete(request, obj_display, obj_id)


# if user defined admin for his blocks, then do not autoregiser block models
for model in STREAMBLOCKS_MODELS:
    if not model._meta.abstract and not admin.site.is_registered(model):
        admin.site.register(model, StreamBlocksAdmin)
