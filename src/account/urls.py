from django.conf.urls import patterns, url

__author__ = 'jay'


urlpatterns = patterns(
    'account.views',
    url('login/', 'login', name='login'),
    url('logout/', 'logout', name='logout'),
)
