from importlib import import_module
from django.urls import include, path
from django.conf import settings
from django.contrib.auth.decorators import login_required

from . import views

STREAMBLOCKS_MODELS = []

for app in settings.INSTALLED_APPS:
    try:
        module = import_module("%s.models" % app)

        if hasattr(module, 'STREAMBLOCKS_MODELS'):
            STREAMBLOCKS_MODELS.append(*module.STREAMBLOCKS_MODELS)
    except ModuleNotFoundError as e:
        pass

admin_instance_urls = []

for model in STREAMBLOCKS_MODELS:
    if not model._meta.abstract:
        block_path = path(
            'admin-instance/%s/<int:pk>' % model.__name__.lower(),
            login_required(views.admin_instance_class(model).as_view()),
            name='admin-instance'
        )
    else:
        block_path = path(
            'abstract-block/%s/' % model.__name__.lower(),
            login_required(views.abstract_block_class(model).as_view()),
            name='abstract-block'
        )

    admin_instance_urls.append(block_path)

urlpatterns = [
    path(
        'admin-instance/<app_label>/<model_name>/<int:pk>/delete/',
        login_required(views.delete_instance),
        name='admin-instance-delete'
    ),
    *admin_instance_urls
]
