from flask import Blueprint, render_template

from ..models import Opportunity


opportunities_bp = Blueprint(
    "opportunities",
    __name__,
    url_prefix="/opportunities",
)


@opportunities_bp.route("/")
def index():
    opportunities = (
        Opportunity.query
        .filter_by(published=True)
        .order_by(Opportunity.created_at.desc())
        .all()
    )

    return render_template(
        "opportunities/index.html",
        opportunities=opportunities,
    )