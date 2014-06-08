from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.http import HttpResponse
from django.shortcuts import render, resolve_url
from django.utils.http import is_safe_url
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from sokoban.utils import json_api


@sensitive_post_parameters()
@csrf_protect
@never_cache
@json_api
def login(request):
    redirect_to = request.REQUEST.get('next', '')
    if request.method == 'GET':
        request.session.set_test_cookie()
        return render(request, 'accounts/login.html', dictionary=dict(
            form=AuthenticationForm(),
            next=redirect_to,
        ))
    elif request.method == 'POST':
        login_form = AuthenticationForm(data=request.POST)
        if not login_form.is_valid():
            return {
                'errors': login_form.errors.as_ul(),
            }, 400
        if not is_safe_url(url=redirect_to, host=request.get_host()):
            redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)
        auth_login(request, login_form.get_user())
        if request.session.test_cookie_worked():
            request.session.delete_test_cookie()
        return {
            'username': request.user.username,
            'next': redirect_to,
        }
    else:
        return HttpResponse(status=405)


@json_api
def logout(request):
    next_page = '/'
    if 'next' in request.REQUEST:
        next_page = request.REQUEST['next']
        # Security check -- don't allow redirection to a different host.
        if not is_safe_url(url=next_page, host=request.get_host()):
            next_page = request.path

    if request.method == 'GET':
        return render(request, 'accounts/logged_out.html', dictionary=dict(
            next=next_page,
        ))
    else:
        auth_logout(request)
        return {
            'success': 1,
        }



