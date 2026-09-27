import re
import unicodedata
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..extensions import db
from ..models import BlogPost

blog_bp = Blueprint("blog", __name__, url_prefix="/blog")


def make_slug(title):
    value = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "post"


def unique_slug(title, post_id=None):
    base = make_slug(title)
    slug = base
    number = 2
    while True:
        query = BlogPost.query.filter_by(slug=slug)
        if post_id is not None:
            query = query.filter(BlogPost.id != post_id)
        if not query.first():
            return slug
        slug = f"{base}-{number}"
        number += 1


@blog_bp.route("/")
def index():
    category = request.args.get("category", "").strip()
    query = BlogPost.query.filter_by(status="approved")
    if category:
        query = query.filter_by(category=category)
    posts = query.order_by(BlogPost.created_at.desc()).all()
    categories = [row[0] for row in db.session.query(BlogPost.category).filter(
        BlogPost.status == "approved", BlogPost.category.isnot(None)
    ).distinct().order_by(BlogPost.category).all()]
    return render_template("blog/index.html", posts=posts, categories=categories, selected_category=category)


@blog_bp.route("/<slug>")
def detail(slug):
    post = BlogPost.query.filter_by(slug=slug, status="approved").first_or_404()
    return render_template("blog/detail.html", post=post)


@blog_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "General").strip() or "General"
        excerpt = request.form.get("excerpt", "").strip()
        content = request.form.get("content", "").strip()

        if not title or not content:
            flash("Title and content are required.", "error")
            return render_template("blog/create.html")
        if len(title) > 200:
            flash("Title must be 200 characters or fewer.", "error")
            return render_template("blog/create.html")
        if len(category) > 100:
            flash("Category must be 100 characters or fewer.", "error")
            return render_template("blog/create.html")
        if not excerpt:
            excerpt = content.replace("\n", " ").strip()[:240]
        else:
            excerpt = excerpt[:500]

        post = BlogPost(
            title=title,
            slug=unique_slug(title),
            excerpt=excerpt,
            content=content,
            category=category,
            status="pending",
            author_id=current_user.id,
        )
        db.session.add(post)
        db.session.commit()
        flash("Your post was submitted and is waiting for admin approval.", "success")
        return redirect(url_for("blog.my_posts"))

    return render_template("blog/create.html")


@blog_bp.route("/my-posts")
@login_required
def my_posts():
    posts = BlogPost.query.filter_by(author_id=current_user.id).order_by(BlogPost.created_at.desc()).all()
    return render_template("blog/my_posts.html", posts=posts)
