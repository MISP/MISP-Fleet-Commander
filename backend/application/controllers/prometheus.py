from flask import Blueprint, Response

from application.controllers.instance import token_required
import application.models.prometheus as prometheusModel

BPprometheus = Blueprint('prometheus', __name__)


@BPprometheus.route('/metrics', methods=['GET'])
@token_required
def metrics(user):
    """The latest usage metrics of the user's monitored servers, in the Prometheus text format. Authenticate with
    `Authorization: Apikey <key>` (Prometheus: `authorization: {type: Apikey, credentials: <key>}`) or a login token.
    Served from what MFC stored: a scrape never queries MISP"""
    return Response(prometheusModel.exposition(user), content_type=prometheusModel.CONTENT_TYPE)
