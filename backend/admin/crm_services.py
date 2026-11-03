"""Shared navigation and bounded quote previews for the customer workspace."""
from flask import url_for
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from backend.database import db
from backend.models import Quote


def crm_url(tab='customers', **filters):
    filters['tab'] = tab if tab in ('customers', 'quotes') else 'customers'
    return url_for('admin.admin_crm', **filters)


def customer_quote_previews(phones, limit=3):
    result = {phone: [] for phone in phones}
    if not result:
        return result
    ranked = db.session.query(Quote.id.label('id'), func.row_number().over(
        partition_by=Quote.phone, order_by=(Quote.created_at.desc(), Quote.id.desc())
    ).label('position')).filter(Quote.phone.in_(result)).subquery()
    quotes = Quote.query.join(ranked, ranked.c.id == Quote.id).filter(ranked.c.position <= limit).options(
        selectinload(Quote.admin_state)).order_by(Quote.created_at.desc(), Quote.id.desc()).all()
    for quote in quotes:
        result[quote.phone].append(quote)
    return result
