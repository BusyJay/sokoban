from django.conf.urls import patterns, url, include

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns(
    'sokoban.views',
    url(r'^$', 'index', name='index'),
    url(r'^dashboard/$', 'dashboard', name='dashboard'),
    url(r'^home/$', 'home', name='home'),
    url(r'^403/$', 'alert_login_required', name='login_required'),
    url(r'^(?P<owner>.+)/projects/', 'list_projects', name='project_list'),
    url(r'^project/(?P<name>.*)/(?P<action>.*)/$', 'rest_project',
        name='project_rest'),
    url(r'^project/(?P<name>.*)/$', 'rest_project', name='project_rest'),
    url(r'^middleware/$', 'installed_middle_ware', name="middle_ware_list"),
    url(r'^log/(?P<project_name>.+)/$', 'get_log', name="get_log"),
    url(r'^logs/$', 'get_log', name="get_logs", kwargs={'project_name': None}),
    url(r'^admin/', include(admin.site.urls)),
    url('^accounts/', include('account.urls')),
    url('^scheduler/', include('scheduler.urls')),
)
