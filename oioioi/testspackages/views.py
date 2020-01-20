import os

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _

from oioioi.base.menu import menu_registry
from oioioi.base.permissions import (enforce_condition, make_request_condition,
                                     not_anonymous)
from oioioi.base.utils import request_cached
from oioioi.contests.utils import (can_enter_contest, contest_exists,
                                   is_contest_admin, visible_problem_instances)
from oioioi.filetracker.utils import stream_file
from oioioi.testspackages.models import TestsPackage
from oioioi.contests.attachment_registration import attachment_registry, attachment_registry_problemset


@request_cached
def visible_tests_packages(request):
    problems = [pi.problem for pi in visible_problem_instances(request)]
    tests_packages = TestsPackage.objects.filter(problem__in=problems)
    return [tp for tp in tests_packages
            if tp.is_visible(request.timestamp) and tp.package is not None]


@attachment_registry.register
def get_tests(request):
    tests = []
    for tp in visible_tests_packages(request):
        t = {'category': tp.problem,
             'name': os.path.basename(tp.name) + '.zip',
             'description': tp.description,
             'link': reverse('test', kwargs={'contest_id': request.contest.id,
                                             'package_id': tp.id}),
             'pub_date': tp.publish_date}
        tests.append(t)
    return tests


@attachment_registry_problemset.register
def get_tests_for_problem(request, problem):
    tests = []
    if is_contest_admin(request):
        tests_packages = TestsPackage.objects.filter(problem=problem)
        for tp in tests_packages:
            t = {'category': tp.problem,
                 'name': os.path.basename(tp.name) + '.zip',
                 'description': tp.description,
                 'link': reverse('test_for_problem', kwargs={'contest_id': request.contest.id,
                                                             'package_id': tp.id}),
                 'pub_date': tp.publish_date}
            tests.append(t)
    return tests


def get_tests_package_file(test_package):
    file_name = '%s.zip' % test_package.name
    file_name = file_name.encode('utf-8')
    return stream_file(test_package.package, name=file_name)


@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
def test_view(request, package_id):
    tp = get_object_or_404(TestsPackage, id=package_id)
    if not is_contest_admin(request) and not tp.is_visible(request.timestamp):
        raise PermissionDenied
    return get_tests_package_file(tp)


@enforce_condition(not_anonymous)
def test_view_for_problem(request, package_id):
    if not is_contest_admin(request):
        raise PermissionDenied
    tp = get_object_or_404(TestsPackage, id=package_id)
    return get_tests_package_file(tp)
