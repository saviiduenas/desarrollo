# -*- coding: utf-8 -*-

import werkzeug
import json
import base64

import odoo.http as http
from odoo.http import request
from odoo import SUPERUSER_ID
from datetime import datetime, timedelta, time
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
import odoo.http as http

class LoanRequest(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(LoanRequest, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        loan_request = request.env['loan.request']
        loan_request_count = loan_request.search_count([('partner_id','=',partner.id)])
        values.update({
            'loan_request_count': loan_request_count,
        })
        return values
        
    @http.route(['/my/loan', '/my/loan/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_loan(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        loan_request = request.env['loan.request']
        domain = []
        archive_groups = self._get_archive_groups('loan.request', domain)
        # count for pager
        loan_request_count = loan_request.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/loan",
            total=loan_request_count,
            page=page,
            step=self._items_per_page
        )
        # search the count to display, according to the pager data
        partner = request.env.user.partner_id
        loans = loan_request.search([('partner_id','=',partner.id)], offset=pager['offset'])
        request.session['my_loan_history'] = loans.ids[:100]

        values.update({
            'loans': loans.sudo(),
            'page_name': 'loan',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/loan',
        })
        return request.render("odoo_customer_supplier_loan_app.portal_my_loan", values)
        
        
    @http.route(['/loan/view/detail/<model("loan.request"):loan>'],type='http',auth="public",website=True)
    def loan_view(self, loan, category='', message=False, search='', **kwargs):
        context = dict(request.env.context or {})
        # loan_request_obj = request.env['loan.request']
        context.update(active_id=loan.id)
        # loan_request_data_list = loan_request_obj
        # loan_request_data = loan_request_obj.sudo().browse(int(loan.id))
        # for items in loan_request_data:
        #     loan_request_data_list.append(items.id)
        return http.request.render('odoo_customer_supplier_loan_app.loan_request_view',{
            'loan_request_data_list': loan,
            'message' : message
        }) 

        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: