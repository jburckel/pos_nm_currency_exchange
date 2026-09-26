# Demo data of pos_nm_currency_exchange on the screenshots database (odoo-bin shell -d shots < shots_data.py)
from odoo import Command
env = env(user=env.ref("base.user_admin").id)
config = env['pos.config'].browse(1)
company = config.company_id
main = config.currency_id
eur = env.ref('base.EUR'); gbp = env.ref('base.GBP')
Account = env['account.account']
income = Account.search([('account_type', '=', 'income_other'), ('company_ids', 'in', company.id)], limit=1) \
    or Account.search([('account_type', '=', 'income'), ('company_ids', 'in', company.id)], limit=1)
config.write({'nm_exchange_enabled': True, 'nm_exchange_income_account_id': income.id, 'nm_exchange_customer_threshold': 500.0})
Setting = env['pos.nm.currency.setting']
for currency, vals in ((eur, {'exchange_commission_percent': 2.0, 'exchange_commission_fixed': 1.0, 'exchange_commission_min': 3.0}),
                       (gbp, {'exchange_commission_percent': 1.5, 'exchange_commission_fixed': 0.0, 'exchange_commission_min': 2.0})):
    setting = Setting.search([('config_id', '=', config.id), ('currency_id', '=', currency.id)], limit=1)
    setting.write(vals)
cash_pm = config._get_cash_payment_method()
journal = cash_pm.journal_id
journal.invalidate_recordset(['current_statement_balance', 'has_statement_lines'])
session = config.current_session_id
if session.state != 'opened':
    session.set_multicurrency_counts({eur.id: 300.0, gbp.id: 120.0}, cashier_name='Marie Dupont')
    session.set_opening_control(250.0, '')
print('session', session.id, session.state, 'EUR drawer', config._nm_currency_balance(eur), 'GBP drawer', config._nm_currency_balance(gbp))
customers = {n: env['res.partner'].search([('name', '=', n)], limit=1) for n in ('Lena Fischer', 'Thomas Leroy', 'Olivia Bennett')}
Exchange = env['pos.nm.exchange']
r1 = Exchange.create_from_ui(session.id, main.id, 200.0, eur.id, partner_id=customers['Lena Fischer'].id, cashier_name='Marie Dupont')
r2 = Exchange.create_from_ui(session.id, gbp.id, 60.0, main.id, cashier_name='Marie Dupont', note='Tourist')
r3 = Exchange.create_from_ui(session.id, eur.id, 150.0, main.id, partner_id=customers['Thomas Leroy'].id, cashier_name='Marie Dupont')
r4 = Exchange.create_from_ui(session.id, main.id, 80.0, gbp.id, cashier_name='Paul Martin')
for r in (r1, r2, r3, r4):
    print(r['name'], r['amount_in'], r['currency_in'], '->', r['amount_out'], r['currency_out'], 'commission', r['commission'])
env.cr.commit()
print('IDS config=%s session=%s token=%s eur_setting=%s' % (config.id, session.id, config.access_token,
      Setting.search([('config_id', '=', config.id), ('currency_id', '=', eur.id)], limit=1).id))
