# -*- coding: utf-8 -*-

from flask import jsonify, request
import traceback
from lapdance import factory
from lapdance.core import cors, swagger
from lapdance.exceptions import LapdanceError
from ldap3.core.exceptions import LDAPException, LDAPOperationResult
from .users import bp as users_bp
from .groups import bp as groups_bp


def register_blueprints(app, blueprints):
    for bp in blueprints:
        app.register_blueprint(bp, url_prefix='/{0}/{1}'.format('api', bp.name))


def create_app(*args, **kwargs):
    app = factory.create_app(__name__, *args, **kwargs)
    cors.init_app(app)

    # Attach bundles
    register_blueprints(app, [users_bp, groups_bp])

    # Init swagger and inject model props
    swagger.init_app(app)

    @app.errorhandler(LDAPException)
    def handle_ldap_error(error):
        status = 400

        if isinstance(error, LDAPOperationResult):
            errmsg = error.__dict__
            [errmsg.pop(k) for k in ['dn', 'response']]
        else:

            status = 500
            errmsg = "LDAP error: {0}".format(error)

        if app.config['ENV'] == 'devel' and app.config['DEBUG'] == True:
            tb = traceback.format_tb(error.__traceback__)
            app.logger.debug(''.join(tb))

        app.logger.error(errmsg)

        response = errmsg if app.config.get('LAPDANCE_SHOW_LDAP_ERROR_DETAILS') else 'Error performing LDAP operation'
        return jsonify(code=status, message=response), status

    @app.errorhandler(LapdanceError)
    def handle_invalid_usage(error):
        msg = "{0} (path: {1}, method: {2})".format(error.message, request.path, request.method)

        if app.config['ENV'] == 'devel' and app.config['DEBUG'] is True:
            tb = traceback.format_tb(error.__traceback__)
            app.logger.debug(''.join(tb))

        if str(error.status_code)[0] == '4':  # Log info on HTTP 4xx
            app.logger.info(msg)
        else:
            app.logger.warning(msg)

        return jsonify(error.to_dict()), error.status_code

    return app