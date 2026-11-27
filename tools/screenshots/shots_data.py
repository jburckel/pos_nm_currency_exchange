# Demo data of pos_nm_currency_exchange on the screenshots database (odoo-bin shell -d shots < shots_data.py)
from datetime import date

env = env(user=env.ref("base.user_admin").id)
config = env['pos.config'].browse(1)
company = config.company_id
main = config.currency_id
eur = env.ref('base.EUR'); gbp = env.ref('base.GBP')
Account = env['account.account']
income = Account.search([('account_type', '=', 'income_other'), ('company_ids', 'in', company.id)], limit=1) \
    or Account.search([('account_type', '=', 'income'), ('company_ids', 'in', company.id)], limit=1)
config.write({
    'nm_exchange_enabled': True, 'nm_exchange_income_account_id': income.id,
    'nm_exchange_customer_threshold': 250.0, 'nm_exchange_document_threshold': 400.0,
    'nm_exchange_linked_days': 7, 'nm_exchange_licence': 'MSB-2026-0418',
    'use_header_or_footer': True, 'receipt_header': 'Exchange counter - open 7 days a week',
    'receipt_footer': 'Keep this receipt: it is proof of your exchange.',
})
Setting = env['pos.nm.currency.setting']
for currency, vals in ((eur, {'exchange_sell_margin_percent': 2.0, 'exchange_commission_percent': 2.0,
                              'exchange_commission_fixed': 1.0, 'exchange_commission_min': 3.0}),
                       (gbp, {'exchange_commission_percent': 1.5, 'exchange_commission_fixed': 0.0, 'exchange_commission_min': 2.0})):
    setting = Setting.search([('config_id', '=', config.id), ('currency_id', '=', currency.id)], limit=1)
    setting.write(vals)
cash_pm = config._get_cash_payment_method()
journal = cash_pm.journal_id
journal.invalidate_recordset(['current_statement_balance', 'has_statement_lines'])
session = config.current_session_id
if session.state != 'opened':
    # Counted as expected, as the opening popup proposes it (main-currency
    # notes only): no opening difference in the closing popup.
    session.set_multicurrency_counts({c.id: config._nm_currency_balance(c) for c in (eur, gbp)}, cashier_name='Marie Dupont')
    session.set_opening_control(config._get_opening_balance() - config._nm_foreign_company_amount(), '')
    session.try_cash_in_out('in', 1000.0, 'Change fund', env.user.partner_id.id)
print('session', session.id, session.state, 'EUR drawer', config._nm_currency_balance(eur), 'GBP drawer', config._nm_currency_balance(gbp))
customers = {n: env['res.partner'].search([('name', '=', n)], limit=1) for n in ('Lena Fischer', 'Thomas Leroy', 'Olivia Bennett')}
customers['Olivia Bennett'].write({
    'nm_id_document_type': 'passport', 'nm_id_document_number': '533419872',
    'nm_id_document_country_id': env.ref('base.uk').id, 'nm_id_document_expiry': date(2031, 3, 14),
    'nm_nationality_id': env.ref('base.uk').id, 'nm_birthdate': date(1986, 7, 2),
})
Exchange = env['pos.nm.exchange']
r1 = Exchange.create_from_ui(session.id, main.id, 200.0, eur.id, partner_id=customers['Lena Fischer'].id)
r2 = Exchange.create_from_ui(session.id, gbp.id, 60.0, main.id, note='Tourist')
r3 = Exchange.create_from_ui(session.id, eur.id, 150.0, main.id, partner_id=customers['Thomas Leroy'].id)
r4 = Exchange.create_from_ui(session.id, main.id, 80.0, gbp.id)
r5 = Exchange.create_from_ui(session.id, eur.id, 400.0, main.id, partner_id=customers['Olivia Bennett'].id)
r6 = Exchange.create_from_ui(session.id, main.id, 120.0, eur.id, note='Wrong currency asked')
for r in (r1, r2, r3, r4, r5, r6):
    print(r['name'], r['amount_in'], r['currency_in'], '->', r['amount_out'], r['currency_out'], 'commission', r['commission'])
cancelled = Exchange.search([('name', '=', r6['name'])])
cancelled.action_cancel()

# ---------------- Exchange office (20.0.4.0.0): two counters
# The office takes over the rules of the point of sale (the same values, so
# that the captures above do not change) and adds the origin of funds and
# review thresholds, the compliance officer and the notes in transit account.
transit = Account.search([('code', '=', '101098'), ('company_ids', 'in', company.id)], limit=1) \
    or Account.create({'name': 'Notes in Transit', 'code': '101098', 'account_type': 'asset_current'})
office = env['pos.nm.exchange.office'].create({
    'name': 'Riverside Exchange Office', 'partner_id': company.partner_id.id, 'licence': 'MSB-2026-0418',
    'compliance_user_id': env.user.id, 'transit_account_id': transit.id,
    'customer_threshold': 250.0, 'document_threshold': 400.0, 'linked_days': 7,
    'origin_threshold': 1000.0, 'review_threshold': 1500.0, 'board_refresh': 60,
})
# Coins of EUR and GBP next to the notes of POS Multi-Currency Cash.
Bill = env['pos.bill']
for currency, values in ((eur, (1, 2)), (gbp, (1, 2))):
    for value in values:
        if not Bill.search([('currency_id', '=', currency.id), ('value', '=', value)]):
            Bill.create({'name': '%s %s' % (value, currency.name), 'value': value, 'currency_id': currency.id})
