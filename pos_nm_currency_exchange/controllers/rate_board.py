# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.tools import consteq


class NmExchangeRateBoard(http.Controller):
    """Rate board of a counter or of an exchange office on a screen facing
    the customers (a TV, a tablet, the customer display of Odoo).

    Public pages, protected by a token: the access token of the point of
    sale (the one of its customer display) or the board token of the
    office. The page loads the rates once, then reloads them through the
    JSON route every ``refresh`` seconds without reloading itself."""

    def _nm_config(self, config_id, access_token):
        config = request.env['pos.config'].sudo().browse(int(config_id)).exists()
        if not config or not config.access_token or not consteq(access_token or '', config.access_token) \
                or not config.nm_exchange_enabled:
            return None
        return config.with_company(config.company_id)

    def _nm_office(self, office_id, access_token):
        office = request.env['pos.nm.exchange.office'].sudo().browse(int(office_id)).exists()
        if not office or not office.active or not office.board_token \
                or not consteq(access_token or '', office.board_token):
            return None
        return office.with_company(office.company_id)

    def _nm_lang(self, company, lang=None):
        """Language of the board: ``lang`` when it is installed (a screen
        set with ?lang=fr_FR), else the language of the company."""
        installed = dict(request.env['res.lang'].sudo().get_installed())
        if lang and lang in installed:
            return lang
        company_lang = company.partner_id.lang
        return company_lang if company_lang in installed else 'en_US'

    def _nm_render(self, board, refresh, data_url, lang, display=False):
        request.update_context(lang=lang)
        return request.render('pos_nm_currency_exchange.rate_board_page', {
            'board': board,
            'refresh': max(10, refresh or 60),
            'data_url': data_url + f'&lang={lang}',
            'display': display,
            'html_lang': lang.replace('_', '-'),
        })

    @http.route('/pos_nm_exchange/board/<int:config_id>', type='http', auth='public', website=False,
                sitemap=False)
    def config_board(self, config_id, access_token=None, display=None, lang=None, **kw):
        config = self._nm_config(config_id, access_token)
        if not config:
            return request.not_found()
        lang = self._nm_lang(config.company_id, lang)
        refresh = config.nm_exchange_office_id.board_refresh or 60
        return self._nm_render(
            config.with_context(lang=lang)._nm_rate_board(), refresh,
            f'/pos_nm_exchange/board/{config.id}/data?access_token={config.access_token}', lang, bool(display))

    @http.route('/pos_nm_exchange/board/<int:config_id>/data', type='http', auth='public', website=False,
                sitemap=False)
    def config_board_data(self, config_id, access_token=None, lang=None, **kw):
        config = self._nm_config(config_id, access_token)
        if not config:
            return request.not_found()
        lang = self._nm_lang(config.company_id, lang)
        return request.make_json_response(
            config.with_context(lang=lang)._nm_rate_board(), headers={'Cache-Control': 'no-store'})

    @http.route('/pos_nm_exchange/office_board/<int:office_id>', type='http', auth='public', website=False,
                sitemap=False)
    def office_board(self, office_id, access_token=None, display=None, lang=None, **kw):
        office = self._nm_office(office_id, access_token)
        if not office or not office._nm_reference_config():
            return request.not_found()
        lang = self._nm_lang(office.company_id, lang)
        return self._nm_render(
            office.with_context(lang=lang)._nm_rate_board(), office.board_refresh,
            f'/pos_nm_exchange/office_board/{office.id}/data?access_token={office.board_token}', lang,
            bool(display))

    @http.route('/pos_nm_exchange/office_board/<int:office_id>/data', type='http', auth='public', website=False,
                sitemap=False)
    def office_board_data(self, office_id, access_token=None, lang=None, **kw):
        office = self._nm_office(office_id, access_token)
        if not office or not office._nm_reference_config():
            return request.not_found()
        lang = self._nm_lang(office.company_id, lang)
        return request.make_json_response(
            office.with_context(lang=lang)._nm_rate_board(), headers={'Cache-Control': 'no-store'})
