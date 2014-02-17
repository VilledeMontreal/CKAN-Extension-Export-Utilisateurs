import logging
import os
import csv
import tempfile

import ckan.plugins as plugins

log = logging.getLogger(__name__)


class ExportUsersPlugin(plugins.SingletonPlugin):

    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)

    def update_config(self, config):

        plugins.toolkit.add_template_directory(config, 'theme/templates')

    def after_map(self, map):
        controller = 'ckanext.export_users.plugin:ExportUsersController'
        map.connect('/export', controller=controller,
                    action='export_users_page')
        map.connect('/export_csv_file', controller=controller,
                    action='export_users_csv')

        return map

    ## IAuthfunctions
    def get_auth_functions(self):

        return {
            'export_page': export_page_auth,
            'export_csv': export_csv_auth,
        }

    ## IActions
    def get_actions(self):
        # return a dict with the export function that we want to add
        return {
            'export_page': export_page,
            'export_csv': export_csv,
        }


def export_page_auth(context, data_dict):

    return {'success': False, 'msg': 'Only sysadmins can see this page'}


def export_page(context, data_dict):

    plugins.toolkit.check_access('export_page', context, data_dict)


def export_csv_auth(context, data_dict):

    return {'success': False,
            'msg': 'Only sysadmins can export user list as csv file'}


def export_csv(context, data_dict):

    # Check if user is a sysadmin
    plugins.toolkit.check_access('export_csv', context, data_dict)

    if not plugins.toolkit.check_ckan_version('2.1'):
        log.warn('This extension has only been tested on CKAN 2.1!')

    #result = plugins.toolkit.get_action('user_list')(context, data_dict)
    data_dict = {
        'order_by': 'name',
    }

    result = plugins.toolkit.get_action('user_list')(context, data_dict)

    # Create a temp file
    fd, tmp_file_path = tempfile.mkstemp(suffix=".csv")

    with open(tmp_file_path, 'w') as f:
        field_names = ['display_name', 'name', 'about',
                       'created', 'email', 'sysadmin',
                       'number_of_edits',
                       'number_administered_packages']

        writer = csv.DictWriter(f, fieldnames=field_names,
                                quoting=csv.QUOTE_ALL)

        writer.writerow(dict((n, n) for n in field_names))
        for user in result:
            row = {}
            for field_name in field_names:
                row[field_name] = unicode(user[field_name]).encode('utf-8')

            writer.writerow(row)

        return {
            'file': tmp_file_path,
        }


class ExportUsersController(plugins.toolkit.BaseController):

    def export_users_page(self):
        try:
            result = plugins.toolkit.get_action('export_page')()
        except plugins.toolkit.NotAuthorized:
            plugins.toolkit.abort(401, 'Not authorized to see export page')
        return plugins.toolkit.render('export.html')

    def export_users_csv(self):

        try:
            result = plugins.toolkit.get_action('export_csv')()
        except plugins.toolkit.NotAuthorized:
            plugins.toolkit.abort(401, 'Not authorized to export users')

        with open(result['file'], 'r') as f:
            content = f.read()

        os.remove(result['file'])

        plugins.toolkit.response.headers['Content-Type'] = 'application/csv'
        plugins.toolkit.response.headers['Content-Length'] = len(content)
        plugins.toolkit.response.headers['Content-Disposition'] = \
            'attachment; filename="export-users.csv"'

        return content