# Second counter: its own cash journal and cash payment method (EUR, GBP),
# the notes tracked by denomination.
journal2 = env['account.journal'].search([('code', '=', 'CTR2'), ('company_id', '=', company.id)], limit=1) \
    or env['account.journal'].create({'name': 'Cash Counter 2', 'code': 'CTR2', 'type': 'cash', 'company_id': company.id,
                                      'profit_account_id': journal.profit_account_id.id,
                                      'loss_account_id': journal.loss_account_id.id})
# (a new cash journal may come with its payment method)
cash_pm2 = journal2.pos_payment_method_ids[:1] or env['pos.payment.method'].create(
    {'name': 'Cash Counter 2', 'journal_id': journal2.id, 'type': 'cash'})
cash_pm2.write({'name': 'Cash Counter 2', 'currency_ids': [(6, 0, (eur | gbp).ids)]})
config2 = config.copy({'name': 'Riverside Counter 2', 'payment_method_ids': [(6, 0, cash_pm2.ids)]})
config2.write({
    'nm_exchange_enabled': True, 'nm_exchange_income_account_id': income.id,
    'nm_exchange_track_notes': True, 'nm_exchange_board_on_display': True,
})
config.write({'nm_exchange_office_id': office.id, 'nm_exchange_board_on_display': True})
config2.write({'nm_exchange_office_id': office.id})
office.reference_config_id = config
# Rate sync: the rates and commissions of the reference counter copied to Counter 2.
office.action_nm_apply_rates()
print('rate differences', office._nm_rate_differences())
# Opening of Counter 2 counted by denomination: 1,080 EUR and 580 GBP.
config2.open_ui()
session2 = config2.current_session_id
opening = {
    eur: {'100': 4, '50': 6, '20': 10, '10': 10, '5': 10, '2': 10, '1': 10},
    gbp: {'50': 4, '20': 10, '10': 10, '5': 10, '2': 10, '1': 10},
}
session2.set_multicurrency_counts(
    {str(c.id): sum(float(k) * q for k, q in d.items()) for c, d in opening.items()}, None,
    {str(c.id): d for c, d in opening.items()}, cashier_name='James Carter')
session2.set_opening_control(0.0, '')
session2.try_cash_in_out('in', 3000.0, 'Change fund', env.user.partner_id.id)


def exchange2(currency_in, amount_in, currency_out, notes_in=None, **kwargs):
    # Notes handed back as the popup proposes them from the stock.
    quote = Exchange.get_quote(config2.id, currency_in.id, amount_in, currency_out.id, partner_id=kwargs.get('partner_id'))
    notes_out = None
    if quote.get('notes_out'):
        notes_out = {row['key']: row['proposed'] for row in quote['notes_out']['rows']}
    return Exchange.create_from_ui(session2.id, currency_in.id, amount_in, currency_out.id,
                                   notes_in=notes_in, notes_out=notes_out, **kwargs)


s1 = exchange2(main, 150.0, eur)
s2 = exchange2(gbp, 100.0, eur, notes_in={'50': 1, '20': 2, '10': 1})
s3 = exchange2(gbp, 60.0, main, notes_in={'50': 1, '10': 1})
# Above the origin of funds and review thresholds: declarations, To Review,
# activity of the compliance officer.
daniel = env['res.partner'].search([('name', '=', 'Daniel Moreau')], limit=1) or env['res.partner'].create({
    'name': 'Daniel Moreau', 'street': '7 avenue Foch', 'city': 'Paris', 'zip': '75116',
    'country_id': env.ref('base.fr').id, 'email': 'daniel.moreau@example.com',
})
daniel.write({
    'nm_id_document_type': 'passport', 'nm_id_document_number': '21FR48213', 'nm_id_document_country_id': env.ref('base.fr').id,
    'nm_id_document_expiry': date(2032, 5, 9), 'nm_nationality_id': env.ref('base.fr').id, 'nm_birthdate': date(1979, 11, 23),
})
s4 = exchange2(eur, 1800.0, main, notes_in={'200': 6, '100': 6}, partner_id=daniel.id, note='Return from a trip',
               declaration={'funds_origin': 'savings', 'funds_origin_note': 'Savings account, Paris', 'purpose': 'travel', 'pep': False})
for r in (s1, s2, s3, s4):
    print(r['name'], r['amount_in'], r['currency_in'], '->', r['amount_out'], r['currency_out'], 'commission', r['commission'])
review = Exchange.search([('name', '=', s4['name'])])
print('review', review.compliance_state, review.review_reason, review.register_hash)
# Notes sent by Counter 2 to the first counter, not received yet: in transit.
transfer = env['pos.nm.exchange.transfer'].send_from_ui(
    session2.id, config.id, eur.id, 500.0, notes={'100': 3, '50': 4}, note='Change fund for the afternoon')
print('transfer', transfer['name'], transfer['state'], transfer.get('notes_label'))
print('drawers', office._nm_drawers())
env.cr.commit()
print('IDS config=%s session=%s token=%s eur_setting=%s cancelled=%s' % (
    config.id, session.id, config.access_token,
    Setting.search([('config_id', '=', config.id), ('currency_id', '=', eur.id)], limit=1).id, cancelled.id))
print('IDS2 office=%s config2=%s session2=%s review=%s transfer=%s' % (
    office.id, config2.id, session2.id, review.id, transfer['id']))
