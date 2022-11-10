# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import datetime
import calendar
from dateutil.relativedelta import *
from odoo.exceptions import UserError, ValidationError

class LoanRequest(models.Model):
	_name = 'loan.request'
	_inherit = ['mail.thread']
	_description = "Loan Request"

	@api.depends('installment_ids')
	def _get_installment_count(self):
		for loan in self:
			loan.installment_count = len(loan.installment_ids)

	name = fields.Char(string="Number",readonly=True)
	partner_id = fields.Many2one('res.partner',string="Partner",required=True)
	applied_date = fields.Date(string="Applied Date")
	loan_type_id = fields.Many2one('loan.type',string="Loan Type",required=True)
	approve_date = fields.Date(string="Approve Date")
	disbursement_date = fields.Date(string="Disbursement Date")
	company_id = fields.Many2one('res.company' ,default=lambda self : self.env.user.company_id.id,string="Company",required=True)
	user_id = fields.Many2one('res.users',default=lambda self : self.env.user.id,string="User",readonly=True)
	loan_partner_type = fields.Selection([('customer','Customer'),('vendor','Supplier')],string="Loan Partner Type")

	principal_amount = fields.Float(string="Principal Amount",required=True,digits=(32, 2))
	is_interest_payable = fields.Boolean(string="Is Interest Payable",default=True,related="loan_type_id.is_interest_payable")
	interest_mode = fields.Selection([('flat','Flat'),('reducing','Reducing')],string="Interest Mode")
	duration_months = fields.Integer(string="Duration(Months)",required=True,default=1)
	rate = fields.Float(string="Rate",related="loan_type_id.rate", store=True, readonly=True)
	total_loan = fields.Float(string="Total Loan",compute="_compute_loan_amounts", store=True)
	total_interest = fields.Float(string="Total Interest On Loan",compute="_compute_loan_amounts",digits=(32,2), store=True)
	additional_amount = fields.Float(string="Additional Amount Every Month")
	received_from_partner = fields.Float(string="Received From Partner",compute="_compute_balance_on_loan", store=True)		#
	balance_on_loan = fields.Float(string="Balance On Loan",compute="_compute_balance_on_loan", store=True)		#

	loan_proof_ids = fields.Many2many('loan.proof','rel_loan_proof_type_request',string="Loan Proofs",related="loan_type_id.loan_proof_ids")

	disburse_journal_id = fields.Many2one('account.journal',string="Disbure Journal")
	disburse_account_id = fields.Many2one('account.account',string="Disbure Account") 
	disburse_journal_entry_id = fields.Many2one('account.move',string="Disbure Journal Entry",readonly=True, copy=False) 
	repayment_board_journal_id = fields.Many2one('account.journal',string="Loan Repayment Journal")
	
	interest_account_id = fields.Many2one('account.account',string="Interest Account")
	interest_journal_id = fields.Many2one('account.journal',string="Interest Journal")
	account_entery_id = fields.Many2one('account.move',string="Interest On Loan Journal Entry",readonly=True, copy=False)
	interest_recv_account_id = fields.Many2one('account.account',string="Interest Receivable Account")
	partner_account_id = fields.Many2one('account.account',string="Partner Account") 
	borrower_loan_account_id = fields.Many2one('account.account',string="Borrower Loan Account")  

	policy_ids = fields.Many2many('loan.policies','rel_policies_loan_req',string="Policies")
	notes = fields.Text(string="Notes")

	state = fields.Selection([('draft','Draft'),('applied','Applied'),('approve','Approved'),('cancel','Cancel'),('disbursed','Disbursed')],default='draft')

	installment_ids = fields.One2many('loan.installment','loan_id',readonly=True)
	is_compute = fields.Boolean(string="Is Compute",copy=False)
	currency_id = fields.Many2one('res.currency',string="Currency",related="company_id.currency_id")
	attachment_count  =  fields.Integer('Attachments', compute='_get_attachment_count')
	installment_count = fields.Integer(compute="_get_installment_count")


	def button_installment_entries(self):
		return {
			'name': _('Installment Entries'),
			'view_type': 'form',
			'view_mode': 'tree,form',
			'res_model': 'loan.installment',
			'view_id': False,
			'type': 'ir.actions.act_window',
			'domain': [('id', 'in', self.installment_ids.ids)],
		}

	@api.constrains('loan_type_id', 'partner_id','policy_ids','principal_amount')
	def _check_partner(self):
		if self.partner_id not in self.loan_type_id.partner_ids :
			raise ValidationError(_("Partner is not allowed to request for this loan type."))
		else: 
			return
		return

	@api.depends('installment_ids.state','total_loan')
	def _compute_balance_on_loan(self):
		for loan in self :
			total_paid = 0.0
			for line in loan.installment_ids :
				if line.state == 'paid':
					total_paid = total_paid + line.emi_installment

			loan.received_from_partner = total_paid
			loan.balance_on_loan = loan.total_loan - total_paid
		return

	@api.depends('principal_amount','rate','duration_months','installment_ids')
	def _compute_loan_amounts(self):
		for line in self :
			if line.principal_amount > 0 and line.rate > 0 and line.installment_ids:
				principal_amount_total = sum([line.principal_amount for line in line.installment_ids])
				interest_amount_total = sum([line.interest_amount for line in line.installment_ids])
				total_loan = principal_amount_total + interest_amount_total
				total_interest = interest_amount_total
				if line.interest_mode == "flat":
					line.total_loan = round(total_loan)
					line.total_interest = round(total_interest)
				else:
					line.total_loan = total_loan
					line.total_interest = total_interest
		return


	def action_confirm(self):
		if not self.policy_ids:
			raise UserError(_('Please configure or add Customer/Supplier Loan Policy..!'))
		if self.policy_ids :
			max_value = 0.0
			value_gap = 0
			is_max = False
			for polily in self.policy_ids :
				if polily.policy_type == 'max' and polily.basis == 'fix'  :
					is_max = True
					if polily.values > max_value :
						max_value = polily.values

				if polily.policy_type == 'gap' :
					if polily.duration_months > value_gap :
						value_gap = polily.duration_months
						
			if value_gap > 0 :
				loan_res = self.env['loan.request'].search([('partner_id','=',self.partner_id.id),('state','=','disbursed')])
				loan_dates = []
				for emp in loan_res :
					if emp.id == self.id :
						continue 
					last_date = emp.applied_date + relativedelta(months=+emp.duration_months)
					loan_dates.append(last_date)
				
				if len(loan_dates) > 0:
					validate_date = max(loan_dates)
					date_1 = validate_date + relativedelta(months=+value_gap)
					if self.applied_date < date_1 :
						r = relativedelta(date_1, self.applied_date)
						time = r.months
						if r.years > 0:
							time = time + (r.years * 12)
						raise ValidationError(_("You can not apply for loan in next  %s   months") % time ) 

			if self.principal_amount > max_value and is_max == True:
				raise ValidationError(_("Your maximum amount to apply for loan is %s ") % max_value) 
				
		self.write({'state':'applied'})
		return

	def action_approve(self):
		if self.policy_ids :
			max_days = 0
			for polily in self.policy_ids :
				if polily.policy_type == 'qualifying' and polily.days > 0:
					if polily.days > max_days :
						max_days = polily.days
			if max_days > 0 :
				end_date = self.applied_date + relativedelta(days=+max_days)
				if end_date > fields.datetime.today().date() :
					raise ValidationError(_("You can approve this loan after  %s ") % end_date ) 
		self.write({'state':'approve'})
		return

	def action_cancel(self):
		for statement in self:
			statement.installment_ids.unlink()
			statement.is_compute = False
		self.write({'state':'cancel'})
		return

	def reset_draft(self):
		self.write({'state':'draft'})

	def unlink(self):
		if self.state != 'draft':
			raise UserError(_('You can only delete an loan request in draft state.'))
		self.installment_ids.unlink()
		return super(LoanRequest, self).unlink()

	@api.model
	def create(self, vals):
		seq = self.env['ir.sequence'].next_by_code('loan.request') or '/'
		vals['name'] = seq
		return super(LoanRequest, self).create(vals)

	def compute_loan(self):
		if not self.approve_date:
			raise UserError("You should have defined an 'Approve Date' in your Loan Request!")
		month = self.approve_date.month
		year = self.approve_date.year
		
		month_principal_amount = self.principal_amount / self.duration_months
		
		total_interest_amount = (self.principal_amount * self.rate * self.duration_months) / (12 * 100)
		interest_amount = total_interest_amount / self.duration_months
		
		installment_obj = self.env['loan.installment']
		installment_list = []

		months = self.duration_months
		amount_to_pay = self.principal_amount 

		common_rate = self.rate
		duration_months_change = self.duration_months
		opening_balance_change = self.principal_amount

		for number in range(1,self.duration_months+1):

			if month == 12 : 
				month = 1
				year = year + 1
			else : 
				month = month + 1

			start_date = datetime.date(year, month, 1)
			_, num_days = calendar.monthrange(year, month)
			end_date = datetime.date(year, month, num_days)

			if self.interest_mode == "flat":
				month_principal_amount = round(month_principal_amount, 2)
				interest_amount = round(interest_amount, 2)
				principal_ending_balance = opening_balance_change  - month_principal_amount
				principal_ending_balance = round(principal_ending_balance, 2)
				if number == (self.duration_months):
					month_principal_amount = month_principal_amount + principal_ending_balance
					principal_ending_balance = opening_balance_change - month_principal_amount
					principal_ending_balance = round(abs(principal_ending_balance), 2)

				vals = {
					'loan_id' : self.id ,
					'partner_id':self.partner_id.id,
					'opening_balance_amount': opening_balance_change,
					'principal_amount': month_principal_amount,
					'interest_amount':  interest_amount,
					'emi_installment' : month_principal_amount + interest_amount,
					'ending_balance_amount' : principal_ending_balance,
					'state' : 'unpaid',
					'currency_id' : self.company_id.currency_id.id,
					'loan_type_id' : self.loan_type_id.id ,
					'installment_number' : number,
					'date_from' : start_date,'date_to' : end_date,
					'loan_partner_type' : self.loan_partner_type,
					}
				installment  = installment_obj.create(vals)
				opening_balance_change = principal_ending_balance
				duration_months_change = duration_months_change - 1

			elif self.interest_mode == "reducing":
				# Reducing Calculation
				rate_of_intrest = (self.rate)/(12 * 100)
				p = self.principal_amount
				r = rate_of_intrest
				m = self.duration_months

				power = pow((1 + r), m)

				equated_monthly_installment =  (p  * r * (power)) / ( power - 1)
				equated_monthly_installment = round(equated_monthly_installment, 2)

				basic_installment = ( opening_balance_change / duration_months_change)
				basic_installment = round(basic_installment, 2)

				intrest_of_basic_installment = ( basic_installment * common_rate * duration_months_change) / (100 * 12)
				intrest_of_basic_installment = round(intrest_of_basic_installment, 2)
				
				emi_principal_amount = (equated_monthly_installment - intrest_of_basic_installment)
				emi_principal_amount = round(emi_principal_amount, 2)

				principal_ending_balance = ( opening_balance_change - emi_principal_amount )
				principal_ending_balance = round(principal_ending_balance, 2)

				if number == (self.duration_months):
					emi_principal_amount = emi_principal_amount - abs(principal_ending_balance)
					emi_principal_amount = round(emi_principal_amount, 2)
					principal_ending_balance = ( opening_balance_change - emi_principal_amount )
					principal_ending_balance = round(abs(principal_ending_balance), 2)

				vals = {
					'loan_id' : self.id ,
					'partner_id':self.partner_id.id,
					'opening_balance_amount': opening_balance_change,
					'principal_amount': emi_principal_amount,
					'interest_amount': intrest_of_basic_installment,
					'emi_installment' : equated_monthly_installment,
					'ending_balance_amount' : principal_ending_balance,
					'state' : 'unpaid',
					'currency_id' : self.company_id.currency_id.id,
					'loan_type_id' : self.loan_type_id.id ,
					'installment_number' : number,
					'date_from' : start_date,'date_to' : end_date
					}
				installment  = installment_obj.create(vals)
				opening_balance_change = principal_ending_balance
				duration_months_change = duration_months_change - 1
			installment_list.append(installment.id)
		#self.installment_ids = [(6,0,installment_list)]
		self.is_compute = True
		return      


	def disburse_loan(self):

		if not self.applied_date:
			raise UserError("You should have defined an 'Applied Date' in your Loan Request!")

		for line in self.installment_ids : 
			if self.loan_type_id.repayment_method == "direct" :
				line.pay_from_payroll = True

			elif self.loan_type_id.repayment_method == "payroll" :
				line.pay_from_payroll = False

		account_move = self.env['account.move']

		name_of = self.partner_id.name
		
		if not self.partner_account_id:
			raise ValidationError(("Please configure partner account in loan system..!"))

		if not self.disburse_journal_id.payment_credit_account_id:
			raise ValidationError(("Please configure payment credit account from disburse journal in loan system..!"))

		debit_line = [0,0,{'account_id' : self.partner_account_id.id,
							'partner_id' : self.user_id.partner_id.id,
							'name' : 'Loan Of ' + name_of,
							'debit' : self.principal_amount,
							'credit' : 0.0
							}]


		credit_line = [0,0,{'account_id' :  self.disburse_journal_id.payment_credit_account_id.id,
							'partner_id' : self.user_id.partner_id.id,
							'name' : 'Loan Of ' + name_of,
							'debit' : 0.0,
							'credit' : self.principal_amount
							}]

		move_line = [debit_line,credit_line]

		jounral = account_move.create({
					'date': self.applied_date,
					'journal_id' :self.disburse_journal_id.id,
					'ref' : str(self.name) ,
					'line_ids' : move_line})

		jounral.action_post()
		self.write({'state' : 'disbursed','disburse_journal_entry_id':jounral.id,'disbursement_date' : fields.datetime.now()})	# 

		int_debit_line = [0,0,{'account_id' : self.interest_recv_account_id.id,
							'partner_id' : self.user_id.partner_id.id,
							'name' : 'Loan Of ' + name_of,
							'debit' : self.total_interest,
							'credit' : 0.0
							}]


		int_credit_line = [0,0,{'account_id' :  self.interest_account_id.id,
							'partner_id' : self.user_id.partner_id.id,
							'name' : 'Loan Of ' + name_of,
							'debit' : 0.0,
							'credit' : self.total_interest
							}]

		int_move_line = [int_debit_line,int_credit_line]

		int_jounral = account_move.create({
					'date': self.applied_date,
					'journal_id' :self.interest_journal_id.id,
					'ref' : str(self.name) ,
					'line_ids' : int_move_line})

		int_jounral.action_post()
		self.write({'state' : 'disbursed','account_entery_id':int_jounral.id,'disbursement_date' : fields.datetime.now()})	#
		
		
	def _get_attachment_count(self):
		for loan in self:
			attachment_ids = self.env['ir.attachment'].search([('loan_request_id','=',loan.id)])
			loan.attachment_count = len(attachment_ids)

	def attachment_on_loan_button(self):
		self.ensure_one()
		return {
			'name': 'Attachment.Details',
			'type': 'ir.actions.act_window',
			'view_mode': 'tree,form',
			'res_model': 'ir.attachment',
			'domain': [('loan_request_id', '=', self.id)],
		}
		
	@api.onchange('partner_id')
	def onchange_partner(self):
		if self.partner_id.policy_ids.ids:
			self.policy_ids = self.partner_id.policy_ids.ids

	@api.onchange('loan_type_id')
	def onchange_loan_type_id(self):
		self.interest_mode = self.loan_type_id.interest_mode
		return

		
class ir_attachment(models.Model):
	_inherit='ir.attachment'

	loan_request_id  =  fields.Many2one('loan.request', 'Loan Request')
	
class Website(models.Model):

	_inherit = "website"
	
	def get_loan_details(self):            
		partner_brw = self.env['res.users'].browse(self._uid)
		loan_ids = self.env['loan.request'].search([('partner_id','=',partner_brw.partner_id.id)])
		return loan_ids
		
