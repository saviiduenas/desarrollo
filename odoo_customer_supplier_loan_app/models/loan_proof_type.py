# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import datetime

class LoanProof(models.Model):
	_name = 'loan.proof'
	_description = 'Loan Proof'

	name = fields.Char(string="Name")
	is_mandatory = fields.Boolean(string='Mandatory')

class LoanTypes(models.Model):
	_name = 'loan.type'
	_description = "Loan Types"

	name = fields.Char(string="Name",required=True)
	code = fields.Char(string="Code")
	is_interest_payable = fields.Boolean(string="Is Interest Payable",default=True)
	interest_mode = fields.Selection([('flat','Flat'),('reducing','Reducing')],default="flat",string="Interest Mode")
	repayment_method = fields.Selection([('payroll','Deduction From Payroll'),('direct','Direct Cash/Cheque')],default="payroll",string="Repayment Method")
	disburse_method = fields.Selection([('payroll','Deduction From Payroll'),('direct','Direct Cash/Cheque')],default="direct",string="Disburse Method")
	company_id = fields.Many2one('res.company' ,default=lambda self : self.env.user.company_id.id,string="Company",readonly=True)
	interest_account = fields.Many2one('account.account',string="Interest Account")
	rate = fields.Float(string="Rate")

	loan_proof_ids = fields.Many2many('loan.proof','rel_loan_proof_type_id',string="Loan Proofs")
	partner_category_ids = fields.Many2many('res.partner.category','rel_partner_category_id',string="Partner Category")
	partner_ids = fields.Many2many('res.partner','rel_partner_loan_type_id',string="Partner")
	
	_sql_constraints = [
			('name_uniq', 'unique (code)', _('The code must be unique !')),
		]

class LoanPolicies(models.Model):
	_name = 'loan.policies'
	_description = "Loan Policies"

	name = fields.Char(string="Name",required=True)
	code = fields.Char(string="Code")

	company_id = fields.Many2one('res.company' ,default=lambda self : self.env.user.company_id.id,string="Company",readonly=True)
	policy_type = fields.Selection([('max','Max Loan Amount'),('gap','Gap Between Two Loans'),('qualifying','Qualifying Period')],string="Policy Type")
	basis = fields.Selection([('fix','Fix Amount')],string='Basis')
	values = fields.Float(string="Values")
	duration_months = fields.Integer(string="Duration(Months)")
	days = fields.Integer(string="Days",default=90)
	partner_category_ids = fields.Many2many('res.partner.category','rel_partner_category_policies',string="Partner Category")
	partner_ids = fields.Many2many('res.partner','rel_partner_policies_id',string="Partner")

	_sql_constraints = [
			('name_uniq', 'unique (code)', _('The code must be unique !')),
		]
